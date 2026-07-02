# ─────────────────────────────────────────────────────────────────
# pages/1_채팅.py
# 파이프라인: Content Safety(crisis_gate) → 분류기 → LLM 라우터 → RAG/STS → OpenAI
# 위기 감지 시: GPS 자동 위치 감지(카카오) → 실패/거부 시 selectbox 폴백 → get_centers()
# ─────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from crisis_gate import check_crisis
from get_centers import get_centers, get_sigungu_list
from kakao_geo import coords_to_address
from streamlit_geolocation import streamlit_geolocation

load_dotenv()

st.set_page_config(page_title="CBT 채팅", page_icon="💬", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #EEF0F3; }
    .user-bubble {
        background: #4A90D9; color: white; padding: 0.8rem 1.2rem;
        border-radius: 18px 18px 4px 18px; margin: 0.5rem 0; max-width: 70%;
        margin-left: auto; font-size: 0.95rem;
        box-shadow: 4px 4px 10px rgba(163, 177, 198, 0.4);
    }
    .bot-bubble {
        background: #EEF0F3; color: #1E3A5F; padding: 0.8rem 1.2rem;
        border-radius: 18px 18px 18px 4px; margin: 0.5rem 0; max-width: 70%;
        font-size: 0.95rem;
        box-shadow:
            6px 6px 13px rgba(163, 177, 198, 0.65),
            -6px -6px 13px rgba(255, 255, 255, 0.95);
    }
    .distortion-badge {
        background: #EDE9FE; color: #4C1D95; padding: 4px 12px;
        border-radius: 20px; font-size: 0.85rem; font-weight: 600;
        display: inline-block; margin: 4px 2px;
    }
    /* 처리 단계 패널 - 개발자 모드 전용이라 뉴모피즘으로 부드럽게 */
    .pipeline-step {
        background: #EEF0F3; padding: 0.5rem 0.9rem;
        margin: 0.4rem 0; font-size: 0.85rem; color: #374151; border-radius: 10px;
        box-shadow:
            3px 3px 6px rgba(163, 177, 198, 0.45),
            -3px -3px 6px rgba(255, 255, 255, 0.8);
    }
    .pipeline-step.done { color: #065F46; }
    .pipeline-step.error { color: #991B1B; }
    .pipeline-step.crisis { color: #92400E; }
    /* ⚠️ 아래 위기 관련 요소는 접근성을 위해 고대비 유지 - 뉴모피즘 적용 안 함 */
    .crisis-card {
        background: #FFFBEB; border: 2px solid #F59E0B; border-radius: 12px;
        padding: 1.2rem; margin: 0.8rem 0;
    }
    .center-card {
        background: white; border-radius: 10px; padding: 0.9rem 1.1rem;
        margin: 0.5rem 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border: 1px solid #E5E7EB;
    }
    .emergency-box {
        background: #FEF2F2; border-left: 4px solid #EF4444; padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0; margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "distortion_history" not in st.session_state:
    st.session_state.distortion_history = []
if "awaiting_location" not in st.session_state:
    st.session_state.awaiting_location = False
if "user_location" not in st.session_state:
    st.session_state.user_location = None  # {"sido":..., "sigungu":...} 한 번 받으면 세션 내 재사용


class _NullPlaceholder:
    """개발자 모드가 꺼져있을 때 pipeline/distortion 패널 호출을 조용히 무시하기 위한 더미 객체"""
    def markdown(self, *args, **kwargs):
        pass
    def caption(self, *args, **kwargs):
        pass


def is_connected(val):
    return val and val != "여기에_나중에_입력"


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
    """get_centers() 결과를 화면에 표시"""
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


# ── 화면 렌더링 ───────────────────────────────
st.title("💬 CBT 채팅")
st.caption("인지왜곡이 감지되면 Azure OpenAI가 사고 재구성을 도와드려요")

# 개발자/심사용 파이프라인 시각화 — 기본은 최종 사용자에게 숨김.
# 이유: "처리 단계"나 "감지된 왜곡 유형" 뱃지를 사용자가 직접 보면
# 스스로에게 진단 라벨을 붙이는 셈이 되어 프로젝트의 "진단 기능 의도적 제외" 원칙과 충돌함.
# 시연/디버깅이 필요할 때만 사이드바에서 켜서 확인하는 용도로 남겨둠.
with st.sidebar:
    st.divider()
    DEBUG_MODE = st.toggle("🔧 개발자 모드 (파이프라인 보기)", value=False)

if DEBUG_MODE:
    col_chat, col_pipeline = st.columns([2, 1])
else:
    col_chat = st.container()
    col_pipeline = None

with col_chat:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble">🙋 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-bubble">🧠 {msg["content"]}</div>', unsafe_allow_html=True)

    # 위기 감지 후 위치 입력 대기 중이면 GPS 버튼 + selectbox 폴백 표시
    if st.session_state.awaiting_location:
        st.markdown('<div class="crisis-card">', unsafe_allow_html=True)
        st.markdown("📍 **가까운 기관을 안내해드릴게요.**")
        st.caption("아래 버튼을 눌러 위치 권한을 허용하면 자동으로 지역을 찾아드려요.")

        location = streamlit_geolocation()

        sido_gps, sigungu_gps = None, None
        if location and location.get("latitude"):
            lat, lon = location["latitude"], location["longitude"]
            region = coords_to_address(lat, lon)
            if region:
                sido_gps = region["시도"]
                sigungu_gps = region["시군구"]
                st.success(f"📍 위치 자동 감지: {sido_gps} {sigungu_gps}")
            else:
                st.warning("좌표를 행정구역으로 변환하지 못했어요. 아래에서 직접 선택해주세요.")

        # GPS 감지 성공 시: selectbox 없이 바로 이 위치로 조회 (session_state에 남은
        # 예전 selectbox 값과 충돌하지 않도록, 자동감지 결과는 별도 버튼으로 분리)
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

    # 직전에 검색된 위기 결과가 있으면 표시
    if st.session_state.get("last_crisis_result"):
        render_crisis_result(st.session_state.last_crisis_result)

    user_input = st.chat_input("오늘 어떤 생각이 드셨나요? 자유롭게 적어보세요...")

if DEBUG_MODE:
    with col_pipeline:
        st.subheader("🔄 처리 단계")
        pipeline_placeholder = st.empty()
        pipeline_placeholder.markdown("""
<div class="pipeline-step">① 안전 게이트 (대기)</div>
<div class="pipeline-step">② 인지왜곡 분류기 (대기)</div>
<div class="pipeline-step">③ LLM 라우터 (대기)</div>
<div class="pipeline-step">④ RAG / STS (대기)</div>
<div class="pipeline-step">⑤ Azure OpenAI (대기)</div>
""", unsafe_allow_html=True)
        st.divider()
        st.subheader("🏷️ 감지된 왜곡 유형")
        distortion_placeholder = st.empty()
        distortion_placeholder.caption("입력 후 결과가 표시됩니다")
else:
    # 최종 사용자 화면: 패널 자체를 만들지 않고, 아래 로직에서 호출해도
    # 아무 일도 일어나지 않는 더미 객체로 대체
    pipeline_placeholder = _NullPlaceholder()
    distortion_placeholder = _NullPlaceholder()


def render_pipeline(steps):
    labels = {"safety": "① 안전 게이트", "classify": "② 인지왜곡 분류기",
              "router": "③ LLM 라우터", "rag": "④ RAG / STS", "openai": "⑤ Azure OpenAI"}
    icons  = {"done": "✅", "processing": "⏳", "pending": "⬜", "error": "❌", "crisis": "🚨"}
    html = ""
    for key, (icon_key, status) in steps.items():
        css = "pipeline-step" + (" done" if status=="done" else " error" if status=="error" else " crisis" if status=="crisis" else "")
        html += f'<div class="{css}">{icons.get(icon_key,"⬜")} {labels[key]}</div>'
    pipeline_placeholder.markdown(html, unsafe_allow_html=True)


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.last_crisis_result = None  # 새 메시지 들어오면 이전 위기카드 비움
    steps = {k: ("⏳","processing") for k in ["safety","classify","router","rag","openai"]}

    # ① Safety — crisis_gate.check_crisis() 사용
    render_pipeline(steps)
    crisis = check_crisis(user_input)
    if crisis["is_crisis"]:
        steps["safety"] = ("🚨","crisis")
        render_pipeline(steps)
        crisis_msg = "🚨 **위기 상황이 감지되었습니다**\n\n지금 많이 힘드신 것 같아요. 아래에서 가까운 기관을 확인해보세요."
        st.session_state.messages.append({"role": "assistant", "content": crisis_msg})

        if st.session_state.user_location:
            # 이미 위치를 받은 적 있으면 selectbox/GPS 생략하고 바로 조회
            loc = st.session_state.user_location
            st.session_state.last_crisis_result = get_centers(loc["sido"], loc["sigungu"], is_crisis=True)
        else:
            st.session_state.awaiting_location = True
        st.rerun()
    steps["safety"] = ("✅","done")

    # ② 분류기
    steps["classify"] = ("⏳","processing")
    render_pipeline(steps)
    clf = classify_distortion(user_input)
    distortion_name = clf["label_name"]
    confidence = clf["confidence"]
    steps["classify"] = ("✅","done")
    distortion_placeholder.markdown(f'<span class="distortion-badge">{distortion_name}</span><br><small>신뢰도: {confidence:.0%}</small>', unsafe_allow_html=True)

    # ③ 라우터
    steps["router"] = ("⏳","processing"); render_pipeline(steps)
    route = llm_router(user_input)
    steps["router"] = ("✅","done")

    # ④ RAG
    steps["rag"] = ("⏳","processing"); render_pipeline(steps)
    rag_context = search_rag(user_input, distortion_name) if route=="RAG" else "짧은 컨텍스트 → STS 직접 응답"
    steps["rag"] = ("✅","done")

    # ⑤ OpenAI
    steps["openai"] = ("⏳","processing"); render_pipeline(steps)
    with st.spinner("응답 생성 중..."):
        ai_response = generate_openai_response(user_input, distortion_name, rag_context, route)
    steps["openai"] = ("✅","done"); render_pipeline(steps)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.session_state.distortion_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_text": user_input,
        "distortion": distortion_name,
        "confidence": confidence,
        "route": route,
    })
    st.rerun()

if st.session_state.messages:
    if st.button("🗑️ 대화 초기화", type="secondary"):
        st.session_state.messages = []
        st.session_state.awaiting_location = False
        st.session_state.last_crisis_result = None
        st.session_state.user_location = None
        # selectbox에 남은 이전 선택값도 같이 초기화 (다음 위기 감지 시 깨끗한 상태로 시작)
        st.session_state.pop("crisis_sido", None)
        st.session_state.pop("crisis_sigungu", None)
        st.rerun()
