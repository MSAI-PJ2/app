# ─────────────────────────────────────────────
# app.py  ←  이 파일이 앱의 "첫 화면(홈)"이에요
# streamlit run app.py  명령으로 실행해요
# ─────────────────────────────────────────────

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# ── 페이지 기본 설정 ──────────────────────────
st.set_page_config(
    page_title="CBT 인지왜곡 분석 대시보드",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 스타일 (색상, 폰트 등) ────────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #EEF0F3;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    /* 뉴모피즘 카드: 배경과 같은 톤 + 이중 그림자(밝은쪽/어두운쪽)로 입체감 표현 */
    .menu-card {
        background: #EEF0F3;
        border-radius: 20px;
        padding: 2rem;
        box-shadow:
            8px 8px 16px rgba(163, 177, 198, 0.5),
            -8px -8px 16px rgba(255, 255, 255, 0.8);
        margin-bottom: 1rem;
        transition: box-shadow 0.2s, transform 0.2s;
        border: none;
    }
    .menu-card:hover {
        transform: translateY(-2px);
        box-shadow:
            10px 10px 20px rgba(163, 177, 198, 0.55),
            -10px -10px 20px rgba(255, 255, 255, 0.9);
    }
    .menu-card h3 {
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .menu-card p {
        color: #6B7280;
        font-size: 0.9rem;
    }
    /* 뉴모피즘 아이콘 배지: 눌려있는(inset) 느낌 */
    .neu-icon {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: #EEF0F3;
        box-shadow:
            inset 4px 4px 8px rgba(163, 177, 198, 0.5),
            inset -4px -4px 8px rgba(255, 255, 255, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-bottom: 12px;
    }
    .badge-ready {
        background: #D1FAE5;
        color: #065F46;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-pending {
        background: #FEF3C7;
        color: #92400E;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    /* 상단 연결 상태 - 타이틀 아래 컴팩트하게 배치 */
    .status-row {
        background: #EEF0F3;
        border-radius: 14px;
        padding: 0.7rem 1.25rem;
        box-shadow:
            5px 5px 10px rgba(163, 177, 198, 0.5),
            -5px -5px 10px rgba(255, 255, 255, 0.85);
        display: flex;
        flex-wrap: wrap;
        gap: 1.6rem;
        margin: 0.5rem 0 1.5rem;
        width: fit-content;
    }
    .status-item {
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: 0.85rem;
        color: #6B7280;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .status-dot.on { background: #22C55E; box-shadow: 0 0 0 3px rgba(34,197,94,0.18); }
    .status-dot.off { background: #EF4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.15); }
    /* 메뉴카드 상단 악센트 바 */
    .card-accent {
        height: 4px;
        width: 36px;
        border-radius: 4px;
        margin-bottom: 14px;
    }
    .card-accent.teal { background: #5EC9B0; }
    .card-accent.lavender { background: #A78BFA; }
    /* 인지왜곡 10개 유형 리스트 - 메뉴카드/지표카드와 동일한 뉴모피즘 톤 */
    .type-row {
        background: #EEF0F3;
        border-radius: 12px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
        box-shadow:
            3px 3px 6px rgba(163, 177, 198, 0.45),
            -3px -3px 6px rgba(255, 255, 255, 0.8);
        font-size: 0.9rem;
        color: #374151;
    }
    .type-row b { color: #1E3A5F; }
    /* 메뉴카드 전체를 클릭 가능한 링크로 감쌀 때 기본 링크 스타일 제거 */
    a.card-link, a.card-link:hover, a.card-link:visited {
        text-decoration: none;
        color: inherit;
        display: block;
    }
</style>
""", unsafe_allow_html=True)


# ── Azure 서비스 연결 상태 확인 함수들 ────────
# 실제 API를 호출하지 않고, .env에 필요한 값들이 채워져 있는지만 확인해요.
# → 비용 발생 없음. 단, "설정값이 있다"는 것과 "실제로 정상 작동한다"는 것은
#   다를 수 있어요 — 진짜 작동 여부는 채팅 페이지에서 직접 확인하세요.

def is_connected(val):
    return bool(val) and val != "여기에_나중에_입력"


def check_content_safety_configured() -> bool:
    return (
        is_connected(os.getenv("CONTENT_SAFETY_ENDPOINT"))
        and is_connected(os.getenv("CONTENT_SAFETY_KEY"))
    )


def check_search_configured() -> bool:
    return (
        is_connected(os.getenv("AZURE_SEARCH_ENDPOINT"))
        and is_connected(os.getenv("AZURE_SEARCH_KEY"))
        and is_connected(os.getenv("AZURE_SEARCH_INDEX"))
    )


def check_openai_configured() -> bool:
    return (
        is_connected(os.getenv("AZURE_OPENAI_ENDPOINT"))
        and is_connected(os.getenv("AZURE_OPENAI_KEY"))
        and is_connected(os.getenv("AZURE_OPENAI_DEPLOYMENT"))
    )


def check_ml_configured() -> bool:
    return (
        is_connected(os.getenv("AZURE_ML_ENDPOINT"))
        and is_connected(os.getenv("AZURE_ML_KEY"))
    )


# 실제 상태 확인 (API 호출 없이 즉시 처리됨)
safety_connected = check_content_safety_configured()
ml_connected = check_ml_configured()
search_connected = check_search_configured()
openai_connected = check_openai_configured()


# ── 홈 화면 본문 ──────────────────────────────

st.markdown('<div class="main-title">🧠 CBT 인지왜곡 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Korean Cognitive Behavioral Therapy Chatbot · MSAI_PJ2_Self</div>', unsafe_allow_html=True)

# Azure 연결 상태 - 별도 섹션 없이 타이틀 바로 아래 한 줄로 컴팩트하게
def _dot(connected: bool) -> str:
    return '<span class="status-dot on"></span>' if connected else '<span class="status-dot off"></span>'

st.markdown(f"""
<div class="status-row">
    <div class="status-item">{_dot(safety_connected)} Content Safety</div>
    <div class="status-item">{_dot(ml_connected)} 인지왜곡 분류기</div>
    <div class="status-item">{_dot(search_connected)} AI Search</div>
    <div class="status-item">{_dot(openai_connected)} Azure OpenAI</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── 메뉴 안내 카드 ────────────────────────────
st.subheader("📌 메뉴 안내")
st.caption("왼쪽 사이드바에서 메뉴를 선택하세요")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("""
    <a class="card-link" href="/채팅" target="_self">
    <div class="menu-card">
        <div class="card-accent teal"></div>
        <div class="neu-icon">💬</div>
        <h3>채팅</h3>
        <p>텍스트를 입력하면 인지왜곡을 분류하고,
        Azure OpenAI가 사고 재구성을 도와줘요.</p>
        <p>포함 기능: Content Safety → 분류기 → LLM 라우터 → RAG → OpenAI</p>
    </div>
    </a>
    """, unsafe_allow_html=True)

with col_b:
    st.markdown("""
    <a class="card-link" href="/분석대시보드" target="_self">
    <div class="menu-card">
        <div class="card-accent lavender"></div>
        <div class="neu-icon">📊</div>
        <h3>분석 대시보드</h3>
        <p>대화 이력을 바탕으로 인지왜곡 유형 분포,
        변화 추이, 세션별 기록을 시각화해요.</p>
        <p>포함 기능: 왜곡 유형 차트 · 변화 추이 · 대화 이력 조회</p>
    </div>
    </a>
    """, unsafe_allow_html=True)

st.divider()

# ── 인지왜곡 10개 유형 설명 ───────────────────
st.subheader("📖 인지왜곡 10개 유형 (KoACD 기준)")
st.caption("분류기가 탐지하는 유형들이에요")

with st.expander("유형 목록 보기 (클릭)"):
    types = [
        ("1", "이분법적 사고", "흑백논리. '완벽하지 않으면 실패야'"),
        ("2", "과잉일반화", "한 번의 실패로 '항상 그렇다'고 결론"),
        ("3", "심리적 여과", "부정적인 것만 걸러내 봄"),
        ("4", "긍정 격하", "좋은 일을 '별거 아니다'고 무시"),
        ("5", "성급한 결론", "근거 없이 최악을 가정"),
        ("6", "과장/축소", "단점은 크게, 장점은 작게 봄"),
        ("7", "감정적 추론", "'이렇게 느끼니까 사실이야'"),
        ("8", "당위적 진술", "'~해야만 해'로 스스로를 압박"),
        ("9", "잘못된 명명", "'나는 실패자야' 식의 극단적 낙인"),
        ("10", "개인화", "내 잘못이 아닌 것도 내 탓으로 돌림"),
    ]
    rows_html = "".join([
        f'<div class="type-row"><b>{num}. {name}</b> — {desc}</div>'
        for num, name, desc in types
    ])
    st.markdown(rows_html, unsafe_allow_html=True)

# ── 하단 안내 ─────────────────────────────────
st.divider()

if not (safety_connected and search_connected and openai_connected and ml_connected):
    st.info("💡 **시작하기**: 왼쪽 사이드바에서 **💬 채팅** 메뉴를 선택하세요. 위에 '미연결'로 표시된 서비스는 `.env` 설정 또는 팀원 작업(모델 배포 등)이 필요해요.")
else:
    st.success("✅ 모든 Azure 서비스 설정이 완료되어 있어요. **💬 채팅** 메뉴에서 바로 시작해보세요.")