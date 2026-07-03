import os

import streamlit as st
from dotenv import load_dotenv

from ui_theme import PALETTE as P
from ui_theme import apply_theme, img_b64, render_sidebar, render_topbar, resolve_page

load_dotenv()

st.set_page_config(
    page_title="마을 광장 · 마음숲",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar(active="home")
render_topbar()


# ── Azure 서비스 연결 상태 확인 (기존 로직 유지 — API 호출 없음) ──
def is_connected(val):
    return bool(val) and val != "여기에_나중에_입력"


def check_content_safety_configured() -> bool:
    return (is_connected(os.getenv("CONTENT_SAFETY_ENDPOINT"))
            and is_connected(os.getenv("CONTENT_SAFETY_KEY")))


def check_search_configured() -> bool:
    return (is_connected(os.getenv("AZURE_SEARCH_ENDPOINT"))
            and is_connected(os.getenv("AZURE_SEARCH_KEY"))
            and is_connected(os.getenv("AZURE_SEARCH_INDEX")))


def check_openai_configured() -> bool:
    return (is_connected(os.getenv("AZURE_OPENAI_ENDPOINT"))
            and is_connected(os.getenv("AZURE_OPENAI_KEY"))
            and is_connected(os.getenv("AZURE_OPENAI_DEPLOYMENT")))


def check_ml_configured() -> bool:
    return (is_connected(os.getenv("AZURE_ML_ENDPOINT"))
            and is_connected(os.getenv("AZURE_ML_KEY")))


services = [
    # (이름, 별명, 이모지, 연결여부, 톤)  — index.tsx services[] 이식
    ("Content Safety",   "안전 게이트",   "🛡️", check_content_safety_configured(), "chip-leaf"),
    ("인지왜곡 분류기",     "생각 감별사",   "🧠", check_ml_configured(),              "chip-coral"),
    ("AI Search (RAG)",  "지식 도서관",   "🔍", check_search_configured(),          "chip-sky"),
    ("Azure OpenAI",     "따뜻한 재구성", "✨", check_openai_configured(),          "chip-sunny"),
]
all_on = all(on for _, _, _, on, _ in services)

# ── 히어로 (index.tsx Hero 섹션) ──────────────────────────────────
hero = img_b64("village-hero.jpg")
hero_bg = (
    f'background-image: linear-gradient(to top, rgba(255,248,231,0.96) 8%, rgba(255,248,231,0.45) 45%, transparent), url("{hero}");'
    if hero else
    "background-image: linear-gradient(135deg, #c0f8e5 0%, #eaf7ce 55%, #fdf1c7 100%);"
)
st.markdown(f"""
<div class="ac-card" style='overflow:hidden; margin-bottom:0; {hero_bg}
     background-size:cover; background-position:center 65%;
     border-bottom-left-radius:0; border-bottom-right-radius:0;'>
  <div style="padding:7.5rem 1.8rem 1.2rem;">
    <span class="ac-chip chip-sunny">🍃 오늘의 마을</span>
    <h1 style="margin:.5rem 0 .2rem; font-size:2rem;">어서와요, 오늘도 마음숲에 오신 걸 환영해요</h1>
    <p style="margin:0; font-size:.92rem; color:{P['muted_fg']};">
      작은 생각도 함께 나누면 큰 나무가 돼요. 편하게 대화를 시작해보세요.</p>
  </div>
</div>
""", unsafe_allow_html=True)
hero_l, hero_r = st.columns([4, 1])
with hero_r:
    st.markdown('<div class="hero-cta">', unsafe_allow_html=True)
    st.page_link(resolve_page("pages/1_채팅.py"), label="💌 대화 시작하기", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

# ── 마을 상점 상태 + 여울이 주민카드 (index.tsx grid 섹션) ────────
col_shop, col_villager = st.columns([2, 1], gap="medium")

with col_shop:
    tiles = ""
    for name, desc, emoji, on, tone in services:
        state_chip = (
            f'<span class="ac-chip chip-leaf">🟢 문 열림</span>' if on
            else f'<span class="ac-chip chip-coral">🔴 닫힘</span>'
        )
        tiles += f"""
        <div style="display:flex; align-items:center; gap:12px; border:1px solid {P['border']};
                    background:rgba(255,248,231,0.6); border-radius:20px; padding:14px 16px;">
            <div class="ac-chip {tone}" style="width:44px;height:44px;justify-content:center;
                 border-radius:16px;font-size:20px;padding:0;">{emoji}</div>
            <div style="flex:1;min-width:0;">
                <div class="font-display" style="font-size:.9rem;">{name}</div>
                <div style="font-size:.75rem;color:{P['muted_fg']};">{desc}</div>
            </div>
            {state_chip}
        </div>"""
    st.markdown(f"""
    <div class="ac-card" style="padding:1.5rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
        <div>
          <h2 style="margin:0;font-size:1.25rem;">마을 상점 상태</h2>
          <p style="margin:0;font-size:.85rem;color:{P['muted_fg']};">오늘 문을 연 서비스들이에요</p>
        </div>
        <span class="ac-chip">🛎️ 실시간</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">{tiles}</div>
    </div>
    """, unsafe_allow_html=True)

with col_villager:
    # 세션 이력 기반 실제 통계 (없으면 0으로 표시)
    hist = st.session_state.get("distortion_history", [])
    n_chat = len(hist)
    n_reframe = len([h for h in hist if h.get("distortion") not in (None, "정상")])
    n_days = len({h["timestamp"][:10] for h in hist}) if hist else 0

    # 오늘의 활동: 이력 상위 3개 왜곡 유형 (없으면 index.tsx 기본값)
    if hist:
        from collections import Counter
        top3 = Counter(h["distortion"] for h in hist).most_common(3)
        activities = [(f"{r}st" if r == 1 else f"{r}nd" if r == 2 else f"{r}rd", name, f"{cnt}회")
                      for r, (name, cnt) in enumerate(top3, start=1)]
    else:
        activities = [("1st", "따뜻한 대화", "0회"), ("2nd", "생각 재구성", "0회"), ("3rd", "감정 일기", "0회")]

    tones = ["chip-sunny", "chip-coral", "chip-lilac"]
    act_rows = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
                border:1px solid {P['border']};background:rgba(255,248,231,0.6);
                border-radius:16px;padding:8px 12px;margin:6px 0;">
              <span style="font-size:.85rem;font-weight:700;">
                <span class="ac-chip {tones[i % 3]}">{rank}</span>&nbsp; {label}</span>
              <span style="font-size:.75rem;color:{P['muted_fg']};">{meta}</span>
            </div>"""
        for i, (rank, label, meta) in enumerate(activities)
    )
    st.markdown(f"""
    <div class="ac-card" style="overflow:hidden;">
      <div style="background:rgba(192,248,229,0.4); padding:1.2rem;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:54px;height:54px;border-radius:18px;background:{P['cream']};
               display:flex;align-items:center;justify-content:center;font-size:26px;
               box-shadow:0 6px 20px -6px rgba(45,143,110,0.25);">🐰</div>
          <div>
            <div class="font-display" style="font-size:1.1rem;">여울이</div>
            <div style="font-size:.72rem;color:{P['muted_fg']};">성격: 다정함 · 별자리: 물병자리</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:14px;text-align:center;">
          <div style="background:{P['card']};border-radius:16px;padding:10px;box-shadow:0 6px 20px -6px rgba(45,143,110,0.2);">
            <div class="font-display" style="font-size:1.1rem;">{n_chat}</div>
            <div style="font-size:.68rem;color:{P['muted_fg']};">대화</div></div>
          <div style="background:{P['card']};border-radius:16px;padding:10px;box-shadow:0 6px 20px -6px rgba(45,143,110,0.2);">
            <div class="font-display" style="font-size:1.1rem;">{n_reframe}</div>
            <div style="font-size:.68rem;color:{P['muted_fg']};">재구성</div></div>
          <div style="background:{P['card']};border-radius:16px;padding:10px;box-shadow:0 6px 20px -6px rgba(45,143,110,0.2);">
            <div class="font-display" style="font-size:1.1rem;">{n_days}일</div>
            <div style="font-size:.68rem;color:{P['muted_fg']};">방문</div></div>
        </div>
      </div>
      <div style="padding:1.1rem 1.2rem;">
        <div class="font-display" style="color:{P['primary']};font-size:.9rem;margin-bottom:8px;">🌟 오늘의 활동</div>
        {act_rows}
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

# ── 메뉴 카드 3개 (index.tsx Menu cards) ─────────────────────────
menus = [
    ("pages/1_채팅.py", "💬", "대화하기", "편지 쓰듯 마음을 적어보세요. 마을 친구가 함께 읽고 재구성해요.", "#c0f8e5", "chip-leaf"),
    ("pages/2_분석대시보드.py", "📊", "마음 일기", "지난 대화들을 모아 인지왜곡 분포와 변화 흐름을 볼 수 있어요.", "#D9B8E8", "chip-lilac"),
    ("pages/3_생각도감.py", "📖", "생각도감", "10가지 인지왜곡 유형을 도감처럼 하나씩 알아가요.", "#E39A86", "chip-coral"),
]
cols = st.columns(3, gap="medium")
for col, (page, emoji, title, desc, accent, tone) in zip(cols, menus):
    with col:
        st.markdown(f"""
        <div class="ac-card menu-card-top" style="overflow:hidden;">
          <div style="height:8px;background:{accent};"></div>
          <div style="padding:1.4rem 1.4rem .6rem;">
            <div class="ac-chip {tone}" style="width:46px;height:46px;justify-content:center;
                 border-radius:16px;font-size:22px;padding:0;margin-bottom:12px;">{emoji}</div>
            <h3 style="margin:0 0 4px;font-size:1.05rem;">{emoji} {title}</h3>
            <p style="margin:0;font-size:.85rem;color:{P['muted_fg']};">{desc}</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="menu-card-cta">', unsafe_allow_html=True)
        st.page_link(resolve_page(page), label="시작하기 →", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── 하단 안내 (기존 app.py 안내 유지) ────────────────────────────
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
if not all_on:
    st.info("💡 **시작하기**: 왼쪽 레일에서 **💬 대화하기**를 선택하세요. 위에 '닫힘'으로 표시된 상점은 `.env` 설정 또는 팀원 작업(모델 배포 등)이 필요해요.")
else:
    st.success("✅ 모든 Azure 상점이 문을 열었어요. **💬 대화하기**에서 바로 시작해보세요.")