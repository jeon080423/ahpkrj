import streamlit as st
import datetime
from yeta_db import get_event_settings

def get_quotation_html(client_name, project_name, amount, plan_name):
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_str = today.strftime("%Y년 %m월 %d일")
    kor_amount = num_to_kor(amount)
    
    stamp_b64 = ""
    try:
        with open("stamp.png", "rb") as f:
            stamp_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error loading stamp.png: {e}")
        
    if stamp_b64:
        stamp_element = f'<img src="data:image/png;base64,{stamp_b64}" style="position: absolute; top: -12px; right: -28px; width: 34px; height: 34px; mix-blend-mode: multiply; pointer-events: none;" />'
    else:
        stamp_element = '<div class="stamp">전상현<br>인</div>'
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>견적서</title>
    <style>

        body {{ font-family: 'Malgun Gothic', 'Dotum', sans-serif; margin: 10px; color: #000; line-height: 1.5; background: #fff; }}
        .title {{ text-align: center; font-size: 30px; font-weight: bold; text-decoration: underline; margin-bottom: 30px; letter-spacing: 5px; }}
        .meta-list {{ list-style: none; padding: 0; margin: 0 0 20px 0; font-size: 13px; }}
        .meta-list li {{ margin-bottom: 6px; font-weight: bold; }}
        .meta-list span.lbl {{ display: inline-block; width: 90px; color: #111; }}
        
        .main-layout {{ display: flex; justify-content: space-between; align-items: stretch; margin-bottom: 20px; gap: 15px; }}
        .info-left {{ width: 52%; }}
        .info-right {{ width: 46%; }}
        .provider-table {{ border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; text-align: left; }}
        .provider-table th, .provider-table td {{ border: 1px solid #000; padding: 6px 8px; word-break: keep-all; }}
        .provider-table th {{ background: #f2f2f2; width: 65px; text-align: center; font-weight: bold; }}
        .provider-table td {{ line-height: 1.4; }}
        
        .stamp-container {{ position: relative; display: inline-block; white-space: nowrap; }}
        .stamp {{ position: absolute; top: -10px; right: -32px; width: 32px; height: 32px; border: 2px solid #ff0000; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #ff0000; font-size: 9px; font-weight: bold; font-family: 'Batang', serif; transform: rotate(-5deg); background-color: rgba(255, 0, 0, 0.05); user-select: none; line-height: 1.1; }}

        .items-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 15px; }}
        .items-table th, .items-table td {{ border: 1px solid #000; padding: 8px 10px; }}
        .items-table th {{ background: #000; color: #fff; text-align: center; font-weight: bold; }}
        .items-table td {{ text-align: center; }}
        
        .sum-row {{ font-weight: bold; background: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="title">견 적 서</div>
    
    <div class="main-layout">
        <div class="info-left">
            <ul class="meta-list">
                <li><span class="lbl">■ 과 제 명 :</span> {project_name}</li>
                <li><span class="lbl">■ 의뢰기관 :</span> {client_name}</li>
                <li><span class="lbl">■ 서비스명 :</span> AHP 의사결정 분석 솔루션(AHP마스터)</li>
                <li><span class="lbl">■ 소요예산 :</span> {kor_amount} (\\₩{amount:,}, VAT 포함)</li>
                <li><span class="lbl">■ 작성일 :</span> {today_str}</li>
                <li><span class="lbl">■ 담 당 자 :</span> 전상현 / jeon080423@gmail.com / 0507-1347-2610</li>
            </ul>
        </div>
        <div class="info-right">
            <table class="provider-table">
                <tr>
                    <th rowspan="4" style="width: 25px; font-size: 11px;">공<br>급<br>자</th>
                    <th>상호</th>
                    <td>프레쉬인사이트</td>
                </tr>
                <tr>
                    <th>등록번호</th>
                    <td style="font-size: 11px; font-weight: bold;">683-27-00122</td>
                </tr>
                <tr>
                    <th>주소</th>
                    <td style="font-size: 11px;">인천 부평구 원길로 12, 가동 203호 (갈산동, 선우빌딩)</td>
                </tr>
                <tr>
                    <th>대표자</th>
                    <td>
                        <div class="stamp-container">
                            전 상 현
                            {stamp_element}
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    
    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 25%;">비 목</th>
                <th style="width: 20%;">금 액</th>
                <th style="width: 35%;">산 출 내 역</th>
                <th style="width: 20%;">비 고</th>
            </tr>
        </thead>
        <tbody>
            <tr style="height: 35px;">
                <td style="font-weight: bold; background: #eee;">1. 경비 소계</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr style="height: 50px;">
                <td style="text-align: left; padding-left: 20px;">
                    AHP 분석<br>솔루션 이용료 ({plan_name})
                </td>
                <td style="text-align: right;">{amount:,}</td>
                <td>{amount:,} 원 X 1 식</td>
                <td>AHPMASTER</td>
            </tr>
            <tr style="height: 90px;">
                <td></td>
                <td colspan="2" style="color: #666; font-size: 12px; vertical-align: top; padding-top: 15px;">이하 여백</td>
                <td></td>
            </tr>
            <tr class="sum-row" style="height: 35px;">
                <td>총 합 계</td>
                <td style="text-align: right;">{amount:,}</td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    </table>
    
    <div style="font-weight: bold; font-size: 12px; margin-bottom: 10px;">※ 간이과세자</div>
</body>
</html>
"""

def get_yeta_login_redirect_html(plan_name="무료 체험판", inner_html="", is_best=False):
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    if "무료" in plan_name or "0" in plan_name:
        btn_label = "분석기로 이동"
    elif "기관" in plan_name:
        btn_label = "로그인 후 B2B 신청"
    else:
        btn_label = "로그인 후 결제"
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>

        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            {border_css}
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          {best_badge}
          <div style="height: 260px; box-sizing: border-box;">{inner_html}</div>
          <button class="btn" onclick="redirectAction()">{btn_label}</button>
      </div>
      <script>
        function redirectAction() {{
            if ("{plan_name}".includes("무료 체험판")) {{
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                for (let i = 0; i < tabs.length; i++) {{
                    if (tabs[i].innerText.includes('예타 종합평가(AHP) 분석') || tabs[i].innerText.includes('Preliminary Feasibility')) {{
                        tabs[i].click();
                        window.parent.scrollTo(0, 0);
                        return;
                    }}
                }}
            }}
            
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('로그인 또는 회원가입이 필요합니다. 메인 화면 또는 사이드바에서 로그인을 해주세요.');
            window.parent.scrollTo(0, 0);
        }}
      </script>
    </body>
    </html>
    """

def get_yeta_portone_payment_html(user_id, plan_name="단건 분석권", amount=300000, months=2, inner_html="", is_best=False):
    import hashlib
    login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    safe_email = user_id.strip() if user_id and "@" in user_id else "test@ahp.kr"
    
    event_cfg = get_event_settings()
    is_cfg_active = event_cfg["active"]
    event_title = event_cfg["title"]
    event_desc = event_cfg["desc"]
    event_deadline_str = event_cfg["deadline"]
    event_discount = event_cfg["discount"]
    
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    try:
        event_deadline = datetime.datetime.strptime(event_deadline_str, "%Y-%m-%d")
        event_deadline = event_deadline.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
    except Exception:
        event_deadline = datetime.datetime(2026, 7, 30, 23, 59, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        
    is_event_active = is_cfg_active and kst_now <= event_deadline and plan_name == "단건 분석권"
    
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    event_ui_html = ""
    if is_event_active:
        event_ui_html = f"""
        <div id="event-container" style="margin-top: auto; margin-bottom: 6px; padding: 6px 8px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 1px dashed #0284c7; border-radius: 6px; font-size: 0.72rem; text-align: left; line-height: 1.2; height: auto; overflow: hidden;">
            <div style="font-weight: bold; color: #0284c7; margin-bottom: 2px;">
                <b>{event_title}</b>
            </div>
            <div style="font-size: 0.65rem; color: #475569; margin-bottom: 4px;">
                {event_desc}
            </div>
            <label style="display: flex; align-items: center; gap: 4px; font-weight: bold; color: #1e293b; cursor: pointer; user-select: none; font-size: 0.7rem; margin: 0;">
                <input type="checkbox" id="event-agree" onchange="toggleEvent()" style="accent-color: #0284c7; cursor: pointer; width: 13px; height: 13px; margin: 0;">
                할인 신청 ({event_discount:,}원 즉시 할인)
            </label>
            <div id="event-inputs" style="display: none; flex-direction: column; gap: 4px; background: white; padding: 6px 24px 6px 10px; border-radius: 4px; border: 1px solid #e2e8f0; margin-top: 4px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">대학명:</span>
                    <input type="text" id="univ-name" placeholder="예: 한국대 대학원" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">논문명:</span>
                    <input type="text" id="thesis-title" placeholder="예: AHP 의사결정 연구" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
            </div>
        </div>
        """

    if plan_name == "무료 체험판 (영구)":
        btn_onclick = "redirectAnalysis()"
        btn_label = "체험하기"
    elif plan_name == "연간 라이선스":
        btn_onclick = "scrollToB2B()"
        btn_label = "세금계산서/인보이스 신청"
    else:
        btn_onclick = "openPaymentWindow()"
        btn_label = f"결제 {plan_name}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>

        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            {border_css}
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          {best_badge}
          <div style="height: 260px; box-sizing: border-box;">{inner_html}</div>
          {event_ui_html}
          <button class="btn" onclick="{btn_onclick}">{btn_label}</button>
      </div>
      <script>
        let isEventApplied = false;
        const originalAmount = {amount};
        let finalAmount = originalAmount;

        function toggleEvent() {{
            const agreeCheckbox = document.getElementById("event-agree");
            const inputDiv = document.getElementById("event-inputs");
            const priceSpanOuter = window.parent.document.getElementById("yeta-single-price-display-span");
            
            if (agreeCheckbox && agreeCheckbox.checked) {{
                if (inputDiv) inputDiv.style.display = "flex";
                finalAmount = originalAmount - {event_discount};
                isEventApplied = true;
            }} else {{
                if (inputDiv) inputDiv.style.display = "none";
                finalAmount = originalAmount;
                isEventApplied = false;
                if (document.getElementById("univ-name")) document.getElementById("univ-name").value = "";
                if (document.getElementById("thesis-title")) document.getElementById("thesis-title").value = "";
            }}
            
            if (priceSpanOuter) {{
                priceSpanOuter.innerText = finalAmount.toLocaleString();
            }}
        }}

        function redirectAnalysis() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('예타 종합평가(AHP) 분석') || tabs[i].innerText.includes('Preliminary Feasibility')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
        }}

        function scrollToB2B() {{
            const b2bEl = window.parent.document.getElementById("b2b-payment-section");
            if (b2bEl) {{
                b2bEl.scrollIntoView({{ behavior: 'smooth' }});
            }} else {{
                alert('하단의 B2B 세금계산서/인보이스 발행 요청 서식을 작성해 주세요.');
            }}
        }}

        function openPaymentWindow() {{
          let univ = "";
          let thesis = "";
          
          if (isEventApplied) {{
              const uInput = document.getElementById("univ-name");
              const tInput = document.getElementById("thesis-title");
              univ = uInput ? uInput.value.trim() : "";
              thesis = tInput ? tInput.value.trim() : "";
              
              if (!univ) {{
                  alert("이벤트 혜택 적용을 위해 대학명을 입력해 주세요.");
                  if (uInput) uInput.focus();
                  return;
              }}
              if (!thesis) {{
                  alert("이벤트 혜택 적용을 위해 논문명을 입력해 주세요.");
                  if (tInput) tInput.focus();
                  return;
              }}
          }}

          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("팝업 차단이 설정되어 있습니다. 팝업 차단을 해제해주세요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>안전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈을 안전하게 불러오는 중입니다...</h3>
              <p>이 창을 닫지 마세요.</p>
            </body>
            </html>
          `);
          win.document.close();

          let baseOrigin = window.location.origin;
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          
          let eventParams = "&event_applied=" + (isEventApplied ? "Y" : "N") + 
                            "&university=" + encodeURIComponent(univ) + 
                            "&thesis_title=" + encodeURIComponent(thesis);
                            
          const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}") + eventParams;
          
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 띄우는 중입니다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "{plan_name} - {safe_email}",
              totalAmount: finalAmount,
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "사용자",
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 실패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 창 호출 중 오류가 발생했습니다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 실패! 인터넷 연결을 확인하세요.";
          }};
          win.document.head.appendChild(script);
        }}
      </script>
    </body>
    </html>
    """

def get_yeta_portone_custom_services_html(user_id=None):
    import hashlib
    login_token = ""
    safe_email = "test@ahp.kr"
    if user_id:
        login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        safe_email = user_id.strip() if "@" in user_id else "test@ahp.kr"

    is_logged_in = "true" if user_id else "false"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>

        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            border: 1px solid #ddd;
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .title {{ margin-top: 0 !important; margin-bottom: 0; font-size: 1.3rem; font-weight: bold; color: #333; }}
        .subtitle {{ color: #888; font-size: 1.1rem; }}
        .price-container {{ margin-top: 15px; margin-bottom: 5px; }}
        .price {{ color: #ff4b4b; font-size: 2rem; font-weight: bold; margin: 0; }}
        .period {{ color: #555; margin-top:0; font-size: 1rem; }}
        .desc {{ font-size: 0.85rem; color: #666; min-height: 40px; margin: 0; }}
        .divider {{ margin: 10px 0; border: 0; border-top: 1px solid #eee; }}
        
        .svc-list {{
            list-style: none;
            padding-left: 0;
            margin: 0;
            font-size: 0.9rem;
            color: #333;
            line-height: 1.8;
            flex-grow: 1;
        }}
        .svc-item {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 8px;
            cursor: pointer;
        }}
        .svc-item input[type="checkbox"] {{
            margin-right: 8px;
            margin-top: 4px;
            cursor: pointer;
            accent-color: #ff4b4b;
        }}
        .svc-item span {{
            font-size: 0.85rem;
            line-height: 1.4;
        }}
        
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          <h3 class="title">부가 서비스 대행</h3>
          <span class="subtitle">Custom Services</span>
          <div class="price-container">
              <h2 class="price" id="totalPriceDisplay">0원</h2>
          </div>
          <p class="period">선택된 서비스 합계 금액</p>
          <p class="desc" id="statusDesc">필요한 서비스를 선택해 주세요.</p>
          <hr class="divider">
          
          <ul class="svc-list">
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_1" value="50000" data-name="온라인 설문 셋팅" onchange="updatePrice()">
                      <span>AHP 온라인 설문 셋팅 <span style="color: #666; font-size: 0.75rem;">(50,000원)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_2" value="50000" data-name="결과 분석 대행" onchange="updatePrice()">
                      <span>AHP 결과 분석 대행 <span style="color: #666; font-size: 0.75rem;">(50,000원)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_3" value="30000" data-name="코딩 엑셀 양식 설정 대행" onchange="updatePrice()">
                      <span>AHP 코딩 엑셀 설정 대행 <span style="color: #666; font-size: 0.75rem;">(30,000원)</span></span>
                  </label>
              </li>
          
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_ext" value="100000" data-name="1개월 이용 연장" onchange="updatePrice()">
                      <span>1개월 이용 연장 <span style="color: #666; font-size: 0.75rem;">(100,000원)</span></span>
                  </label>
              </li>
          </ul>
          
          <div style="font-size: 0.72rem; color: #555; text-align: center; margin-bottom: 12px; background: #fafafa; padding: 6px; border-radius: 5px; border: 1px dashed #ccc; line-height: 1.4;">
              견적서 발급 및 부가서비스 문의: <br>카톡아이디: <b>AHPkr</b>
          </div>
          
          <button class="btn" id="payBtn" onclick="handlePayAction()">결제하기</button>
      </div>
      
      <script>
        function updatePrice() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            const optExt = document.getElementById("svc_opt_ext");
            
            let total = 0;
            let count = 0;
            if (opt1.checked) {{ total += parseInt(opt1.value); count++; }}
            if (opt2.checked) {{ total += parseInt(opt2.value); count++; }}
            if (opt3.checked) {{ total += parseInt(opt3.value); count++; }}
            if (optExt && optExt.checked) {{ total += parseInt(optExt.value); count++; }}
            
            document.getElementById("totalPriceDisplay").innerText = total.toLocaleString() + "원";
            if (count > 0) {{
                document.getElementById("statusDesc").innerText = "선택된 대행 서비스 총 " + count + "건";
                document.getElementById("payBtn").innerText = "결제하기";
                document.getElementById("payBtn").style.backgroundColor = "#ff4b4b";
            }} else {{
                document.getElementById("statusDesc").innerText = "필요한 서비스를 선택해 주세요.";
                document.getElementById("payBtn").innerText = "옵션을 선택해주세요";
                document.getElementById("payBtn").style.backgroundColor = "#333333";
            }}
        }}
        
        updatePrice();
        
        function handlePayAction() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            const optExt = document.getElementById("svc_opt_ext");
            
            let total = 0;
            let items = [];
            let addMonths = 0;
            if (opt1.checked) {{ total += parseInt(opt1.value); items.push(opt1.getAttribute("data-name")); }}
            if (opt2.checked) {{ total += parseInt(opt2.value); items.push(opt2.getAttribute("data-name")); }}
            if (opt3.checked) {{ total += parseInt(opt3.value); items.push(opt3.getAttribute("data-name")); }}
            if (optExt && optExt.checked) {{ total += parseInt(optExt.value); items.push(optExt.getAttribute("data-name")); addMonths = 1; }}
            
            if (total === 0) {{
                alert("결제하실 부가 서비스 대행 옵션을 하나 이상 선택해주세요.");
                return;
            }}
            
            if ({is_logged_in}) {{
                openPaymentWindow(total, items.join(", "), addMonths);
            }} else {{
                redirectSignup();
            }}
        }}
        
        function redirectSignup() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('로그인 또는 회원가입이 필요합니다. 메인 탭이나 사이드바를 통해 로그인/가입을 진행해주세요.');
            window.parent.scrollTo(0, 0);
        }}
        
        function openPaymentWindow(amount, planName, addMonths) {{
          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("팝업 차단이 설정되어 있습니다. 팝업 차단을 해제해주세요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>안전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈을 안전하게 불러오는 중입니다...</h3>
              <p>이 창을 닫지 마세요.</p>
            </body>
            </html>
          `);
          win.document.close();
          
          let baseOrigin = window.location.origin;
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          
          const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 서비스: " + planName);
          
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 띄우는 중입니다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "부가 서비스: " + planName + " - {safe_email}",
              totalAmount: amount,
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "사용자",
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 실패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 창 호출 중 오류가 발생했습니다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 실패! 인터넷 연결을 확인하세요.";
          }};
          win.document.head.appendChild(script);
        }}
      </script>
    </body>
    </html>
    """