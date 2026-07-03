import streamlit as st

from api_client import create_profile, get_profile
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, resolve_page

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
        st.session_state.is_logged_in = True

        profile = get_profile() or create_profile()
        st.session_state.user_profile = profile

        if profile.get("survey_completed"):
            st.success("로그인 완료. 기존 프로필을 불러왔습니다.")
        else:
            st.info("로그인 완료. 맞춤 응답을 위한 선택 설문이 있습니다 — 건너뛰어도 됩니다.")
        st.rerun()

    if st.session_state.get("is_logged_in"):
        profile = st.session_state.get("user_profile") or {}
        st.divider()
        if not profile.get("survey_completed"):
            st.write("**답변하시면 상황에 더 맞는 안내를 드릴 수 있어요.** (선택, 나중에 하셔도 됩니다)")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📝 지금 설문하기", use_container_width=True):
                    st.switch_page(resolve_page("pages/4_설문.py"))
            with c2:
                if st.button("💬 나중에 하기", use_container_width=True):
                    st.switch_page(resolve_page("pages/1_채팅.py"))
        else:
            st.success("설문이 완료된 계정이에요.")
            if st.button("💬 대화하러 가기", use_container_width=True):
                st.switch_page(resolve_page("pages/1_채팅.py"))