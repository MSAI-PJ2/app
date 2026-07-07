import base64
import uuid
from collections import Counter
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from api_client import respond_stream, respond_stream_audio, respond_stream_image
from get_centers import get_centers, get_sigungu_list
from kakao_geo import coords_to_address
from streamlit_geolocation import streamlit_geolocation
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, require_consent, safe_bubble_text

load_dotenv()

st.set_page_config(page_title="대화하기 · 마음숲", page_icon="💬", layout="wide")
apply_theme()
render_sidebar(active="chat")
render_topbar()

# 로그인 + 필수 개인정보 동의(사전 질문) 없이는 채팅 자체를 이용할 수 없음
require_consent()

# ── 우측 패널 고정 (팀 피드백: "채팅에서 우측 스크롤되지 않게") ──────
# 채팅이 길어지면 우측 패널(처리 단계/왜곡/위기 카드)이 같이 위로 밀려
# 사라지는 문제 → position: sticky 로 화면에 고정한다.
# ⚠️ ui_theme.py 전역 규칙 두 개가 sticky 를 무력화하므로 이 페이지에서만 덮어씀:
#   1) stHorizontalBlock 의 align-items: stretch → 컬럼이 반대편 높이만큼
#      늘어나 버리면 sticky 가 움직일 여백이 없음 → flex-start 로.
#   2) stColumn 내부 div 전부 height:100% → sticky 컨테이너 높이 계산이
#      깨짐 → auto 로 되돌림.
# (2026-07-06 참고: ui_theme.py의 이 두 전역 규칙은 홈 화면 카드 전용으로
#  .st-key-home_hero_row/.st-key-home_menu_row 안으로 스코프를 좁혔지만,
#  stHorizontalBlock의 align-items:stretch는 flexbox 자체의 기본 동작이라
#  이 페이지 전용 override는 그대로 필요함)
# 이 페이지엔 topbar/빠른답장 칩 등 다른 st.columns 도 있어서, 우측 패널에만
# 존재하는 .pipeline-step 을 :has() 앵커로 써서 정확히 그 컬럼만 잡는다.
st.markdown("""
<style>
/* 1) flex-start로 컬럼이 끝까지 늘어나지 않고 sticky가 작동할 공간 확보 */
div[data-testid="stHorizontalBlock"]:has(.pipeline-step) { align-items: flex-start !important; }

/* 2) 컨테이너 높이 계산 정상화를 위해 auto로 설정 */
div[data-testid="stColumn"]:has(.pipeline-step) div { height: auto !important; }

/* 3) 오른쪽 컬럼을 화면에 고정하는 핵심 코드 */
div[data-testid="stColumn"]:has(.pipeline-step) {
    position: -webkit-sticky !important; /* Safari 호환성 */
    position: sticky !important;
    top: 5rem !important; /* 상단 메뉴(Top bar) 높이에 맞춰 조절 (예: 80px, 4rem 등) */
    z-index: 100; /* 다른 요소에 가려지지 않도록 설정 */
    transition: top 0.3s ease; /* 부드러운 전환 효과 */
}
</style>
""", unsafe_allow_html=True)

# 인지왜곡 분류기의 라우팅 전용 라벨 — 사용자에게 "왜곡"으로 보여주면 안 됨
# ('정상'은 왜곡이 없다는 뜻, '불충분'은 판단하기엔 정보가 부족하다는 뜻)
NON_DISTORTION_LABELS = ("정상", "불충분")

SIDO_OPTIONS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

# ── 세션 상태 ─────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())  # 게이트웨이 대화 세션 ID (Cosmos session_id 로 저장됨)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "distortion_history" not in st.session_state:
    st.session_state.distortion_history = []
if "awaiting_location" not in st.session_state:
    st.session_state.awaiting_location = False
if "user_location" not in st.session_state:
    st.session_state.user_location = None  # {"sido":..., "sigungu":...} 세션 내 재사용
if "queued_input" not in st.session_state:
    st.session_state.queued_input = None   # 빠른 답장 칩 → 메시지 큐
if "input_widget_seq" not in st.session_state:
    st.session_state.input_widget_seq = 0


