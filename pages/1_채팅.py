import os
from collections import Counter
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

from crisis_gate import check_crisis
from get_centers import get_centers, get_sigungu_list
from kakao_geo import coords_to_address
from streamlit_geolocation import streamlit_geolocation
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar

load_dotenv()

st.set_page_config(page_title="대화하기 · 마음숲", page_icon="💬", layout="wide")
apply_theme()
render_sidebar(active="chat")
render_topbar()

# ── 환경 변수 (변경 없음) ─────────────────────────────────────────
AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY        = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_SEARCH_ENDPOINT   = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY        = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX      = os.getenv("AZURE_SEARCH_INDEX")
AZURE_ML_ENDPOINT       = os.getenv("AZURE_ML_ENDPOINT")
AZURE_ML_KEY            = os.getenv("AZURE_ML_KEY")

DISTORTION_LABELS = {
    0: "이분법적 사고", 1: "과잉일반화", 2: "심리적 여과",
    3: "긍정 격하",    4: "성급한 결론", 5: "과장/축소",
    6: "감정적 추론",  7: "당위적 진술", 8: "잘못된 명명", 9: "개인화",
}

SIDO_OPTIONS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

# ── 세션 상태 (변경 없음 + queued_input 추가) ────────────────────
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


def is_connected(val):
    return val and val != "여기에_나중에_입력"


# ── 파이프라인 함수들 (변경 없음) ─────────────────────────────────
def classify_distortion(text):
    if not is_connected(AZURE_ML_ENDPOINT):
        return {"label": 0, "label_name": "이분법적 사고 (테스트)", "confidence": 0.85, "connected": False}
    try:
        headers = {"Authorization": f"Bearer {AZURE_ML_KEY}", "Content-Type": "application/json"}
        r = requests.post(AZURE_ML_ENDPOINT, headers=headers, json={"text": text}, timeout=15).json()
        label = r.get("label", 0)
        return {"label": label, "label_name": DISTORTION_LABELS.get(label, "알 수 없음"),
                "confidence": r.get("confidence", 0.0), "connected": True}
    except Exception as e:
        return {"label": -1, "label_name": "분류 오류", "confidence": 0.0, "connected": False, "error": str(e)}


def llm_router(text):
    return "RAG" if len(text) > 50 else "STS"


def search_rag(query, distortion_label):
    if not is_connected(AZURE_SEARCH_ENDPOINT):
        dummy = {
            "이분법적 사고": "연속선 기법: 0~100 척도로 상황을 평가해보세요.",
            "과잉일반화": "증거 검토 기법: '항상', '절대로' 같은 단어를 쓸 때 실제 증거를 검토해보세요.",
        }
        return f"[테스트 모드]\n{dummy.get(distortion_label, '인지재구성 기법: 다른 관점에서 증거를 기반으로 생각을 재평가해보세요.')}"
    try:
        from openai import AzureOpenAI
        ai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        vec = ai_client.embeddings.create(
            model=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small"),
            input=f"{distortion_label} {query}"
        ).data[0].embedding

        url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/search?api-version=2024-05-01-preview"
        headers = {"api-key": AZURE_SEARCH_KEY, "Content-Type": "application/json"}
        body = {
            "search": f"{distortion_label} {query}",
            "queryType": "semantic",
            "semanticConfiguration": "cbt-semantic-config",
            "top": 3,
            "vectorQueries": [{
                "kind": "vector",
                "vector": vec,
                "fields": "content_vector",
                "k": 5
            }]
        }
        r = requests.post(url, headers=headers, json=body, timeout=10).json()
        docs = r.get("value", [])
        return "\n\n".join([d.get("content", "") for d in docs]) if docs else "관련 기법을 찾지 못했어요."
    except Exception as e:
        return f"RAG 오류: {e}"


