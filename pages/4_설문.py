import streamlit as st

from api_client import submit_survey
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, resolve_page

st.set_page_config(page_title="설문 · 마음숲", page_icon="📝", layout="wide")
apply_theme()
render_sidebar(active="survey")
render_topbar()

if not st.session_state.get("is_logged_in"):
    st.warning("먼저 로그인해주세요.")
    if st.button("🔐 로그인하러 가기"):
        st.switch_page(resolve_page("pages/0_로그인.py"))
    st.stop()

st.markdown(f"""
<span class="ac-chip chip-lilac">📝 사전 설문</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">조금 더 알려주실래요?</h1>
<p style="margin:0 0 1.4rem;font-size:.87rem;color:{P['muted_fg']};">
답변하시면 상황에 더 맞는 안내를 드릴 수 있어요. 원치 않는 항목은 비워두셔도 됩니다.</p>
""", unsafe_allow_html=True)

SIDO_LIST = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시",
    "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
    "경기도", "강원특별자치도", "충청북도", "충청남도",
    "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
]

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">🏡 기본 정보</div>', unsafe_allow_html=True)
    nickname = st.text_input("닉네임", value="익명사용자")
    sido = st.selectbox("거주 시/도", SIDO_LIST)
    sigungu = st.text_input("시/군/구", placeholder="예: 전주시, 양산시")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">📞 비상연락처 (선택)</div>', unsafe_allow_html=True)
    emergency_name = st.text_input("이름", placeholder="예: 보호자")
    emergency_relationship = st.selectbox("관계", ["가족", "친구", "지인", "상담자", "기타"])
    emergency_phone = st.text_input("전화번호", placeholder="010-0000-0000")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">🗨️ 상담 관련 (선택)</div>', unsafe_allow_html=True)
    prior_counseling = st.selectbox("기존 상담 경험", ["응답하지 않음", "없음", "있음"])
    prior_diagnosis = st.selectbox("기존 진단/치료 경험", ["응답하지 않음", "없음", "있음"])
    current_support = st.selectbox("현재 도움받는 사람/기관", ["응답하지 않음", "없음", "있음"])
    conversation_depth = st.selectbox(
        "어느 정도로 이야기하고 싶어요?",
        ["잘 모르겠어요", "가볍게", "자세히"],
    )
    preferred_help = st.multiselect(
        "위기 상황에서 선호하는 도움 방식",
        ["비상연락처 표시", "가까운 기관 안내", "긴급전화 표시"],
        default=["가까운 기관 안내", "긴급전화 표시"],
    )

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">🔒 동의</div>', unsafe_allow_html=True)
    agreed_terms = st.checkbox("서비스 이용을 위한 기본 정보 저장에 동의합니다. (필수)")
    agreed_sensitive = st.checkbox("비상연락처 및 상담 관련 정보 저장에 동의합니다. (필수)")
    allow_contact_display = st.checkbox("위기 상황에서 등록한 비상연락처를 화면에 표시하는 것에 동의합니다. (선택)")
    allow_location_use = st.checkbox("위기 상황에서 위치 정보(GPS)를 활용해 가까운 기관을 자동으로 안내받는 것에 동의합니다. (선택)")
    st.caption("위치 동의는 언제든 바꿀 수 있어요. 동의하지 않아도 채팅에서 직접 지역을 선택해 안내받을 수 있어요.")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

if st.button("💾 저장하기", type="primary"):
    if not agreed_terms or not agreed_sensitive:
        st.error("필수 동의 항목을 확인해주세요.")
        st.stop()

    payload = {
        "nickname": nickname,
        "location": {"sido": sido, "sigungu": sigungu or None},
        "emergency_contact": {
            "name": emergency_name or None,
            "relationship": emergency_relationship,
            "phone": emergency_phone or None,
            "consent_to_show": allow_contact_display,
        },
        "survey": {
            "prior_counseling": prior_counseling,
            "prior_diagnosis_or_treatment": prior_diagnosis,
            "current_support": current_support,
            "conversation_depth": conversation_depth,
            "preferred_help": preferred_help,
        },
        "privacy": {
            "agreed_terms": agreed_terms,
            "agreed_sensitive_profile": agreed_sensitive,
            "allow_emergency_contact_display": allow_contact_display,
            "allow_location_use": allow_location_use,
        },
    }

    try:
        saved = submit_survey(payload)
        st.session_state.user_profile = saved
        st.success("프로필이 저장되었습니다.")
        st.balloons()
    except Exception as e:
        st.error(f"저장 실패: {e}")