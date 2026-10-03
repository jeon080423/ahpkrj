"""
image_text_scale.py
-------------------
설문 설명 이미지 속 글자 크기를 설문 본문 텍스트 크기에 자동으로 맞추는 모듈.

배경:
- 설문 설명을 이미지(그림 파일)로 업로드하면, 이미지 속 글자 크기가 제각각이라
  설문 화면의 본문 텍스트와 이질감이 생긴다는 지적이 있었음.
- 이 모듈은 Tesseract OCR로 이미지 속 텍스트 줄의 높이(px) 중앙값을 측정하고,
  설문 문항 폰트 크기(기본 16px, Streamlit 위젯 라벨 기본값 — 예: "SQ6. 성별")에 맞춰
  이미지 전체를 리사이즈한다.
  이미지 내 상대적 크기 비율(제목/본문 차이)은 그대로 유지된다.

안전장치:
- Tesseract가 설치돼 있지 않거나, 이미지에서 텍스트를 찾지 못하면
  배율 1.0(원본 그대로)을 반환한다. 절대 실패로 설문이 깨지지 않는다.
- 배율은 MIN_SCALE~MAX_SCALE 범위로 제한한다.
- 같은 이미지에 대한 감지 결과는 메모리에 캐시한다.
"""

import hashlib
import io
import logging

logger = logging.getLogger(__name__)

# 설문 문항 기본 폰트 크기(px). 설문 문항("SQ6. 성별" 등)은 Streamlit 위젯 라벨로
# 렌더링되며 별도 CSS 지정이 없어 기본 1rem = 16px이 적용된다.
# (이전에는 본문 0.95rem ≈ 15.2px 기준이었으나, 2026-10-03 사용자 요청으로 문항 기준으로 변경)
TARGET_FONT_PX = 16.0
# OCR로 측정한 단어 박스 높이 ≈ font-size × 1.0
# (2026-10-03 태블릿 실측: 1.12로 설정 시 이미지 글자가 문항보다 약 12% 크게 표시됨.
#  한글 Tesseract 단어 박스 높이는 font-size와 거의 동일하므로 1.0으로 바로잡음)
# 중요: Tesseract TSV 출력은 인식 텍스트를 단어 레벨(level 5)에만 기록하므로,
# 텍스트 감지는 반드시 단어 레벨에서 수행해야 한다 (줄 레벨의 text 필드는 비어 있음).
WORD_HEIGHT_RATIO = 1.0
# 배율 제한: 너무 작아지거나 흐려질 정도로 커지는 것을 방지
MIN_SCALE = 0.35
MAX_SCALE = 2.0
# OCR 전 작업 이미지 최대 변 (속도 확보용, 비율은 원본 기준으로 환산)
OCR_MAX_DIM = 1600
# 텍스트로 인정하는 최소 줄 높이(px). 이보다 작으면 노이즈로 제외.
MIN_TEXT_HEIGHT_PX = 8
# Tesseract 신뢰도(conf) 하한. 이보다 낮으면 제외.
MIN_CONFIDENCE = 30

_scale_cache = {}
_CACHE_MAX = 128


def _cache_get(key):
    return _scale_cache.get(key)