def generate_openai_response(user_text, distortion_name, rag_context, route):
    if not is_connected(AZURE_OPENAI_ENDPOINT):
        return (
            f"**[테스트 모드 응답]**\n\n"
            f"입력하신 내용에서 **{distortion_name}** 패턴이 감지되었어요.\n\n"
            f"Azure OpenAI가 연결되면 실제 CBT 사고 재구성 안내가 여기에 표시됩니다."
        )
    try:
        url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version=2025-01-01-preview"
        headers = {"api-key": AZURE_OPENAI_KEY, "Content-Type": "application/json"}
        system_prompt = """당신은 인지행동치료(CBT) 전문 상담 AI입니다.
사용자의 말에서 인지왜곡을 발견했을 때, 다음 3단계로 응답하세요:
1. 발견된 인지왜곡 유형을 따뜻하게 설명하기
2. CBT 기법을 활용한 사고 재구성 안내
3. 새로운 관점으로 재발화 유도
항상 공감적이고 비판단적인 태도를 유지하세요. 한국어로 응답하세요."""
        user_prompt = f"""사용자 발화: "{user_text}"
감지된 인지왜곡: {distortion_name}
관련 CBT 기법 참고자료: {rag_context}
라우팅 방식: {route}
위 정보를 바탕으로 CBT 상담 응답을 생성해주세요."""
        body = {
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.7, "max_tokens": 600
        }
        r = requests.post(url, headers=headers, json=body, timeout=30).json()
        return r["choices"][0]["message"]["content"]
    except Exception as e:
        return f"OpenAI 오류: {e}"


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
    # 헤더 (chat.tsx header)
    st.markdown(f"""
<div class="chat-header">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:44px;height:44px;border-radius:16px;background:{P['cream']};
         display:flex;align-items:center;justify-content:center;font-size:20px;
         box-shadow:0 6px 20px -6px rgba(45,143,110,0.25);">🍃</div>
    <div>
      <div class="font-display" style="font-size:.95rem;">여울이 · 마음숲 친구</div>
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
    bubbles = ""
    if not st.session_state.messages:
        bubbles = f"""
<div class="msg-row">
  <div class="msg-avatar bot">🍃</div>
  <div class="msg-col">
    <div class="bubble bot">안녕하세요! 오늘은 어떤 마음이 마을에 놀러왔나요? 편지 쓰듯 편하게 적어주세요 🍃</div>
  </div>
</div>"""
    for msg in st.session_state.messages:
        time_str = msg.get("time", "")
        if msg["role"] == "user":
            bubbles += f"""
<div class="msg-row me">
  <div class="msg-col me">
    <div class="bubble me">{msg["content"]}</div>
    <div class="msg-time">{time_str}</div>
  </div>
  <div class="msg-avatar me">🐰</div>
</div>"""
        else:
            meta = msg.get("meta") or {}
            meta_html = ""
            if meta.get("distortion"):
                sev = f'<span class="ac-chip chip-sunny">신뢰도 {meta["confidence"]:.0%}</span>' if meta.get("confidence") else ""
                meta_html = f'<div class="msg-meta"><span class="ac-chip chip-coral">🧠 {meta["distortion"]}</span>{sev}</div>'
            bubbles += f"""
<div class="msg-row">
  <div class="msg-avatar bot">🍃</div>
  <div class="msg-col">
    <div class="bubble bot">{msg["content"]}</div>
    {meta_html}
    <div class="msg-time">{time_str}</div>
  </div>
</div>"""
    st.markdown(f'<div class="chat-body">{bubbles}</div>', unsafe_allow_html=True)

    # 빠른 답장 칩 (chat.tsx composer 하단 칩) — 누르면 바로 전송
    st.markdown('<div class="chat-footer">', unsafe_allow_html=True)
    quick = ["🌱 오늘 있었던 일", "🌧️ 속상한 마음", "🌟 다시 생각해보기", "🌸 감사한 순간"]
    qcols = st.columns(len(quick))
    for qc, q in zip(qcols, quick):
        with qc:
            if st.button(q, key=f"quick_{q}", use_container_width=True):
                st.session_state.queued_input = q[2:].strip() + "에 대해 이야기하고 싶어요"
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 위기 감지 후 위치 입력 대기 (변경 없음 — GPS + selectbox 폴백) ──
    if st.session_state.awaiting_location:
        st.markdown('<div class="crisis-card">', unsafe_allow_html=True)
        st.markdown("📍 **가까운 기관을 안내해드릴게요.**")

        # 위치 동의는 설문(4_설문.py)의 동의란에서 미리 받아둔 값을 사용 — 여기서 다시 묻지 않음
        _profile = st.session_state.get("user_profile") or {}
        location_consent = bool(_profile.get("privacy", {}).get("allow_location_use"))

        sido_gps, sigungu_gps = None, None
        if location_consent:
            st.caption("설문에서 위치 정보 사용에 동의하셨어요 — 자동으로 가까운 지역을 찾아드릴게요.")
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
            st.caption("위치 정보 사용에 동의하지 않으셨어요. 아래에서 지역을 직접 선택해주세요. (설문에서 동의하시면 다음부터는 자동으로 찾아드려요)")

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
        st.markdown('</div>', unsafe_allow_html=True)

    # 직전 위기 결과 표시 (변경 없음)
    if st.session_state.get("last_crisis_result"):
        render_crisis_result(st.session_state.last_crisis_result)

    # composer — st.chat_input (CSS로 Lovable composer 톤 적용됨)
    user_input = st.chat_input("여울이에게 편지를 써보세요…")

    # 대화 초기화 (변경 없음)
    if st.session_state.messages:
        if st.button("🗑️ 대화 초기화", type="secondary"):
            st.session_state.messages = []
            st.session_state.awaiting_location = False
            st.session_state.last_crisis_result = None
            st.session_state.user_location = None
            st.session_state.pop("crisis_sido", None)
            st.session_state.pop("crisis_sigungu", None)
            st.rerun()

# ═══════════ 사이드 패널 (chat.tsx aside) ═══════════
with col_side:
    # 처리 단계 패널 (항상 노출 — 심사/시연 시 내부 동작을 투명하게 보여주는 쪽으로 팀 확정)
    st.markdown(f"""<div class="ac-card" style="padding:1.2rem 1.3rem 0.4rem;margin-bottom:1rem;">
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
    st.divider()

    # 최근 감지된 왜곡 — 이력 기반 프로그레스바 (chat.tsx 사이드 카드)
    hist = st.session_state.distortion_history
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
<div class="ac-card" style="padding:1.3rem;margin-bottom:1rem;">
  <div class="font-display" style="margin-bottom:10px;">🧠 최근 감지된 왜곡</div>
  {bars}
  {'<div style="font-size:.72rem;color:' + P['muted_fg'] + ';">아직 대화 이력이 없어요</div>' if not hist else ''}
</div>""", unsafe_allow_html=True)

    # 🚨 위기 시 도움받기 (chat.tsx 사이드 카드 — 번호는 백엔드 EMERGENCY와 동일 체계)
    hotlines = [("자살예방 상담전화", "109"), ("정신건강 위기상담", "1577-0199"),
                ("응급·소방", "119"), ("경찰", "112")]
    lines = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
             padding:10px 16px;border-top:1px solid {P['border']};font-size:.85rem;">
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
    steps = {k: ("⏳", "processing") for k in ["safety", "classify", "router", "rag", "openai"]}

    # ① Safety — crisis_gate.check_crisis() (변경 없음)
    render_pipeline(steps)
    crisis = check_crisis(user_input)
    if crisis["is_crisis"]:
        steps["safety"] = ("🚨", "crisis")
        render_pipeline(steps)
        crisis_msg = "🚨 **위기 상황이 감지되었습니다**\n\n지금 많이 힘드신 것 같아요. 아래에서 가까운 기관을 확인해보세요."
        st.session_state.messages.append({"role": "assistant", "content": crisis_msg, "time": now_str})

        if st.session_state.user_location:
            loc = st.session_state.user_location
            st.session_state.last_crisis_result = get_centers(loc["sido"], loc["sigungu"], is_crisis=True)
        else:
            st.session_state.awaiting_location = True
        st.rerun()
    steps["safety"] = ("✅", "done")

    # ② 분류기 (변경 없음)
    steps["classify"] = ("⏳", "processing")
    render_pipeline(steps)
    clf = classify_distortion(user_input)
    distortion_name = clf["label_name"]
    confidence = clf["confidence"]
    steps["classify"] = ("✅", "done")
    distortion_placeholder.markdown(
        f'<span class="distortion-badge">{distortion_name}</span><br><small>신뢰도: {confidence:.0%}</small>',
        unsafe_allow_html=True)

    # ③ 라우터 (변경 없음)
    steps["router"] = ("⏳", "processing"); render_pipeline(steps)
    route = llm_router(user_input)
    steps["router"] = ("✅", "done")

    # ④ RAG (변경 없음)
    steps["rag"] = ("⏳", "processing"); render_pipeline(steps)
    rag_context = search_rag(user_input, distortion_name) if route == "RAG" else "짧은 컨텍스트 → STS 직접 응답"
    steps["rag"] = ("✅", "done")

    # ⑤ OpenAI (변경 없음)
    steps["openai"] = ("⏳", "processing"); render_pipeline(steps)
    with st.spinner("여울이가 편지를 쓰는 중…"):
        ai_response = generate_openai_response(user_input, distortion_name, rag_context, route)
    steps["openai"] = ("✅", "done"); render_pipeline(steps)

    # 응답 저장 — Lovable 말풍선 메타칩용으로 meta 추가 (처리단계 패널과 함께 항상 노출)
    meta = {"distortion": distortion_name, "confidence": confidence}
    st.session_state.messages.append({"role": "assistant", "content": ai_response,
                                      "time": datetime.now().strftime("%H:%M"), "meta": meta})
    st.session_state.distortion_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_text": user_input,
        "distortion": distortion_name,
        "confidence": confidence,
        "route": route,
    })
    st.rerun()
