import streamlit as st

from api_client import submit_survey
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, resolve_page

st.set_page_config(page_title="사전 질문 · 마음숲", page_icon="📝", layout="wide")
apply_theme()
render_sidebar(active="survey")
render_topbar()

if not st.session_state.get("is_logged_in"):
    st.warning("먼저 로그인해주세요.")
    if st.button("🔐 로그인하러 가기"):
        st.switch_page(resolve_page("pages/0_로그인.py"))
    st.stop()

st.markdown(f"""
<span class="ac-chip chip-lilac">📝 사전 질문</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">조금 더 알려주실래요?</h1>
<p style="margin:0 0 1.4rem;font-size:.87rem;color:{P['muted_fg']};">
답변하시면 상황에 더 맞는 안내를 드릴 수 있어요. 아래 필수 동의 항목만 체크하면
나머지 항목은 비워두셔도 서비스를 이용할 수 있어요.</p>
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
    st.caption("여기 적는 분은 본인이 아니라 제3자예요. 아래 '동의' 항목에서 그분께 미리 알리고 "
               "동의를 받았는지 확인해주세요.")

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

# ══════════════════════════════════════════════════════════════════
# AI 서비스 이용 안내 (신규 — 책임성 고지)
# 전문을 스크롤 박스에 넣고, 그 박스 맨 아래에만 있는 "여기까지 다 읽었어요" 버튼을
# 눌러야 동의 체크박스가 활성화된다(그 전까지는 disabled=True로 물리적으로 잠김).
# 커스텀 JS 컴포넌트 없이 순수 Streamlit 위젯 배치만으로 "끝까지 읽어야 다음 단계로
# 넘어간다"는 걸 강제한다 — 버튼이 스크롤 맨 밑에 있어서 안 내리면 아예 안 보이고 못 누른다.
# ══════════════════════════════════════════════════════════════════

AI_NOTICE_TEXT = """
**1. 이 서비스는 AI가 답변을 자동으로 만들어요**

마음갈피의 답변(생각 재구성, 공감 표현 등)은 Azure OpenAI 기반 대규모 언어모델이
자동으로 생성합니다. 사람 상담사가 실시간으로 작성하는 답변이 아니며, 문맥을
오해하거나 부정확한 내용을 포함할 수 있습니다.

**2. 인지왜곡 분류에 사용한 데이터**

발화에서 인지왜곡 유형(과잉일반화, 흑백사고 등)을 찾아내는 분류 모델은 KoACD
공개 데이터셋(청소년 인지왜곡 발화 약 10만 건, 10개 유형)으로 학습했습니다.
답변을 재구성할 때는 청소년 상담(KYCI), 위기대응(ASIST), CBT 관련 전문 자료를
참고 자료(RAG)로 함께 사용합니다.

**3. 의료적 진단·치료가 아니에요**

본 서비스는 정신건강 전문가의 진단, 치료, 상담을 대체하지 않습니다. 의학적
판단이 필요한 상황이라면 반드시 정신건강의학과, 심리상담센터 등 전문가와
상담해주세요. 자해·자살 위기 상황에서는 Azure AI Content Safety가 감지해
긴급 연락처를 안내하지만, 이 또한 전문 기관의 실제 개입을 대신하지 않습니다.

**4. 참고자료로만 활용하고, 책임은 본인에게 있어요**

AI가 만든 답변에는 오류나 편향이 있을 수 있습니다. 답변 내용은 스스로 생각을
점검해보는 참고 자료로 활용해주시고, 이를 바탕으로 한 판단이나 행동에 대한
책임은 이용자 본인에게 있음을 이해해주세요.

**5. 오작동·오분류 시**

인지왜곡이 잘못 분류되거나 답변이 부적절하다고 느껴지면 언제든 대화를 중단하고
전문가 상담이나 하단에 안내되는 긴급 연락처를 이용해주세요. 서비스 개선을 위해
관련 문의는 팀에 남겨주시면 감사하겠습니다.
"""

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">🤖 AI 서비스 이용 안내 (꼭 확인해주세요)</div>',
               unsafe_allow_html=True)
    with st.container(height=220, border=True):
        st.markdown(AI_NOTICE_TEXT)
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        # 이 버튼은 스크롤 박스 맨 아래에 있어서, 실제로 끝까지 스크롤해야 보이고 눌린다.
        # (커스텀 JS 컴포넌트 없이도 순수 Streamlit 위젯만으로 "끝까지 읽어야 다음 단계로
        #  넘어간다"는 걸 물리적으로 강제하는 방식 — 버튼이 안 보이면 누를 수가 없다.)
        if st.session_state.get("_ai_notice_read"):
            st.caption("✅ 여기까지 확인했어요.")
        else:
            if st.button("🔽 여기까지 다 읽었어요", key="ai_notice_read_btn", use_container_width=True):
                st.session_state["_ai_notice_read"] = True
                st.rerun()

    ai_notice_read = st.session_state.get("_ai_notice_read", False)
    agreed_ai_notice = st.checkbox(
        "위 AI 서비스 이용 안내 전문을 확인했으며, 내용을 이해하고 동의합니다. (필수)",
        disabled=not ai_notice_read,
        key="agreed_ai_notice_cb",
    )
    if not ai_notice_read:
        st.caption("⬆️ 위 박스를 끝까지 스크롤해서 맨 아래 '여기까지 다 읽었어요' 버튼을 눌러야 체크할 수 있어요.")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="font-display" style="margin-bottom:.6rem;">🔒 동의</div>', unsafe_allow_html=True)
    agreed_terms = st.checkbox(
        "닉네임, 거주지역 등 기본 정보의 수집 및 이용(상담 서비스 제공 목적)에 동의합니다. (필수)")
    agreed_sensitive = st.checkbox(
        "비상연락처 및 상담 관련 정보의 수집 및 이용(위기 대응 목적)에 동의합니다. (필수)")

    has_emergency_contact = bool((emergency_name or "").strip() or (emergency_phone or "").strip())
    if has_emergency_contact:
        agreed_emergency_third_party = st.checkbox(
            "위에 입력한 비상연락처 대상자(제3자)에게 정보 저장 사실을 미리 알리고, "
            "위기 상황 시 연락될 수 있음에 대한 동의를 받았습니다. (필수 — 비상연락처를 입력한 경우)")
    else:
        agreed_emergency_third_party = True  # 비상연락처를 입력하지 않았다면 해당 사항 없음

    allow_contact_display = st.checkbox("위기 상황에서 등록한 비상연락처를 화면에 표시하는 것에 동의합니다. (선택)")
    allow_location_use = st.checkbox("위기 상황에서 위치 정보(GPS)를 활용해 가까운 기관을 자동으로 안내받는 것에 동의합니다. (선택)")
    st.caption("위치 동의는 언제든 바꿀 수 있어요. 동의하지 않아도 채팅에서 직접 지역을 선택해 안내받을 수 있어요.")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)


def _build_payload() -> dict:
    return {
        "nickname": nickname,
        "location": {"sido": sido, "sigungu": sigungu or None},
        "emergency_contact": {
            "name": emergency_name or None,
            "relationship": emergency_relationship,
            "phone": emergency_phone or None,
            "consent_to_show": allow_contact_display,
            "third_party_consent_confirmed": agreed_emergency_third_party if has_emergency_contact else None,
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
            "agreed_ai_notice": agreed_ai_notice,
            "agreed_emergency_third_party": agreed_emergency_third_party,
            "allow_emergency_contact_display": allow_contact_display,
            "allow_location_use": allow_location_use,
        },
    }


# ══════════════════════════════════════════════════════════════════
# 최종 확인 팝업 (이중 동의) — "저장하기"를 눌러도 바로 저장되지 않고,
# 한 번 더 요약을 보여준 뒤 명시적으로 확인해야 실제로 저장된다.
# ══════════════════════════════════════════════════════════════════

@st.dialog("최종 확인")
def confirm_and_submit_dialog():
    st.markdown("아래 내용으로 저장할게요. 다시 한 번 확인해주세요.")
    st.markdown(f"- **닉네임**: {nickname}")
    st.markdown(f"- **거주지역**: {sido} {sigungu or ''}".rstrip())
    if has_emergency_contact:
        st.markdown(f"- **비상연락처**: {emergency_name or '(이름 없음)'} ({emergency_relationship}) "
                    f"— 대상자 동의 확인: {'예' if agreed_emergency_third_party else '아니오'}")
    st.markdown(f"- **AI 서비스 이용 안내 확인**: {'예' if agreed_ai_notice else '아니오'}")
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("취소", use_container_width=True):
            st.session_state["_survey_confirm_open"] = False
            st.rerun()
    with c2:
        if st.button("예, 동의하고 저장합니다", type="primary", use_container_width=True):
            try:
                saved = submit_survey(_build_payload())
                st.session_state.user_profile = saved
                st.session_state["_survey_saved_ok"] = True
            except Exception as e:
                st.session_state["_survey_save_error"] = str(e)
            st.session_state["_survey_confirm_open"] = False
            st.rerun()


if st.button("💾 저장하기", type="primary"):
    missing = []
    if not agreed_terms:
        missing.append("기본 정보 수집·이용 동의")
    if not agreed_sensitive:
        missing.append("비상연락처/상담 정보 수집·이용 동의")
    if not agreed_ai_notice:
        missing.append("AI 서비스 이용 안내 확인·동의")
    if has_emergency_contact and not agreed_emergency_third_party:
        missing.append("비상연락처 대상자 동의 확인")

    if missing:
        st.error("다음 필수 동의 항목을 확인해주세요: " + ", ".join(missing))
    else:
        st.session_state["_survey_confirm_open"] = True

if st.session_state.get("_survey_confirm_open"):
    confirm_and_submit_dialog()

if st.session_state.get("_survey_saved_ok"):
    st.success("프로필이 저장되었습니다. 이제 채팅과 마음 일기 등 모든 서비스를 이용할 수 있어요.")
    st.balloons()
    if st.button("💬 대화하러 가기", key="survey_go_chat_btn"):
        st.session_state.pop("_survey_saved_ok", None)
        st.switch_page(resolve_page("pages/1_채팅.py"))

if st.session_state.get("_survey_save_error"):
    st.error(f"저장 실패: {st.session_state.pop('_survey_save_error')}")
