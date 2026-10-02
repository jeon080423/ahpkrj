"""
image_text_scale.py
-------------------
설문 설명 이미지 속 글자 크기를 설문 본문 텍스트 크기에 자동으로 맞추는 모듈.

배경:
- 설문 설명을 이미지(그림 파일)로 업로드하면, 이미지 속 글자 크기가 제각각이라
  설문 화면의 본문 텍스트와 이질감이 생긴다는 지적이 있었음.
- 이 모듈은 Tesseract OCR로 이미지 속 텍스트 줄의 높이(px) 중앙값을 측정하고,
  설문 본문 폰트 크기(기본 16px)에 맞춰 이미지 전체를 리사이즈한다.
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

# 설문 본문 기본 폰트 크기(px). 앱 CSS에서 본문을 0.95rem으로 지정 (루트 16px 기준 약 15.2px).
TARGET_FONT_PX = 15.2
# OCR로 측정한 텍스트 줄 박스 높이 ≈ font-size × 1.25 (상·하단 여백 포함)
LINE_HEIGHT_RATIO = 1.25
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
        from PIL import Image
        import pytesseract

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        if w <= 0 or h <= 0:
            return 1.0

        # OCR 속도 확보를 위해 큰 이미지는 축소 (측정값은 원본 기준으로 환산)
        work_scale = 1.0
        work_img = img
        if max(w, h) > OCR_MAX_DIM:
            work_scale = OCR_MAX_DIM / float(max(w, h))
            work_img = img.resize(
                (max(1, int(w * work_scale)), max(1, int(h * work_scale))),
                Image.LANCZOS,
            )

        data = pytesseract.image_to_data(
            work_img, lang="kor+eng", output_type=pytesseract.Output.DICT
        )
        heights = []
        n = len(data.get("text", []))
        for i in range(n):
            try:
                # level 4 = 텍스트 줄 단위
                if int(data["level"][i]) != 4:
                    continue
                text = (data["text"][i] or "").strip()
                if not text:
                    continue
                if float(data["conf"][i]) < MIN_CONFIDENCE:
                    continue
                box_h = int(data["height"][i])
                if box_h < MIN_TEXT_HEIGHT_PX:
                    continue
                # 작업 이미지 기준 높이를 원본 이미지 기준으로 환산
                heights.append(box_h / work_scale)
            except Exception:
                continue

        if not heights:
            return 1.0

        median_h = _median(heights)
        target_h = float(target_font_px) * LINE_HEIGHT_RATIO
        scale = target_h / median_h if median_h > 0 else 1.0
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