def render_crisis_result(result: dict):
    """get_centers() 결과 표시 (변경 없음 — 고대비 유지)"""
    em = result["emergency_numbers"]
    em_html = "".join([f"<div><b>{num}</b> — {desc}</div>" for num, desc in em.items()])
    st.markdown(f'<div class="emergency-box">🚨 <b>비상연락처 (24시간)</b><br>{em_html}</div>', unsafe_allow_html=True)

    if result["night_mode"]:
        st.caption("🌙 현재 야간/주말 시간대 — 광역 단위 기관만 표시됩니다")

    for c in result["centers"]:
        types = "+".join(c.get("_merged_types", [c["유형"]]))
        info = c.get("_type_info", {})
        st.markdown(f"""
<div class="center-card">
<b>{c['기관명']}</b> <span class="distortion-badge">{types}</span><br>
📞 <a href="tel:{c['전화']}">{c['전화']}</a><br>
<small>{info.get('tagline','')} — {info.get('description','')}</small>
</div>""", unsafe_allow_html=True)

    if result["foundation"]:
        f = result["foundation"]
        info = f.get("_type_info", {})
        st.markdown(f"""
<div class="center-card" style="border-left:4px solid #6B7280;">
<b>[정책기관] {f['기관명']}</b><br>
📞 <a href="tel:{f['전화']}">{f['전화']}</a><br>
<small>{info.get('tagline','')} — {info.get('description','')}</small>
</div>""", unsafe_allow_html=True)


# ── 레이아웃: [채팅 패널 | 사이드 패널] (chat.tsx grid 이식) ──────
# 처리 단계 패널은 항상 노출 (팀 결정: 심사/시연 시 내부 동작을 투명하게 보여주는 쪽으로 확정)
col_chat, col_side = st.columns([2, 1], gap="medium")

