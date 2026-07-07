import os

import streamlit as st
from dotenv import load_dotenv

from ui_theme import PALETTE as P
from ui_theme import apply_theme, img_b64, render_sidebar, render_topbar, resolve_page

load_dotenv()

st.set_page_config(
    page_title="마을 광장 · 마음갈피",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar(active="home")
render_topbar(show_new_chat=False)


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

# ── 히어로 + 말랑이 프로필 (좌우 배치) ────────────────────────────
hero = img_b64("bookmark-hero.svg")
hero_bg = (
    f'background-image: linear-gradient(to top, rgba(255,248,231,0.96) 8%, rgba(255,248,231,0.45) 45%, transparent), url("{hero}");'
    if hero else
    "background-image: linear-gradient(135deg, #c0f8e5 0%, #eaf7ce 55%, #fdf1c7 100%);"
)

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
          <span style="font-size:.82rem;font-weight:700;">
            <span class="ac-chip {tones[i % 3]}">{rank}</span>&nbsp; {label}</span>
          <span style="font-size:.72rem;color:{P['muted_fg']};">{meta}</span>
        </div>"""
    for i, (rank, label, meta) in enumerate(activities)
)

with st.container(key="home_hero_row"):
    col_hero, col_villager = st.columns([2, 1], gap="medium")

    with col_hero:
        st.markdown(f"""
        <div class="ac-card" style='position:relative; overflow:hidden; height:100%; {hero_bg}
             background-size:cover; background-position:center center;'>
          <div style="padding:6.5rem 1.8rem 1.2rem;">
            <span class="ac-chip chip-sunny">🍃 오늘의 서재</span>
            <h1 style="margin:.5rem 0 .2rem; font-size:1.8rem;">어서와요, 오늘도 마음갈피와 함께해요</h1>
            <p style="margin:0; font-size:.9rem; color:{P['muted_fg']};">
              작은 생각도 소중한 한 페이지가 돼요. 편하게 대화를 시작해보세요.</p>
            <a href="/채팅" target="_self" class="btn-primary"
               style="position:absolute; right:1.8rem; bottom:1.4rem;">💌 대화 시작하기</a>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_villager:
        if st.session_state.get("is_logged_in"):
            villager_name = "말랑이"
        else:
            villager_name = f"""<a href="/로그인" target="_self"
                 style="color:{P['primary']};text-decoration:none;">로그인하세요 →</a>"""
        st.markdown(f"""
        <div class="ac-card" style="padding:1.3rem 1.4rem;height:100%;">
          <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:48px;height:48px;border-radius:16px;background:rgba(192,248,229,0.5);
                 display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;
                 box-shadow:0 6px 20px -6px rgba(45,143,110,0.25);">🐰</div>
            <div class="font-display" style="font-size:1.05rem;">{villager_name}</div>
          </div>
          <div style="display:flex;gap:6px;margin-top:12px;">
            <div style="flex:1;background:rgba(255,248,231,0.6);border:1px solid {P['border']};
                 border-radius:14px;padding:8px 4px;text-align:center;
                 display:flex;flex-direction:column;justify-content:center;">
              <div class="font-display" style="font-size:1rem;">{n_chat}</div>
              <div style="font-size:.65rem;color:{P['muted_fg']};">대화</div></div>
            <div style="flex:1;background:rgba(255,248,231,0.6);border:1px solid {P['border']};
                 border-radius:14px;padding:8px 4px;text-align:center;
                 display:flex;flex-direction:column;justify-content:center;">
              <div class="font-display" style="font-size:1rem;">{n_reframe}</div>
              <div style="font-size:.65rem;color:{P['muted_fg']};">재구성</div></div>
            <div style="flex:1;background:rgba(255,248,231,0.6);border:1px solid {P['border']};
                 border-radius:14px;padding:8px 4px;text-align:center;
                 display:flex;flex-direction:column;justify-content:center;">
              <div class="font-display" style="font-size:1rem;">{n_days}일</div>
              <div style="font-size:.65rem;color:{P['muted_fg']};">방문</div></div>
          </div>
          <div style="margin-top:14px;">
            <div class="font-display" style="color:{P['primary']};font-size:.85rem;margin-bottom:6px;">🌟 오늘의 활동</div>
            {act_rows}
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

# ── 메뉴 카드 3개 (index.tsx Menu cards) ─────────────────────────
menus = [
    ("/채팅", "💬", "대화하기", "편지 쓰듯 마음을 적어보세요. 마을 친구가 함께 읽고 재구성해요.", "#c0f8e5", "chip-leaf"),
    ("/분석대시보드", "📊", "마음 일기", "지난 대화들을 모아 인지왜곡 분포와 변화 흐름을 볼 수 있어요.", "#D9B8E8", "chip-lilac"),
    ("/생각도감", "📖", "생각도감", "10가지 인지왜곡 유형을 도감처럼 하나씩 알아가요.", "#E39A86", "chip-coral"),
]
cols_container = st.container(key="home_menu_row")
with cols_container:
    cols = st.columns(3, gap="medium")
    for col, (url, emoji, title, desc, accent, tone) in zip(cols, menus):
        with col:
            st.markdown(f"""
            <div class="ac-card" style="overflow:hidden;height:100%;display:flex;flex-direction:column;">
              <div style="flex:0 0 8px;background:{accent};"></div>
              <div style="padding:1.4rem 1.4rem 1.3rem;display:flex;flex-direction:column;flex:1 1 auto;">
                <div class="ac-chip {tone}" style="width:46px;height:46px;justify-content:center;
                     border-radius:16px;font-size:22px;padding:0;margin-bottom:12px;">{emoji}</div>
                <h3 style="margin:0 0 4px;font-size:1.05rem;">{emoji} {title}</h3>
                <p style="margin:0 0 10px;font-size:.85rem;color:{P['muted_fg']};">{desc}</p>
                <a href="{url}" target="_self"
                   style="display:inline-block;color:{P['primary']};font-weight:800;
                          font-size:.85rem;text-decoration:none;margin-top:auto;">시작하기 →</a>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── 하단 안내 (기존 app.py 안내 유지) ────────────────────────────
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 스폰서 광고 팝업 (수익성 — 심사 항목 '시장 가능성' 대응용 목업) ──
# 실제 광고 서버 연동 없이, 파트너십/스폰서 안내를 팝업(모달)으로 보여주는 정적 목업이다.
# "광고" 라벨을 붙여 사용자에게 광고 콘텐츠임을 명확히 표시한다 (투명성).
ads = [
    ("🏛️", "대한상공회의소", "청소년 마음건강 지원 사업과 함께합니다", "#FDE9C8"),
    ("🪟", "Microsoft for Startups", "Azure로 만든 AI 상담 보조 서비스, 마음갈피", "#D6E8FA"),
]


@st.dialog("스폰서 안내")
def show_sponsor_dialog():
    st.markdown(
        f'<span class="ac-chip" style="font-size:.68rem;">광고</span>',
        unsafe_allow_html=True,
    )
    for emoji, name, desc, tone in ads:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;border:1px solid {P["border"]};'
            f'background:{tone};border-radius:16px;padding:14px 16px;margin-top:10px;">'
            f'<div style="font-size:28px;">{emoji}</div>'
            f'<div><div style="font-weight:800;font-size:.95rem;">{name}</div>'
            f'<div style="font-size:.8rem;color:{P["muted_fg"]};">{desc}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    if st.button("닫기", use_container_width=True, key="sponsor_dialog_close"):
        st.rerun()


# 세션당 한 번, 마을 광장(홈) 첫 진입 시 자동으로 팝업을 띄운다.
if "sponsor_ad_shown" not in st.session_state:
    st.session_state.sponsor_ad_shown = True
    show_sponsor_dialog()

# 닫은 뒤에도 다시 볼 수 있도록 하단에 작은 재실행 버튼을 남겨둔다.
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
_, col_ad_btn = st.columns([5, 1])
with col_ad_btn:
    if st.button("🏛️ 스폰서 안내", key="sponsor_dialog_reopen", use_container_width=True):
        show_sponsor_dialog()
