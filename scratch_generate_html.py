import os
import base64

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
    # Determine mime type from extension
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    return f"data:{mime};base64,{encoded_string}"

def create_html():
    output_dir = "AHP마스터 블로그"
    img1 = os.path.join(output_dir, "screenshot1_tab2.png")
    img2 = os.path.join(output_dir, "screenshot2_tab2.png")
    img3 = os.path.join(output_dir, "screenshot3_tab2.png")
    html_path = os.path.join(output_dir, "AHP 상대비료 온라인 설문 작성 및 배포 무료.html")
    
    img1_b64 = get_base64_image(img1)
    img2_b64 = get_base64_image(img2)
    img3_b64 = get_base64_image(img3)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>AHP 상대비료 온라인 설문 작성 및 배포 무료</title>
    <style>
        body {{
            font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        p {{
            margin-bottom: 15px;
            font-size: 16px;
        }}
        .image-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .image-container img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .caption {{
            font-size: 14px;
            color: #666;
            margin-top: 10px;
            font-weight: bold;
        }}
        .highlight {{
            font-weight: bold;
            color: #e74c3c;
        }}
        .link-box {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin: 30px 0;
        }}
        .link-box a {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
        }}
        .link-box a:hover {{
            text-decoration: underline;
        }}
        .hashtags {{
            color: #7f8c8d;
            font-size: 15px;
            margin-top: 40px;
            word-spacing: 5px;
        }}
    </style>
</head>
<body>

    <h1>AHP 상대비료 온라인 설문 작성 및 배포 무료</h1>

    <p>최근 의사결정 계층화 분석법(AHP, Analytic Hierarchy Process)을 활용한 논문 작성 및 기업 내 의사결정 수요가 꾸준히 증가하고 있습니다. AHP 설문지는 일반적인 리커트 척도 설문과는 달리, 요소 간의 상대적인 중요도를 쌍대비교(Pairwise Comparison)하는 방식으로 구성되어야 하므로 직접 설문 폼을 제작하기가 매우 까다롭습니다.</p>

    <p>하지만 이제 'AHP 마스터' 애플리케이션의 <span class="highlight">온라인 설문 작성 및 배포 기능</span>을 이용하면 이러한 고민을 완벽하게 해결할 수 있습니다. 본 글에서는 해당 기능의 유용성과 놀라운 편의성에 대해 상세히 안내해 드립니다.</p>

    <h2>1. 비회원도 누구나! 무료로 체험하는 설문지 자동 생성</h2>
    <p>가장 큰 장점 중 하나는 별도의 비용이나 복잡한 가입 절차 없이, 웹사이트에 접속하는 것만으로 누구나 AHP 설문지 폼을 직접 작성해보고 미리보기 기능까지 경험할 수 있다는 점입니다. 1계층과 2계층의 평가 지표만 입력하면, 시스템이 알아서 가능한 모든 조합의 쌍대비교 문항을 생성해 줍니다.</p>

    <div class="image-container">
        <img src="{img1_b64}" alt="비회원도 접근 가능한 온라인 설문 작성 탭과 친절한 안내 화면">
        <div class="caption">▲ 비회원도 접근 가능한 온라인 설문 작성 탭과 친절한 안내 화면</div>
    </div>

    <div class="image-container">
        <img src="{img2_b64}" alt="계층 지표 입력 시 자동으로 쌍대비교 문항이 구성되는 편리한 UI">
        <div class="caption">▲ 계층 지표 입력 시 자동으로 쌍대비교 문항이 구성되는 편리한 UI</div>
    </div>

    <h2>2. 구글 스프레드시트와의 강력한 실시간 연동</h2>
    <p>설문지 폼 작성을 마쳤다면, 버튼 클릭 한 번으로 배포용 URL이 생성됩니다. 이 URL을 카카오톡이나 이메일 등으로 응답자들에게 전달하기만 하면 됩니다. 응답자들이 설문을 제출하면, 그 결과가 내 구글 스프레드시트에 실시간으로 차곡차곡 쌓이게 되어 별도의 데이터 취합 과정이 전혀 필요하지 않습니다.</p>

    <h2>3. 단 한 번의 가입으로 누리는 '작성 내용 자동 보존' 기능</h2>
    <p>비회원 상태에서 정성껏 입력한 설문 문항들이 날아갈까 걱정하지 않으셔도 됩니다. 폼 작성 도중에 화면을 닫지 않고 바로 사이드바를 통해 무료 회원가입을 완료하면, 방금 전까지 입력했던 모든 내용이 마법처럼 그대로 유지됩니다. 가입 직후 즉시 [배포 및 DB 연동] 버튼을 눌러 설문을 시작할 수 있는 최적의 사용자 경험(UX)을 제공합니다.</p>

    <h2>4. 논문 통과를 보장하는 '응답 일관성(CR) 보조 기능'</h2>
    <p>AHP 설문의 가장 큰 진입 장벽은 응답자의 논리적 일관성을 나타내는 CR(Consistency Ratio) 수치입니다. 응답자가 A가 B보다 중요하고 B가 C보다 중요하다고 응답했는데, C가 A보다 중요하다고 체크한다면 논리적 모순이 발생하여 해당 데이터는 논문에 사용할 수 없게 됩니다.</p>
    
    <p>'AHP 마스터'는 관리자가 허용할 CR 한계치를 미리 지정하고, 응답자가 모순된 응답을 했을 때 실시간으로 경고를 보내거나 '스마트 보정 마법사'를 띄워 가장 모순된 문항을 스스로 고치도록 안내합니다. 이로 인해 분석 가능한 유효 응답률을 획기적으로 끌어올릴 수 있습니다.</p>

    <div class="image-container">
        <img src="{img3_b64}" alt="응답 일관성(CR) 한계치 및 스마트 가이드 설정 화면">
        <div class="caption">▲ 응답 일관성(CR) 한계치 및 스마트 가이드 설정 화면</div>
    </div>

    <p>지금 바로 'AHP 마스터'에 접속하여 무료로 제공되는 막강한 설문 배포 및 데이터 수집 기능을 직접 경험해 보세요. 연구와 업무의 효율성이 비약적으로 향상될 것입니다!</p>

    <div class="link-box">
        🌐 AHP 마스터 바로가기: <a href="https://ahpkrj.streamlit.app/" target="_blank">https://ahpkrj.streamlit.app/</a>
    </div>

    <div class="hashtags">
        #AHP #AHP마스터 #쌍대비교 #설문조사 #논문작성 #의사결정 #설문지자동생성 #무료설문지
    </div>

</body>
</html>
"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"HTML post created at {html_path}")

if __name__ == "__main__":
    create_html()