# ═══════════ 채팅 패널 ═══════════
with col_chat:
    # ⚠️ 구조 변경(2026-07-06, "무너진 대화하기 창 UI" 수정): 예전엔 chat-header/
    # chat-body/chat-footer 를 각각 별개의 st.markdown() 호출로 열고-닫았다.
    # Streamlit은 st.markdown() 호출마다 독립된 DOM 컨테이너를 만들기 때문에,
    # 열어놓은 <div>는 그 호출 하나의 컨테이너 안에서만 닫히고, 그 사이에 낀
    # 실제 위젯(st.button, st.chat_input, st.radio, st.expander 등)은 카드
    # 바깥의 형제 요소로 렌더링된다 — 카드가 빈 배경 박스로만 보이고 입력창/
    # 버튼이 카드 밖으로 떨어져 나오는 버그의 원인이었다.
    # → st.container(key="chat_card") 로 전체(헤더~구성기)를 하나의 진짜 DOM
    #   컨테이너로 묶고, CSS는 .st-key-chat_card 에 카드 스타일을 입힌다.
    with st.container(key="chat_card"):
        # 헤더 배너 — 이 div는 한 번의 st.markdown() 호출 안에서 열고 바로
        # 닫으므로 안전하다 (다른 위젯을 안에 담지 않음).
        st.markdown(f"""
<div class="chat-header">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:44px;height:44px;border-radius:16px;background:{P['cream']};
         display:flex;align-items:center;justify-content:center;font-size:20px;
         box-shadow:0 6px 20px -6px rgba(45,143,110,0.25);">🍃</div>
    <div>
      <div class="font-display" style="font-size:.95rem;">마음갈피 친구</div>
      <div style="font-size:.72rem;color:{P['muted_fg']};">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
              background:{P['leaf_deep']};vertical-align:middle;"></span>
        온라인 · 편지 쓰는 중…</div>
    </div>
  </div>
  <div style="display:flex;gap:6px;">
    <span class="ac-chip chip-leaf">🛡️ 안전</span>
    <span class="ac-chip chip-sunny">✨ OpenAI</span>
  </div>
</div>""", unsafe_allow_html=True)

        # 메시지 영역 (chat.tsx messages) — 아바타 + 말풍선 + 메타칩 + 시각
        # ⚠️ 메시지 전체를 문자열 하나로 합쳐서 한 번에 st.markdown() 하면, 답변
        # 하나의 구조 때문에 raw-HTML 블록 인식이 중간에 깨질 경우 그 뒤에 오는
        # 모든 메시지가 영향을 받는다(<div class="msg-time"> 코드 노출 버그).
        # 메시지마다 별도의 st.markdown() 호출로 렌더링해서 서로 완전히 격리시킨다.
        # (카드 배경은 이제 .st-key-chat_card 가 담당하므로 별도 래퍼 div 불필요)
        if not st.session_state.messages:
            st.markdown("""
<div class="msg-row">
  <div class="msg-avatar bot">🍃</div>
  <div class="msg-col">
    <div class="bubble bot">안녕하세요! 오늘은 어떤 마음이 마을에 놀러왔나요? 편지 쓰듯 편하게 적어주세요 🍃</div>
  </div>
</div>""", unsafe_allow_html=True)
        for msg in st.session_state.messages:
            time_str = msg.get("time", "")
            if msg["role"] == "user":
                # 카톡 캡쳐 업로드 메시지는 추출 텍스트 대신 업로드한 이미지를 버블에 그대로 보여준다
                body = (f'<img src="{msg["image"]}" alt="업로드한 카톡 캡쳐" '
                        f'style="max-width:240px;max-height:360px;border-radius:12px;display:block;" />'
                        if msg.get("image") else safe_bubble_text(msg["content"]))
                st.markdown(f"""
<div class="msg-row me">
  <div class="msg-col me">
    <div class="bubble me">{body}</div>
  </div>
  <div class="msg-avatar me">🐰</div>
</div>""", unsafe_allow_html=True)
                # ⚠️ 시간 표시는 raw HTML(<div class="msg-time">)이 아니라 Streamlit 네이티브
                # st.caption()으로 렌더링한다 — HTML 파싱 자체를 안 거치므로 태그가 텍스트로
                # 노출되는 버그가 구조적으로 발생할 수 없다. (디자인 손실: 우측 정렬은 못 함)
                st.caption(time_str)
            else:
                # 답변 밑에는 어떤 배지(왜곡 유형/신뢰도 등)도 표시하지 않음 — 사용자 요청으로
                # 전체 메타칩 제거. 왜곡 유형은 사이드 "처리 단계" 패널에서만 참고용으로 보여준다.
                st.markdown(f"""
<div class="msg-row">
  <div class="msg-avatar bot">🍃</div>
  <div class="msg-col">
    <div class="bubble bot">{safe_bubble_text(msg["content"])}</div>
  </div>
</div>""", unsafe_allow_html=True)
                st.caption(time_str)

        st.markdown('<div class="chat-footer-divider"></div>', unsafe_allow_html=True)

        # ── 위기 감지 후 위치 입력 대기 (GPS + selectbox 폴백) ──
        # crisis-card 도 같은 이유로 st.container(key="crisis_card")로 교체.
        if st.session_state.awaiting_location:
            with st.container(key="crisis_card"):
                st.markdown("📍 **가까운 기관을 안내해드릴게요.**")

                # 위치 동의는 사전 질문(4_설문.py)의 동의란에서 미리 받아둔 값을 사용 — 여기서 다시 묻지 않음
                _profile = st.session_state.get("user_profile") or {}
                location_consent = bool(_profile.get("privacy", {}).get("allow_location_use"))

                sido_gps, sigungu_gps = None, None
                if location_consent:
                    st.caption("사전 질문에서 위치 정보 사용에 동의하셨어요 — 자동으로 가까운 지역을 찾아드릴게요.")
                    location = streamlit_geolocation()

                    if location and location.get("latitude"):
                        lat, lon = location["latitude"], location["longitude"]
                        region = coords_to_address(lat, lon)
                        if region:
                            sido_gps = region["시도"]
                            sigungu_gps = region["시군구"]
                            st.success(f"📍 위치 자동 감지: {sido_gps} {sigungu_gps}")
                        else:
                            st.warning("좌표를 행정구역으로 변환하지 못했어요. 아래에서 직접 선택해주세요.")
                else:
                    st.caption("위치 정보 사용에 동의하지 않으셨어요. 아래에서 지역을 직접 선택해주세요. (사전 질문에서 동의하시면 다음부터는 자동으로 찾아드려요)")

                if sido_gps:
                    if st.button(f"📍 {sido_gps} {sigungu_gps} 기준으로 기관 찾기", key="crisis_gps_btn"):
                        st.session_state.user_location = {"sido": sido_gps, "sigungu": sigungu_gps}
                        result = get_centers(sido_gps, sigungu_gps, is_crisis=True)
                        st.session_state.last_crisis_result = result
                        st.session_state.awaiting_location = False
                        st.rerun()

                with st.expander("다른 지역으로 직접 선택하기" if sido_gps else "지역 직접 선택하기", expanded=not sido_gps):
                    sido = st.selectbox("시/도 선택", SIDO_OPTIONS, key="crisis_sido")
                    sigungu_options = ["전체"] + get_sigungu_list(sido)
                    sigungu_selected = st.selectbox("시/군/구 선택", sigungu_options, key="crisis_sigungu")
                    sigungu = None if sigungu_selected == "전체" else sigungu_selected

                    if st.button("이 지역으로 기관 찾기", key="crisis_search_btn"):
                        st.session_state.user_location = {"sido": sido, "sigungu": sigungu or None}
                        result = get_centers(sido, sigungu or None, is_crisis=True)
                        st.session_state.last_crisis_result = result
                        st.session_state.awaiting_location = False
                        st.rerun()

        # 직전 위기 결과 표시 (변경 없음)
        if st.session_state.get("last_crisis_result"):
            render_crisis_result(st.session_state.last_crisis_result)

        # composer — 입력 방식 선택 (텍스트/음성/카톡 캡쳐)
        input_mode = st.radio("입력 방식", ["✍️ 텍스트", "🎙️ 음성", "🖼️ 카톡 캡쳐"],
                              horizontal=True, label_visibility="collapsed", key="input_mode")

        user_input = None
        audio_value = None
        image_value = None
        if input_mode == "✍️ 텍스트":
            user_input = st.chat_input("마음갈피에게 편지를 써보세요…")
        elif input_mode == "🎙️ 음성":
            audio_value = st.audio_input("마이크로 말해보세요", key=f"audio_input_{st.session_state.input_widget_seq}")
        elif input_mode == "🖼️ 카톡 캡쳐":
            image_value = st.file_uploader("카톡 대화 캡쳐를 올려주세요", type=["png", "jpg", "jpeg"],
                                       key=f"image_uploader_{st.session_state.input_widget_seq}")
            kakao_sender = st.text_input("상대방 이름 (선택 — 있으면 화자 구분이 더 정확해요)", key="kakao_sender")

        # 대화 초기화 (변경 없음)
        if st.session_state.messages:
            if st.button("🗑️ 대화 초기화", type="secondary"):
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())  # 새 대화 = 새 Cosmos 세션
                st.session_state.awaiting_location = False
                st.session_state.last_crisis_result = None
                st.session_state.user_location = None
                st.session_state.pop("crisis_sido", None)
                st.session_state.pop("crisis_sigungu", None)
                st.rerun()