def _cache_put(key, value):
    if len(_scale_cache) >= _CACHE_MAX:
        # 가장 오래된 항목부터 정리 (dict는 삽입 순서 유지)
        for k in list(_scale_cache.keys())[: _CACHE_MAX // 2]:
            _scale_cache.pop(k, None)
    _scale_cache[key] = value


def tesseract_available():
    """Tesseract OCR 바이너리 + pytesseract 사용 가능 여부."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _median(values):
    s = sorted(values)
    return s[len(s) // 2]


def _percentile(values, p):
    """p 백분위수 (0~100). 이미지 내 큰 글자 기준으로 맞추기 위해 사용."""
    s = sorted(values)
    if not s:
        return 0
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


# 스케일 계산에 사용하는 백분위수. 이미지 안에 제목(큰 글자)+본문(작은 글자)이
# 섞여 있을 때, 눈에 띄는 큰 글자가 문항 크기와 맞도록 백분위수 기준 사용.
# (2026-10-03: median(50)으로는 큰 글자가 여전히 커 보였고, 75로는 과하게 작아져
#  사용자 확인 후 60으로 조정)
SCALE_PERCENTILE = 60


def _collect_word_heights(data, work_scale):
    """
    Tesseract TSV dict에서 단어 레벨(level 5)의 텍스트 박스 높이들을 수집한다.
    TSV의 text 필드는 단어 레벨에만 값이 있으므로 줄 레벨(level 4)에서는
    텍스트 유무를 판단할 수 없다. (2026-10-02 진단에서 줄수=0 원인으로 확인)
    반환: 원본 이미지 기준 높이(px) 리스트
    """
    heights = []
    n = len(data.get("text", []))
    for i in range(n):
        try:
            if int(data["level"][i]) != 5:
                continue
            if not (data["text"][i] or "").strip():
                continue
            if float(data["conf"][i]) < MIN_CONFIDENCE:
                continue
            bh = int(data["height"][i])
            if bh >= MIN_TEXT_HEIGHT_PX:
                heights.append(bh / work_scale)
        except Exception:
            continue
    return heights


def _ocr_data_for(image_bytes):
    """OCR 실행 후 (work_scale, data dict, 사용 lang) 반환. 실패 시 (None, None, None)."""
    from PIL import Image
    import pytesseract

    img = Image.open(io.BytesIO(bytes(image_bytes))).convert("RGB")
    w, h = img.size
    if w <= 0 or h <= 0:
        return None, None, None
    work_scale = 1.0
    work_img = img
    if max(w, h) > OCR_MAX_DIM:
        work_scale = OCR_MAX_DIM / float(max(w, h))
        work_img = img.resize(
            (max(1, int(w * work_scale)), max(1, int(h * work_scale))),
            Image.LANCZOS,
        )
    for _lang in ("kor+eng", "eng"):
        try:
            data = pytesseract.image_to_data(
                work_img, lang=_lang, output_type=pytesseract.Output.DICT
            )
            return work_scale, data, _lang
        except Exception:
            continue
    return None, None, None


def diagnose_ocr(image_bytes):
    """
    진단용: OCR 파이프라인 각 단계의 상태를 반환한다.
    반환 dict: {
      "tesseract_bin": bool,   # tesseract 바이너리+kor+eng 사용 가능 여부
      "lines": int,            # 감지된 텍스트 줄 수 (실패 시 -1)
      "median_h": float|None,  # 중앙값 줄 높이(px)
      "lang_used": str,        # 실제 사용된 lang ("kor+eng" / "eng" / "-")
    }
    """
    info = {"tesseract_bin": False, "lines": -1, "median_h": None, "lang_used": "-",
            "total_rows": 0, "level_counts": {}, "nonempty": 0, "conf_ge30": 0, "sample": []}
    try:
        import pytesseract

        try:
            pytesseract.get_tesseract_version()
            info["tesseract_bin"] = True
        except Exception:
            return info
        from PIL import Image

        img = Image.open(io.BytesIO(bytes(image_bytes))).convert("RGB")
        w, h = img.size
        work, ws = img, 1.0
        if max(w, h) > OCR_MAX_DIM:
            ws = OCR_MAX_DIM / float(max(w, h))
            work = img.resize((max(1, int(w * ws)), max(1, int(h * ws))), Image.LANCZOS)
        last_err = None
        for lang in ("kor+eng", "eng"):
            try:
                data = pytesseract.image_to_data(work, lang=lang, output_type=pytesseract.Output.DICT)
                info["lang_used"] = lang
                break
            except Exception as e:
                last_err = e
                continue
        else:
            return info
        heights = []
        n = len(data.get("text", []))
        info["total_rows"] = n
        for i in range(n):
            try:
                lv = str(data["level"][i])
                info["level_counts"][lv] = info["level_counts"].get(lv, 0) + 1
                txt_raw = (data["text"][i] or "").strip()
                if txt_raw:
                    info["nonempty"] += 1
                    try:
                        _cf = float(data["conf"][i])
                    except Exception:
                        _cf = -1.0
                    if _cf >= MIN_CONFIDENCE:
                        info["conf_ge30"] += 1
                    if len(info["sample"]) < 3:
                        info["sample"].append(
                            f"L{lv}/c{data['conf'][i]}/h{data['height'][i]}/{txt_raw[:12]}"
                        )
                if int(data["level"][i]) != 5:
                    continue
                if not txt_raw:
                    continue
                if float(data["conf"][i]) < MIN_CONFIDENCE:
                    continue
                bh = int(data["height"][i])
                if bh >= MIN_TEXT_HEIGHT_PX:
                    heights.append(bh / ws)
            except Exception:
                continue
        info["lines"] = len(heights)
        if heights:
            info["median_h"] = round(_median(heights), 1)
        return info
    except Exception:
        return info


def detect_text_scale(image_bytes, target_font_px=TARGET_FONT_PX):
    """
    이미지 속 대표 글자 높이를 측정해 목표 크기에 맞추는 배율을 반환한다.
    측정 실패 시 1.0(원본 유지)을 반환한다.
    """
    if not image_bytes:
        return 1.0
    try:
        digest = hashlib.sha1(bytes(image_bytes)).hexdigest()
    except Exception:
        return 1.0
    cache_key = f"{digest}@{target_font_px}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    scale = _detect_uncached(bytes(image_bytes), target_font_px)
    _cache_put(cache_key, scale)
    return scale


def _detect_uncached(image_bytes, target_font_px):
    try:
        work_scale, data, _lang = _ocr_data_for(image_bytes)
        if data is None:
            return 1.0
        heights = _collect_word_heights(data, work_scale)
        if not heights:
            return 1.0
        ref_h = _percentile(heights, SCALE_PERCENTILE)
        target_h = float(target_font_px) * WORD_HEIGHT_RATIO
        scale = target_h / ref_h if ref_h > 0 else 1.0
        return max(MIN_SCALE, min(MAX_SCALE, scale))
    except Exception as e:
        logger.debug("detect_text_scale 실패, 원본 유지: %s", e)
        return 1.0


def apply_text_size_match(image_bytes, manual_mult=1.0, target_font_px=TARGET_FONT_PX):
    """
    자동 감지 배율 × 수동 배율로 이미지를 리사이즈한다.
    반환: (리사이즈된 이미지 bytes, mime_type, 너비(px), 높이(px), 적용된 최종 배율)
    - 배율이 1.0에 근접하면 원본을 그대로 반환한다.
    - 원본 포맷(PNG/JPEG)을 유지한다.
    - 어떤 경우에도 예외를 밖으로 던지지 않고 원본을 반환한다.
    """
    if not image_bytes:
        return image_bytes, "image/png", 0, 0, 1.0
    try:
        manual_mult = float(manual_mult) if manual_mult else 1.0
    except Exception:
        manual_mult = 1.0

    try:
        raw = bytes(image_bytes)
        scale = detect_text_scale(raw, target_font_px) * manual_mult
        scale = max(MIN_SCALE, min(MAX_SCALE, scale))
        if abs(scale - 1.0) < 0.02:
            w0, h0 = _image_size(raw)
            return raw, _guess_mime(raw), w0, h0, 1.0

        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        orig_format = img.format or "PNG"
        img = img.convert("RGB")
        w, h = img.size
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        resized = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        fmt = str(orig_format).upper()
        if fmt in ("JPG", "JPEG"):
            resized.save(buf, format="JPEG", quality=92)
            return buf.getvalue(), "image/jpeg", new_size[0], new_size[1], scale
        if fmt == "WEBP":
            resized.save(buf, format="WEBP", quality=92)
            return buf.getvalue(), "image/webp", new_size[0], new_size[1], scale
        resized.save(buf, format="PNG")
        return buf.getvalue(), "image/png", new_size[0], new_size[1], scale
    except Exception as e:
        logger.debug("apply_text_size_match 실패, 원본 유지: %s", e)
        try:
            raw = bytes(image_bytes)
            w0, h0 = _image_size(raw)
            return raw, _guess_mime(raw), w0, h0, 1.0
        except Exception:
            return image_bytes, "image/png", 0, 0, 1.0


def _image_size(image_bytes):
    try:
        from PIL import Image

        with Image.open(io.BytesIO(bytes(image_bytes))) as im:
            return im.size[0], im.size[1]
    except Exception:
        return 0, 0


def _guess_mime(image_bytes):
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(bytes(image_bytes)))
        fmt = (img.format or "PNG").upper()
        if fmt in ("JPG", "JPEG"):
            return "image/jpeg"
        if fmt == "WEBP":
            return "image/webp"
        return "image/png"
    except Exception:
        return "image/png"
