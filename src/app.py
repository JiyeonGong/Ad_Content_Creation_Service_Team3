# 기본 코드
# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\app.py
import streamlit as st

st.set_page_config(layout="wide")

st.title(" 소상공인을 위한 광고 콘텐츠 생성 서비스 🚀")
st.write("Docker 환경에서 성공적으로 실행되었습니다.")
st.write(f"현재 사용자님의 환경(macOS)과 GCP 서버, 다른 팀원들의 PC 모두 이 동일한 환경을 바라보고 있습니다.")

if st.button("테스트 버튼"):
    st.success("작동 확인!")