# ═══════════ 사이드 패널 (chat.tsx aside) ═══════════
with col_side:
    # 처리 단계 패널 (항상 노출 — 심사/시연 시 내부 동작을 투명하게 보여주는 쪽으로 팀 확정)
    st.markdown(f"""<div class="ac-card" style="padding:1.2rem 1.3rem 0.4rem;margin-bottom:0.45rem;">
    <div class="font-display" style="margin-bottom:6px;">🔄 처리 단계</div></div>""", unsafe_allow_html=True)
    pipeline_placeholder = st.empty()
    pipeline_placeholder.markdown("""
<div class="pipeline-step">⬜ ① 안전하게 살펴보는 중 (대기)</div>
<div class="pipeline-step">⬜ ② 생각 패턴 살펴보는 중 (대기)</div>
<div class="pipeline-step">⬜ ③ 답변 방식 정하는 중 (대기)</div>
<div class="pipeline-step">⬜ ④ 참고할 자료 찾는 중 (대기)</div>
<div class="pipeline-step">⬜ ⑤ 답변 준비하는 중 (대기)</div>
""", unsafe_allow_html=True)
    st.markdown('<div class="font-display" style="margin:8px 0 4px;">🏷️ 감지된 왜곡 유형</div>', unsafe_allow_html=True)
    distortion_placeholder = st.empty()
    distortion_placeholder.caption("입력 후 결과가 표시됩니다")
    st.markdown(f'<hr style="margin:.5rem 0;border:none;border-top:1px solid {P["border"]};">',
               unsafe_allow_html=True)

    # 최근 감지된 왜곡 — 이력 기반 프로그레스바 (chat.tsx 사이드 카드)
    # '불충분'은 인지왜곡이 아니라 라우팅 라벨이므로 이 통계에서 제외한다.
    hist = [h for h in st.session_state.distortion_history if h.get("distortion") not in NON_DISTORTION_LABELS]
    bar_tones = ["#E39A86", "#D9B8E8", "#C4DCEA", "#F3DD8F"]
    if hist:
        counts = Counter(h["distortion"] for h in hist).most_common(4)
        total = sum(c for _, c in counts) or 1
        rows = [(name, round(cnt / len(hist) * 100)) for name, cnt in counts]
    else:
        rows = [("과잉일반화", 0), ("잘못된 명명", 0), ("감정적 추론", 0), ("당위적 진술", 0)]

    bars = "".join(
        f"""<div style="display:flex;justify-content:space-between;font-size:.75rem;">
              <span style="font-weight:700;">{name}</span>
              <span style="color:{P['muted_fg']};">{pct}%</span></div>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{bar_tones[i % 4]};"></div></div>"""
        for i, (name, pct) in enumerate(rows)
    )
    st.markdown(f"""
<div class="ac-card" style="padding:1.3rem;margin-bottom:0.45rem;">
  <div class="font-display" style="margin-bottom:10px;">🧠 최근 감지된 왜곡</div>
  {bars}
  {'<div style="font-size:.72rem;color:' + P['muted_fg'] + ';">아직 대화 이력이 없어요</div>' if not hist else ''}
</div>""", unsafe_allow_html=True)

    # 🚨 위기 시 도움받기 (chat.tsx 사이드 카드 — 번호는 백엔드 EMERGENCY와 동일 체계)
    hotlines = [("자살예방 상담전화", "109"), ("정신건강 위기상담", "1577-0199"),
                ("응급·소방", "119"), ("경찰", "112")]
    lines = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
             padding:7px 16px;border-top:1px solid {P['border']};font-size:.85rem;">
             <span>{n}</span><a href="tel:{t}" class="font-display"
             style="color:{P['primary']};text-decoration:none;">{t}</a></div>"""
        for n, t in hotlines
    )
    st.markdown(f"""
