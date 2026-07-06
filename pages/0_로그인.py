import streamlit as st

from api_client import create_profile, get_profile, virtual_user_id
from ui_theme import PALETTE as P
from ui_theme import apply_theme, has_required_consent, render_sidebar, render_topbar, resolve_page

st.set_page_config(page_title="로그인 · 마음숲", page_icon="🔐", layout="wide")
apply_theme()
render_sidebar(active="login")
render_topbar()

st.markdown(f"""
<span class="ac-chip chip-leaf">🔐 마을 입구</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">마음숲에 오신 걸 환영해요</h1>
""", unsafe_allow_html=True)

with st.container(border=True):
    email = st.text_input("이메일", placeholder="test@example.com")

    if st.button("🚪 마을 입장하기", type="primary"):
        if not email:
            st.error("이메일을 입력해주세요.")
            st.stop()

        st.session_state.user_email = email   # 표시용
        st.session_state.user_id = virtual_user_id(email)      # 가상 ID — 이후 모든 호출의 x-user-id
        st.query_params["uid"] = st.session_state.user_id      # 새로고침해도 로그인 유지(3번 항목)
        st.session_state.is_logged_in = True
        
        profile = get_profile() or create_profile()
        st.session_state.user_profile = profile

        if has_required_consent():
            st.success("로그인 완료. 기존 프로필을 불러왔습니다.")
        else:
            st.info("로그인 완료. 채팅, 마음 일기 등 서비스를 이용하려면 사전 질문에서 필수 동의를 먼저 완료해주세요.")
        st.rerun()

    if st.session_state.get("is_logged_in"):
        st.divider()
        if not has_required_consent():
            st.write("**서비스를 이용하려면 사전 질문의 필수 동의 항목을 완료해야 해요.** "
                     "(나머지 답변 항목은 비워두셔도 됩니다)")
            if st.button("📝 지금 사전 질문 하러 가기", use_container_width=True):
                st.switch_page(resolve_page("pages/4_설문.py"))
        else:
            st.success("사전 질문(필수 동의)이 완료된 계정이에요.")
            if st.button("💬 대화하러 가기", use_container_width=True):
                st.switch_page(resolve_page("pages/1_채팅.py"))
