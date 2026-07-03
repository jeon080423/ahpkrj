import urllib.parse
import requests
import streamlit as st

# ---------------------------------------------------------
# 구글 로그인 API 설정 (발급받은 키 적용)
# ---------------------------------------------------------
GOOGLE_CLIENT_ID = "13428899528-m3pqn23is4e5ui2pete8a6434u78rrd9.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

def get_redirect_uri():
    """현재 실행 중인 환경(로컬/운영)에 맞는 리다이렉트 URI 반환"""
    # Streamlit Cloud 등에서는 st.query_params 나 환경 변수를 활용할 수도 있지만, 
    # 보통 localhost로 테스트 중인지 여부로 구분합니다.
    # 단순화를 위해 일단 Streamlit Cloud 배포 주소를 기본으로 하되, 
    # 로컬 테스트 시에는 localhost를 사용하도록 처리 가능합니다.
    # 가장 안전한 방법은 두 환경을 모두 지원하도록 분기하는 것입니다.
    # 지금은 앱 구동 환경을 정확히 알기 어려우므로, 배포 도메인을 기본으로 합니다.
    # 만약 로컬에서 튕긴다면 이 값을 'http://localhost:8501'로 변경하세요.
    return "https://ahpkrj.streamlit.app"

def get_google_auth_url(redirect_uri):
    """구글 로그인 페이지 URL을 생성합니다."""
    scope = "email profile"
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope={urllib.parse.quote(scope)}&state=google"
    return auth_url

def get_google_user_info(code, redirect_uri):
    """콜백으로 받은 코드를 이용해 구글 유저 정보(이메일)를 가져옵니다."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    # 1. Access Token 획득
    res = requests.post(token_url, data=data)
    if res.status_code != 200:
        return {"error": f"Failed to get token: {res.text}"}
        
    access_token = res.json().get("access_token")
    if not access_token:
        return {"error": "No access token in response"}
        
    # 2. 유저 정보 획득
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_res = requests.get(user_info_url, headers=headers)
    
    if user_res.status_code != 200:
        return {"error": f"Failed to get user info: {user_res.text}"}
        
    return user_res.json() # contains 'email', 'name', etc.