<div class="ac-card" style="overflow:hidden;">
  <div style="background:rgba(227,154,134,0.22);padding:1rem 1.2rem;">
    <div class="font-display">🚨 위기 시 도움받기</div>
    <p style="margin:4px 0 0;font-size:.75rem;color:{P['muted_fg']};">
      힘든 마음이 크게 느껴진다면 언제든 연결할 수 있어요.</p>
  </div>
  {lines}
</div>""", unsafe_allow_html=True)


# ── 파이프라인 실행 (변경 없음 — 시각/메타 저장만 추가) ───────────
def render_pipeline(steps):
    labels = {"safety": "① 안전하게 살펴보는 중", "classify": "② 생각 패턴 살펴보는 중",
              "router": "③ 답변 방식 정하는 중", "rag": "④ 참고할 자료 찾는 중", "openai": "⑤ 답변 준비하는 중"}
    icons  = {"done": "✅", "processing": "⏳", "pending": "⬜", "error": "❌", "crisis": "🚨"}
    html = ""
    for key, (icon_key, status) in steps.items():
        css = "pipeline-step" + (" done" if status == "done" else " error" if status == "error" else " crisis" if status == "crisis" else "")
        html += f'<div class="{css}">{icons.get(icon_key,"⬜")} {labels[key]}</div>'
    pipeline_placeholder.markdown(html, unsafe_allow_html=True)


# 빠른 답장 칩으로 큐된 입력이 있으면 그것을 사용
if st.session_state.queued_input and not user_input:
    user_input = st.session_state.queued_input
    st.session_state.queued_input = None

if user_input:
    now_str = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": user_input, "time": now_str})
    st.session_state.last_crisis_result = None  # 새 메시지 → 이전 위기카드 비움
    steps = {k: ("⬜", "pending") for k in ["safety", "classify", "router", "rag", "openai"]}
    render_pipeline(steps)

    assistant_parts: list[str] = []
    primary = None
    confidence = 0.0
    is_crisis = False
    crisis_message = None
    error_message = None
    route = "STS"  # chunks 이벤트가 안 오면(예: crisis 분기) 기본값 유지

    # 게이트웨이 POST /v1/respond 를 호출해 SSE 이벤트를 순서대로 소비한다.
    # 2026-07-04 게이트웨이 업데이트로 단계 완료를 알려주는 progress 이벤트가 추가됐다.
    # meta/chunks 도착 시점으로 "단계가 끝났다"를 추측하던 이전 방식보다, 백엔드가 직접
    # 보내는 progress(stage) 신호를 쓰는 게 더 정확하다 — meta/chunks 는 이제 데이터만 담당.
    # 순서: progress(input) -> progress(analyze) -> meta -> chunks -> progress(route)
    #       -> token... -> progress(generate) -> [progress(speak)] -> done
    try:
        with st.spinner("마음갈피가 편지를 쓰는 중…"):
            for event in respond_stream(st.session_state.session_id, user_input):
                etype = event.get("type")

                if etype == "progress":
                    stage = event.get("stage")
                    if stage == "analyze":
                        # 안전점검 + 분류 + RAG 후보 검색이 동시에(gather) 끝난 시점
                        steps["safety"] = ("✅", "done")
                        steps["classify"] = ("✅", "done")
                        render_pipeline(steps)
                    elif stage == "route":
                        # 라우팅 결정 + 프롬프트 구성까지 끝난 시점
                        steps["router"] = ("✅", "done")
                        steps["rag"] = ("✅", "done")
                        steps["openai"] = ("⏳", "processing")
                        render_pipeline(steps)
                    elif stage == "generate":
                        steps["openai"] = ("✅", "done")
                        render_pipeline(steps)

                elif etype == "meta":
                    # 이제 단계 표시는 progress 가 담당 — meta 는 라벨/신뢰도 데이터만 취한다
                    primary = event.get("primary")
                    labels = event.get("labels") or []
                    confidence = next((l["score"] for l in labels if l["label"] == primary), 0.0)
                    if primary and primary not in NON_DISTORTION_LABELS:
                        distortion_placeholder.markdown(
                            f'<span class="distortion-badge">{primary}</span><br><small>신뢰도: {confidence:.0%}</small>',
                            unsafe_allow_html=True)
                    elif primary:  # '불충분'·'정상'은 인지왜곡이 아니므로 왜곡 유형으로 표시하지 않는다
                        distortion_placeholder.caption("감지된 인지왜곡 없음")

                elif etype == "crisis":
                    is_crisis = True
                    crisis_message = event.get("message") or "🚨 위기 상황이 감지되었습니다."
                    steps["safety"] = ("🚨", "crisis")
                    render_pipeline(steps)

                elif etype == "chunks":
                    # route 판정(RAG 사용 여부)만 취한다 — ✅ 표시는 progress(route) 가 이미 처리
                    route = "RAG" if event.get("chunks") else "STS"

                elif etype == "token":
                    assistant_parts.append(event.get("text", ""))

                elif etype == "input_required":
                    error_message = event.get("message") or "입력을 다시 확인해주세요."

                elif etype == "done":
                    break
    except Exception as e:
        error_message = f"게이트웨이 연결 오류: {e}"

    if error_message:
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error_message}", "time": now_str})
        st.rerun()

    if is_crisis:
        steps.update(router=("⬜", "pending"), rag=("⬜", "pending"), openai=("⬜", "pending"))
        render_pipeline(steps)
        st.session_state.messages.append({"role": "assistant", "content": crisis_message, "time": now_str})

        # 백엔드 crisis 이벤트(전국 공통 창구)와 별개로, 로컬 kfsp_centers 지역 기관 조회는 그대로 유지
        if st.session_state.user_location:
            loc = st.session_state.user_location
            st.session_state.last_crisis_result = get_centers(loc["sido"], loc["sigungu"], is_crisis=True)
        else:
            st.session_state.awaiting_location = True
        st.rerun()

    steps["openai"] = ("✅", "done")
    render_pipeline(steps)

    # route 는 위 루프의 chunks 이벤트에서 이미 정확히 설정됨(steps["rag"]는 이제
    # progress(route) 이벤트로 항상 done 이 되므로 여기서 재계산하면 안 됨 — 2026-07-04 수정)
    ai_response = "".join(assistant_parts).strip() or "응답을 생성하지 못했어요. 다시 시도해주세요."

    # 응답 저장 — Lovable 말풍선 메타칩용으로 meta 추가 (처리단계 패널과 함께 항상 노출)
    meta = {"distortion": primary, "confidence": confidence}
    st.session_state.messages.append({"role": "assistant", "content": ai_response,
                                      "time": datetime.now().strftime("%H:%M"), "meta": meta})
    if primary:
        st.session_state.distortion_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user_text": user_input,
            "distortion": primary,
            "confidence": confidence,
            "route": route,
        })
    st.rerun()
    
elif input_mode == "🎙️ 음성" and audio_value is not None:
    st.session_state.input_widget_seq += 1  # 위젯 key 갱신 → 다음 rerun에서 값 초기화(무한루프 방지)
    now_str = datetime.now().strftime("%H:%M")
    audio_bytes = audio_value.getvalue()
    st.session_state.messages.append({"role": "user", "content": "🎙️ (음성 메시지)", "time": now_str})
    st.session_state.last_crisis_result = None
    steps = {k: ("⬜", "pending") for k in ["safety", "classify", "router", "rag", "openai"]}
    render_pipeline(steps)

    transcript = None
    assistant_parts, primary, confidence = [], None, 0.0
    is_crisis, crisis_message, error_message = False, None, None
    route = "STS"
    try:
        with st.spinner("음성을 듣고 있어요…"):
            for event in respond_stream_audio(st.session_state.session_id, audio_bytes, "audio/wav"):
                etype = event.get("type")
                if etype == "stt":
                    if event.get("status") == "completed":
                        transcript = event.get("transcript")
                        if transcript:
                            st.session_state.messages[-1]["content"] = transcript
                    else:
                        error_message = event.get("error") or event.get("reason") or "음성을 인식하지 못했어요."
                elif etype == "input_required":
                    error_message = error_message or (event.get("message") or "다시 말씀해주세요.")
                elif etype == "progress":
                    stage = event.get("stage")
                    if stage == "analyze":
                        steps["safety"] = ("✅", "done"); steps["classify"] = ("✅", "done")
                        render_pipeline(steps)
                    elif stage == "route":
                        steps["router"] = ("✅", "done"); steps["rag"] = ("✅", "done")
                        steps["openai"] = ("⏳", "processing"); render_pipeline(steps)
                    elif stage == "generate":
                        steps["openai"] = ("✅", "done"); render_pipeline(steps)
                elif etype == "meta":
                    primary = event.get("primary")
                    labels = event.get("labels") or []
                    confidence = next((l["score"] for l in labels if l["label"] == primary), 0.0)
                elif etype == "crisis":
                    is_crisis = True
                    crisis_message = event.get("message") or "🚨 위기 상황이 감지되었습니다."
                    steps["safety"] = ("🚨", "crisis"); render_pipeline(steps)
                elif etype == "chunks":
                    route = "RAG" if event.get("chunks") else "STS"
                elif etype == "token":
                    assistant_parts.append(event.get("text", ""))
                elif etype == "done":
                    break
    except Exception as e:
        error_message = f"게이트웨이 연결 오류: {e}"

    if error_message and not transcript:
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error_message}", "time": now_str})
        st.rerun()

    if is_crisis:
        st.session_state.messages.append({"role": "assistant", "content": crisis_message, "time": now_str})
        if st.session_state.user_location:
            loc = st.session_state.user_location
            st.session_state.last_crisis_result = get_centers(loc["sido"], loc["sigungu"], is_crisis=True)
        else:
            st.session_state.awaiting_location = True
        st.rerun()

    steps["openai"] = ("✅", "done"); render_pipeline(steps)
    ai_response = "".join(assistant_parts).strip() or "응답을 생성하지 못했어요."
    st.session_state.messages.append({"role": "assistant", "content": ai_response,
                                      "time": datetime.now().strftime("%H:%M"),
                                      "meta": {"distortion": primary, "confidence": confidence}})
    if primary:
        st.session_state.distortion_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user_text": transcript or "(음성 메시지)", "distortion": primary,
            "confidence": confidence, "route": route,
        })
    st.rerun()

elif input_mode == "🖼️ 카톡 캡쳐" and image_value is not None:
    st.session_state.input_widget_seq += 1  # 위젯 key 갱신 → 다음 rerun에서 값 초기화(무한루프 방지)
    now_str = datetime.now().strftime("%H:%M")
    image_bytes = image_value.getvalue()
    mime = "image/jpeg" if image_value.type in ("image/jpeg", "image/jpg") else "image/png"
    sender_names = [kakao_sender.strip()] if st.session_state.get("kakao_sender", "").strip() else []

    # 채팅 버블에 추출 텍스트가 아니라 업로드한 이미지를 그대로 표시 — 분석 대상 원본을 눈으로 확인.
    # (OCR 추출 텍스트는 여전히 게이트웨이로 보내 분류하되, 화면에는 이미지만 보여준다.)
    image_data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
    st.session_state.messages.append({"role": "user", "content": "🖼️ (카톡 캡쳐 업로드)",
                                      "image": image_data_uri, "time": now_str})
    st.session_state.last_crisis_result = None
    steps = {k: ("⬜", "pending") for k in ["safety", "classify", "router", "rag", "openai"]}
    render_pipeline(steps)

    extracted_text = None
    assistant_parts, primary, confidence = [], None, 0.0
    is_crisis, crisis_message, error_message = False, None, None
    route = "STS"
    try:
        with st.spinner("카톡 대화를 읽고 있어요…"):
            for event in respond_stream_image(st.session_state.session_id, image_bytes, mime,
                                              ocr_profile="kakao", sender_names=sender_names):
                etype = event.get("type")
                if etype == "ocr":
                    if event.get("status") == "completed":
                        extracted_text = event.get("user_text")
                        if extracted_text:
                            st.session_state.messages[-1]["content"] = extracted_text
                        else:
                            error_message = "캡쳐에서 내 발화를 찾지 못했어요. 화면을 다시 확인해주세요."
                    else:
                        error_message = event.get("error") or "이미지를 읽지 못했어요."
                elif etype == "input_required":
                    error_message = error_message or (event.get("message") or "이미지를 다시 확인해주세요.")
                elif etype == "progress":
                    stage = event.get("stage")
                    if stage == "analyze":
                        steps["safety"] = ("✅", "done"); steps["classify"] = ("✅", "done")
                        render_pipeline(steps)
                    elif stage == "route":
                        steps["router"] = ("✅", "done"); steps["rag"] = ("✅", "done")
                        steps["openai"] = ("⏳", "processing"); render_pipeline(steps)
                    elif stage == "generate":
                        steps["openai"] = ("✅", "done"); render_pipeline(steps)
                elif etype == "meta":
                    primary = event.get("primary")
                    labels = event.get("labels") or []
                    confidence = next((l["score"] for l in labels if l["label"] == primary), 0.0)
                elif etype == "crisis":
                    is_crisis = True
                    crisis_message = event.get("message") or "🚨 위기 상황이 감지되었습니다."
                    steps["safety"] = ("🚨", "crisis"); render_pipeline(steps)
                elif etype == "chunks":
                    route = "RAG" if event.get("chunks") else "STS"
                elif etype == "token":
                    assistant_parts.append(event.get("text", ""))
                elif etype == "done":
                    break
    except Exception as e:
        error_message = f"게이트웨이 연결 오류: {e}"

    if error_message and not extracted_text:
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error_message}", "time": now_str})
        st.rerun()

    if is_crisis:
        st.session_state.messages.append({"role": "assistant", "content": crisis_message, "time": now_str})
        if st.session_state.user_location:
            loc = st.session_state.user_location
            st.session_state.last_crisis_result = get_centers(loc["sido"], loc["sigungu"], is_crisis=True)
        else:
            st.session_state.awaiting_location = True
        st.rerun()

    steps["openai"] = ("✅", "done"); render_pipeline(steps)
    ai_response = "".join(assistant_parts).strip() or "응답을 생성하지 못했어요."
    st.session_state.messages.append({"role": "assistant", "content": ai_response,
                                      "time": datetime.now().strftime("%H:%M"),
                                      "meta": {"distortion": primary, "confidence": confidence}})
    if primary:
        st.session_state.distortion_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user_text": extracted_text or "(카톡 캡쳐)", "distortion": primary,
            "confidence": confidence, "route": route,
        })
    st.rerun()