import base64
import os
import unicodedata
from datetime import datetime
from functools import lru_cache

import streamlit as st

# ── 디자인 토큰 (src/styles.css :root 를 hex로 근사 변환) ──────────
PALETTE = {
    "cream":      "#FFF8E7",   # --cream / --background
    "card":       "#FFFEF9",   # --card
    "fg":         "#4A4032",   # --foreground  oklch(0.32 0.05 60)
    "fg_deep":    "#1E4638",
    "muted":      "#EFE7D2",   # --muted
    "muted_fg":   "#877B67",   # --muted-foreground
    "border":     "#E6DBBF",   # --border
    "primary":    "#288a6b",   # --primary
    "primary_fg": "#FBF7EA",
    "leaf":       "#c0f8e5",
    "leaf_deep":  "#2d8f6e",
    "sand":       "#F2EAD3",
    "sky":        "#C4DCEA",
    "coral":      "#E39A86",
    "peach":      "#F2CBA8",
    "sunny":      "#F3DD8F",
    "lilac":      "#D9B8E8",
    "wood":       "#A28A6B",
    "sidebar":         "#B4B87C",
    "sidebar_fg":      "#3A3D22",
    "sidebar_primary": "#E8DFA0",
    "sidebar_accent":  "#9CA366",
    # recharts palette (analytics.tsx)
    "chart": ["#E39A86", "#D9B8E8", "#8FB4D6", "#F3DD8F", "#5bcea8", "#CBA06B", "#E0A0BE",
              "#2d8f6e", "#F2CBA8", "#B8C9A3"],
}

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_APP_ROOT = os.path.dirname(os.path.abspath(__file__))


def resolve_page(rel_path: str) -> str:
    """st.page_link()에 넘길 상대경로를, 실제 디스크의 파일명 바이트로 치환.

    ⚠️ macOS(APFS)는 한글 파일명을 분해형(NFD)으로 저장하는데, 소스코드에
    적힌 문자열은 완성형(NFC)이라 화면엔 같아 보여도 바이트가 달라요.
    st.page_link 내부는 두 문자열을 정확히(==) 비교하기 때문에 이 차이만으로
    "StreamlitPageNotFoundError"가 납니다. (파일을 여는 것 자체는 OS가 알아서
    정규화해주기 때문에 문제가 없어서, 다른 기능은 멀쩡히 동작하는 게 특징.)
    → 실제 os.listdir() 결과에서 정규화 기준으로 같은 파일을 찾아, 그 디렉토리가
      보고하는 바이트 그대로 반환. Linux/Windows(NFC)에서도 그대로 안전하게 동작.
    """
    dirname, filename = os.path.split(rel_path)
    search_dir = os.path.join(_APP_ROOT, dirname) if dirname else _APP_ROOT
    try:
        entries = os.listdir(search_dir)
    except OSError:
        return rel_path
    target = unicodedata.normalize("NFC", filename)
    for entry in entries:
        if unicodedata.normalize("NFC", entry) == target:
            return os.path.join(dirname, entry) if dirname else entry
    return rel_path


@lru_cache(maxsize=8)
def img_b64(filename: str) -> str:
    """assets/ 이미지 → base64 데이터 URI (없으면 빈 문자열)"""
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        return ""
    if filename.endswith("svg"):
        mime = "svg+xml"
    elif filename.endswith("png"):
        mime = "png"
    else:
        mime = "jpeg"
    with open(path, "rb") as f:
        return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"


# ── 전역 CSS (styles.css + app-layout.tsx 이식) ────────────────────
def restore_session():
    """새로고침 등으로 session_state가 리셋돼도 URL의 ?uid= 로 로그인 상태를 복원한다.
    브라우저 탭을 완전히 새로 열면(주소창에 uid 없이 접속) 복원 안 됨 — 그땐 재로그인이 맞는 동작."""
    if not st.session_state.get("user_id"):
        qp_uid = st.query_params.get("uid")
        if qp_uid:
            st.session_state.user_id = qp_uid
            st.session_state.is_logged_in = True
    _seed_demo_consent()  # 데모 계정은 진입 경로(로그인/URL) 무관하게 동의 시드


def _seed_demo_consent():
    """[로컬 워크어라운드 — 커밋 금지] 데모 계정(demo@maeumgalpi.kr)에 한해 사전 질문
    게이트(require_consent)를 통과하도록 필수 동의를 자동 시드한다. 시연에서 데모 계정이
    설문에 막히지 않게 하는 용도 — 로그인 흐름·URL(?uid=) 진입 모두 커버한다.
    데모 uid 가 정확히 일치할 때만 작동하므로 실제 사용자는 진짜 동의 게이트를 그대로 거친다.
    (로그인 시 0_로그인.py 가 user_profile 을 게이트웨이 프로필로 덮으므로, apply_theme 가
    매 rerun 최상단에서 이 함수를 호출해 그 다음 실행에서 동의를 다시 채워 넣는다.)"""
    try:
        from demo_data import DEMO_LOGIN_UID
    except Exception:
        return
    if st.session_state.get("user_id") != DEMO_LOGIN_UID:
        return
    prof = st.session_state.get("user_profile") or {}
    privacy = prof.get("privacy") or {}
    if not (privacy.get("agreed_terms") and privacy.get("agreed_sensitive_profile")):
        prof["privacy"] = {**privacy, "agreed_terms": True, "agreed_sensitive_profile": True}
        st.session_state.user_profile = prof

def apply_theme():
    restore_session()
    p = PALETTE
    st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
    /* ── 폰트 & 배경 (ac-leaf-bg 잎사귀 패턴 포함) ───────────── */
    html, body, [class*="css"], .stApp, p, div, span, label {{
        font-family: 'Nunito', ui-sans-serif, system-ui, sans-serif;
        color: {p['fg']};
    }}
    h1, h2, h3, h4, .font-display {{
        font-family: 'Fredoka', ui-rounded, system-ui, sans-serif !important;
        letter-spacing: -0.01em;
        color: {p['fg']};
    }}
    .stApp {{
        background-color: {p['cream']};
        background-image:
            radial-gradient(circle at 10% 20%, rgba(192,248,229,0.35) 0 8px, transparent 9px),
            radial-gradient(circle at 80% 60%, rgba(159,232,208,0.40) 0 10px, transparent 11px),
            radial-gradient(circle at 40% 80%, rgba(91,206,168,0.30) 0 7px, transparent 8px);
        background-size: 320px 320px;
    }}
    .block-container {{ padding-top: 1.8rem; max-width: 1200px; }}

    /* ── st.columns 같은 줄 카드끼리 높이 자동으로 맞추기 ─────────
       Streamlit이 컬럼 안에 넣는 감싸는 div들은 기본적으로 내용물
       높이만큼만 차지해서, 카드에 넣은 height:100%가 먹히지 않는
       문제가 있음. 이전엔 wrapper 하나하나 이름(stVerticalBlock,
       stElementContainer, stMarkdown...)을 짚어가며 고쳤는데, 실제로는
       그 사이에 이름 없는 wrapper div가 하나 더 있어서 계속 끊겼음
       (개발자도구로 실제 DOM 확인 후 발견).
       → 이름을 일일이 쫓는 대신, 컬럼 안의 모든 div에 height:100%를
         강제 적용해서 몇 겹이 있든 관통하도록 함. 부모(stColumn)가
         flex stretch로 이미 "확정된 높이"를 가지므로, 그 아래 모든
         div가 한 겹씩 100%→100%→100%로 이어져 결국 우리 카드까지 닿음.
       ⚠️ 단, .ac-card **안쪽**(아바타 줄, 통계 칸, 활동 리스트 등)까지
         전부 100%로 늘리면 서로 겹쳐서 레이아웃이 깨짐 — :not(.ac-card),
         :not(.ac-card *) 로 .ac-card 경계에서 딱 멈추게 함. Streamlit
         wrapper까지만 늘리고, 카드 내부는 원래 방식(자연스러운 내용물
         크기)대로 그대로 둠.
       ⚠️⚠️ 버그 수정(2026-07-06): 이 규칙이 `div[data-testid="stColumn"]`
         전체(앱 전역)에 걸려 있어서, 홈 화면 말고 다른 페이지의 st.columns()
         에도 전부 적용되고 있었다 — 특히 1_채팅.py의 col_side(처리 단계 /
         감지된 왜곡 유형)처럼 .ac-card가 아닌 요소가 나란히 있는 컬럼에서는
         전부 height:100%로 강제되어 텍스트가 서로 겹쳐 보이는 버그를 냈다.
         → st.container(key="home_hero_row")/st.container(key="home_menu_row")
         로 홈 화면의 두 카드 묶음만 감싸고, 이 CSS를 그 두 컨테이너
         (.st-key-home_hero_row, .st-key-home_menu_row) 안으로만 좁힌다. */
    .st-key-home_hero_row div[data-testid="stHorizontalBlock"],
    .st-key-home_menu_row div[data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
    .st-key-home_hero_row div[data-testid="stColumn"],
    .st-key-home_menu_row div[data-testid="stColumn"] {{ display: flex; flex-direction: column; }}
    .st-key-home_hero_row div[data-testid="stColumn"] div:not(.ac-card):not(.ac-card *),
    .st-key-home_menu_row div[data-testid="stColumn"] div:not(.ac-card):not(.ac-card *) {{ height: 100%; }}

    /* Streamlit 기본 헤더(Deploy 버튼 등)가 커스텀 상단바 위에 겹쳐서
       필(pill)이 잘려 보이는 문제 방지 — 완전 커스텀 UI라 기본 헤더 불필요 */
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stToolbar"] {{ display: none !important; }}

    /* ── 사이드바: 올리브 아이콘 레일 (app-layout.tsx <aside>) ── */
    [data-testid="stSidebarNav"] {{ display: none; }}   /* 기본 페이지 네비 숨김 */

    /* 사이드바 접기/펼치기 버튼을 완전히 제거 → 클릭 자체가 불가능하게.
       테스트id가 버전에 따라 다를 수 있어 이름이 겹치는 패턴까지 폭넓게 잡음. */
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid*="CollapsedControl"],
    [data-testid*="CollapseButton"],
    [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
    }}

    /* ⚠️ 핵심 방어: 버튼을 숨겨도 Streamlit이 내부적으로 사이드바를
       "접힘" 상태(aria-expanded="false")로 표시하면 사이드바 자체가
       화면 밖으로 밀려나거나 width:0 이 되어 사라짐 — 그러면 되돌릴
       버튼도 같이 사라져서 영영 못 꺼내는 상황이 생김.
       그래서 접힘 상태 속성이 붙어도 컨테이너를 강제로 항상 펼친
       크기/위치로 고정한다 (버튼 숨김만으로는 불충분). */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        background: {p['sidebar']} !important;
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
        transform: none !important;
        margin-left: 0 !important;
        visibility: visible !important;
        position: relative !important;
    }}
    /* 접힘 상태일 때 Streamlit이 본문 영역을 전체 폭으로 늘리지 못하게,
       사이드바 폭만큼 항상 여백을 확보 */
    div[data-testid="stAppViewContainer"] > section:last-child {{
        margin-left: 0 !important;
    }}

    /* 사이드바 오른쪽 경계의 "드래그로 폭 조절" 핸들 제거.
       ⚠️ 이 핸들은 data-testid가 아예 없는 요소라 testid 기반 선택자로는
       못 잡음 — Streamlit 번들 JS를 직접 뜯어서 확인한 실제 클래스(eelgd2m3,
       re-resizable 라이브러리의 핸들 컴포넌트)를 정확히 지정한다.
       Streamlit 버전이 바뀌면 이 내부 클래스명이 달라질 수 있어, 구조적
       선택자(사이드바 바로 아래 absolute+col-resize 요소)로 한 번 더 방어. */
    section[data-testid="stSidebar"] .eelgd2m3,
    section[data-testid="stSidebar"] [class*="eelgd2m3"] {{
        display: none !important;
        pointer-events: none !important;
        width: 0 !important;
    }}
    /* 구조적 방어선: 사이드바 바로 아래, 헤더/컨텐츠가 아닌 나머지 요소는
       전부 클릭 통과(pointer-events: none)시켜서 리사이즈 드래그 자체를
       막는다. 텍스트/버튼이 아니라 위치 잡기용 div라 기능엔 영향 없음. */
    section[data-testid="stSidebar"] > div:not([data-testid="stSidebarContent"]) {{
        pointer-events: none !important;
    }}
    section[data-testid="stSidebar"] {{
        resize: none !important;
    }}

    section[data-testid="stSidebar"] > div:first-child {{
        padding: 1.2rem 0.7rem 1rem;
        display: flex; flex-direction: column; align-items: center;
    }}
    .rail-logo {{
        background: {p['sidebar_accent']};
        border-radius: 18px; padding: 8px;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
        margin-bottom: 14px; display: inline-block;
    }}
    .rail-logo img {{ width: 44px; height: 44px; display: block; }}
    a.rail-item, a.rail-item:visited {{
        display: flex; flex-direction: column; align-items: center; gap: 3px;
        width: 100%; padding: 9px 4px; margin: 3px 0;
        border-radius: 18px; text-decoration: none;
        font-size: 11px; font-weight: 800; color: {p['sidebar_fg']};
        transition: background .15s;
    }}
    a.rail-item:hover {{ background: {p['sidebar_accent']}; }}
    a.rail-item.active {{
        background: {p['sunny']};
        color: {p['fg']};
        box-shadow: 0 10px 30px -8px rgba(40,138,107,0.35);
    }}
    .rail-item .rail-icon {{ font-size: 20px; line-height: 1; }}
    .rail-avatar {{
        margin-top: 18px;
        width: 42px; height: 42px; border-radius: 50%;
        border: 2px solid {p['sunny']}; background: {p['cream']};
        display: flex; align-items: center; justify-content: center; font-size: 20px;
    }}
    /* 사이드바 안의 toggle(개발자 모드) 색 톤 */
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {{
        color: {p['sidebar_fg']} !important; font-size: 12px !important; font-weight: 700;
    }}
    /* ── st.page_link → 레일 메뉴 pill (rail-item 대체) ─────── */
    section[data-testid="stSidebar"] [data-testid="stPageLink"] {{
        border-radius: 16px; margin: 3px 0; padding: 2px 0;
        transition: background .15s;
    }}
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:hover {{
        background: {p['sidebar_accent']};
    }}
    section[data-testid="stSidebar"] [data-testid="stPageLink"] p {{
        font-size: 11.5px !important; font-weight: 800 !important;
        color: {p['sidebar_fg']} !important; text-align: center;
    }}
    section[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
        display: flex; flex-direction: column; align-items: center; gap: 2px;
        text-decoration: none;
    }}
    /* ── 상단 바 (app-layout.tsx <header>) ─────────────────── */
    .topbar {{
        display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
        padding: 4px 0 14px; border-bottom: 1px solid {p['border']};
        margin-bottom: 1.4rem;
    }}
    .topbar .pill {{
        display: inline-flex; align-items: center; gap: 7px;
        background: {p['card']}; border: 1px solid {p['border']};
        border-radius: 999px; padding: 7px 14px;
        font-size: 13px; font-weight: 700;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
    }}
    .topbar .pill small {{ color: {p['muted_fg']}; font-weight: 600; }}
    .topbar .spacer {{ flex: 1; }}
    a.btn-primary, a.btn-primary:visited {{
        display: inline-flex; align-items: center; gap: 7px;
        background: {p['primary']}; color: {p['primary_fg']} !important;
        border-radius: 999px; padding: 9px 18px;
        font-size: 13px; font-weight: 800; text-decoration: none;
        box-shadow: 0 10px 30px -8px rgba(40,138,107,0.35);
    }}
    a.btn-primary:hover {{ filter: brightness(1.05); }}

    /* 네이티브 위젯을 감싸는 카드 — st.container(border=True) 공통 스타일
       (로그인/설문 폼처럼 real Streamlit 위젯을 카드 안에 넣어야 하는 곳에서 사용) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 24px !important;
        border-color: {p['border']} !important;
        background: {p['card']} !important;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
    }}

    /* multiselect 선택 태그 — 기본 Streamlit 빨간톤이 자극적이라 테마 톤으로 교체 */
    span[data-baseweb="tag"] {{
        background-color: {p['primary']} !important;
        border-radius: 999px !important;
    }}
    span[data-baseweb="tag"] span {{ color: {p['primary_fg']} !important; }}
    span[data-baseweb="tag"] svg {{ fill: {p['primary_fg']} !important; }}

    /* ── ac-card / ac-chip 유틸 (styles.css @utility) ───────── */
    .ac-card {{
        background: {p['card']};
        border: 1px solid {p['border']};
        border-radius: 28px;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
    }}
    .ac-chip {{
        display: inline-flex; align-items: center; gap: 5px;
        padding: 3px 11px; border-radius: 999px;
        font-size: 12px; font-weight: 800;
        background: {p['sand']}; color: {p['fg']};
    }}

    /* ── 채팅 요소 (routes/chat.tsx) ────────────────────────── */
    /* ⚠️ 구조 변경(2026-07-06): 예전엔 chat-header/chat-body/chat-footer 를
       각각 별개의 st.markdown() 호출로 열고-닫았는데, Streamlit은 st.markdown()
       호출마다 독립된 DOM 컨테이너를 만들기 때문에 열린 <div>가 그 호출 하나의
       컨테이너 안에서만 닫히고, 그 사이에 낀 실제 위젯(st.button, st.chat_input,
       st.radio 등)은 카드 바깥의 형제 요소로 렌더링됨 — 카드가 빈 박스로 보이고
       입력창/버튼이 카드 밖으로 떨어져 나오는 "무너진 UI" 버그의 원인이었음.
       → st.container(key="chat_card") 로 전체를 감싸 실제 DOM 하나로 묶고,
       이 CSS는 그 컨테이너(.st-key-chat_card)에 카드 스타일을 입힌다.
       header 배너만 카드 안쪽에서 한 번의 st.markdown() 호출로 완결되는
       (열고 그 자리에서 바로 닫는) 배너 div로 처리 — 이건 안전함. */
    .st-key-chat_card {{
        background: rgba(255,248,231,0.55);
        border: 1px solid {p['border']};
        border-radius: 28px;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
        overflow: hidden;
        padding: 0 20px 16px !important;
    }}
    .chat-header {{
        display: flex; align-items: center; justify-content: space-between;
        background: rgba(192,248,229,0.35);
        margin: 0 -20px 14px;
        padding: 12px 20px;
        border-radius: 28px 28px 0 0;
    }}
    .chat-footer-divider {{
        border-top: 1px solid {p['border']};
        margin: 10px -20px 10px;
    }}
    .msg-row {{ display: flex; align-items: flex-end; gap: 8px; margin: 14px 0; }}
    .msg-row.me {{ justify-content: flex-end; }}
    .msg-avatar {{
        width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 16px;
    }}
    .msg-avatar.bot {{ background: rgba(192,248,229,0.7); }}
    .msg-avatar.me  {{ background: rgba(243,221,143,0.75); }}
    .msg-col {{ max-width: 75%; display: flex; flex-direction: column; }}
    .msg-col.me {{ align-items: flex-end; }}
    .bubble {{
        padding: 11px 16px; font-size: 14.5px; line-height: 1.55;
        border-radius: 24px;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25);
    }}
    .bubble.bot {{
        background: {p['card']}; border: 1px solid {p['border']};
        border-bottom-left-radius: 8px; color: {p['fg']};
    }}
    .bubble.me {{
        background: {p['primary']}; color: {p['primary_fg']};
        border-bottom-right-radius: 8px;
    }}
    .bubble.me * {{ color: {p['primary_fg']} !important; }}
    .msg-meta {{ margin-top: 5px; display: flex; gap: 5px; flex-wrap: wrap; }}
    .msg-time {{ margin-top: 4px; padding: 0 4px; font-size: 10px; color: {p['muted_fg']}; }}
    .chip-coral {{ background: rgba(227,154,134,0.28) !important; }}
    .chip-sunny {{ background: rgba(243,221,143,0.5) !important; }}
    .chip-leaf  {{ background: rgba(192,248,229,0.45) !important; color: {p['leaf_deep']} !important; }}
    .chip-lilac {{ background: rgba(217,184,232,0.4) !important; }}
    .chip-sky   {{ background: rgba(196,220,234,0.55) !important; }}

    /* 진행 바 (chat.tsx 최근 감지된 왜곡) */
    .bar-track {{ height: 8px; border-radius: 999px; background: {p['muted']}; overflow: hidden; margin: 4px 0 10px; }}
    .bar-fill  {{ height: 100%; border-radius: 999px; }}

    /* st.chat_input 을 Lovable composer 톤으로 */
    [data-testid="stChatInput"] {{ background: transparent; }}
    [data-testid="stChatInput"] > div {{
        border-radius: 999px !important;
        border: 1.5px solid {p['border']} !important;
        background: #FFFDF4 !important;
        box-shadow: 0 6px 20px -6px rgba(45,143,110,0.25) !important;
    }}
    [data-testid="stChatInput"] textarea {{ font-family: 'Nunito', sans-serif !important; }}

    /* 빠른 답장 칩 버튼 (st.button 기본형 → ac-chip 톤) */
    div[data-testid="stHorizontalBlock"] .stButton > button {{
        border-radius: 999px; border: 1px solid {p['border']};
        background: {p['sand']}; color: {p['fg']};
        font-size: 12.5px; font-weight: 800; padding: 4px 14px;
        box-shadow: none;
    }}
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {{
        background: rgba(243,221,143,0.5); border-color: {p['sunny']}; color: {p['fg']};
    }}

    /* 기본 Streamlit 버튼도 둥근 톤으로 */
    .stButton > button {{
        border-radius: 999px; border: 1px solid {p['border']};
        background: {p['card']}; color: {p['fg']}; font-weight: 800;
    }}
    .stDownloadButton > button {{
        border-radius: 999px; background: {p['primary']}; color: {p['primary_fg']};
        border: none; font-weight: 800;
        box-shadow: 0 10px 30px -8px rgba(40,138,107,0.35);
    }}

    /* Expander / Selectbox 라운딩 */
    details, div[data-testid="stExpander"] {{
        border-radius: 20px !important; border: 1px solid {p['border']} !important;
        background: {p['card']};
    }}

    /* ⚠️ 위기 관련 요소 — 접근성 고대비 원칙 유지 (원본 1_채팅.py 주석 계승) */
    /* crisis-card 도 위와 같은 이유로 st.container(key="crisis_card") 로 교체 —
       예전엔 이 div 안에 GPS 버튼, selectbox, expander 등 실제 위젯이 여러 개
       들어있었는데 그 위젯들이 카드 밖으로 렌더링되던 것과 같은 문제였음. */
    .st-key-crisis_card {{
        background: #FFFBEB; border: 2px solid #F59E0B; border-radius: 20px;
        padding: 1.2rem; margin: 0.8rem 0;
    }}
    .center-card {{
        background: white; border-radius: 16px; padding: 0.9rem 1.1rem;
        margin: 0.5rem 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border: 1px solid #E5E7EB;
    }}
    .emergency-box {{
        background: #FEF2F2; border-left: 4px solid #EF4444; padding: 0.8rem 1rem;
        border-radius: 0 14px 14px 0; margin-bottom: 0.8rem;
    }}
    .distortion-badge {{
        background: #ecd9f7; color: #5b3a75; padding: 4px 12px;
        border-radius: 20px; font-size: 0.85rem; font-weight: 700;
        display: inline-block; margin: 4px 2px;
    }}
    .pipeline-step {{
        background: #FFFDF6; border: 1px solid {p['border']};
        padding: 0.5rem 0.9rem; margin: 0.4rem 0;
        font-size: 0.85rem; color: #4b5f52; border-radius: 14px;
    }}
    .pipeline-step.done   {{ color: {p['fg_deep']}; font-weight: 700; }}
    .pipeline-step.error  {{ color: #991B1B; font-weight: 700; }}
    .pipeline-step.crisis {{ color: #92400E; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)


# ── 사이드바: 민트 아이콘 레일 (app-layout.tsx nav 이식) ──────────
# ⚠️ st.page_link()를 사용해야 함: <a href="/경로"> 같은 raw anchor는
#    이 Streamlit 버전에서 pages/ 폴더가 st.navigation()으로 등록되지
#    않은 경우 URL 매칭에 실패해 "Page not found"가 뜸.
#    st.page_link는 내부적으로 page_script_hash 기반으로 이동하므로
#    항상 정상 동작함 (공식 지원 API).
NAV = [
    ("home",      "app.py",                    "🏠", "마을 광장"),
    ("chat",      "pages/1_채팅.py",             "💬", "대화하기"),
    ("analytics", "pages/2_분석대시보드.py",       "📊", "마음 일기"),
    ("types",     "pages/3_생각도감.py",          "📖", "생각도감"),
    ("survey",    "pages/4_설문.py",             "📝", "사전 질문"),
    ("history",   "pages/5_이전대화기록.py",       "🗂️", "이전 대화"),
    ("career",    "pages/6_취업도우미.py",        "🌱", "취업 준비"),
]


def render_sidebar(active: str = "home"):
    is_logged_in = bool(st.session_state.get("is_logged_in"))
    with st.sidebar:
        for key, page, icon, label in NAV:
            st.page_link(resolve_page(page), label=label, icon=icon, use_container_width=True)
        st.markdown('<div style="flex:1;"></div>', unsafe_allow_html=True)  # 사이드바 이미 flex라 이게 토끼를 하단 고정
        if is_logged_in:
            if st.button("🐰 로그아웃", key="rabbit_logout_btn", use_container_width=True):
                for k in ("user_id", "user_email", "is_logged_in", "user_profile"):
                    st.session_state.pop(k, None)
                st.query_params.clear()
                st.switch_page(resolve_page("pages/0_로그인.py"))
        else:
            st.page_link(resolve_page("pages/0_로그인.py"), label="로그인", icon="🐰", use_container_width=True)


# ── 상단 바 (app-layout.tsx header 이식) ─────────────────────────
def render_topbar(show_new_chat: bool = True):
    """show_new_chat=False로 호출하면 우측 '새 대화' 버튼을 숨김
    (홈처럼 이미 자체 CTA가 있는 페이지에서 중복을 피하기 위함)"""
    col_pill, col_spacer, col_btn = st.columns([3, 3, 1])
    with col_btn:
        if show_new_chat:
            st.markdown(
                '<a href="/채팅" target="_self" class="btn-primary" '
                'style="width:100%;justify-content:center;">💌 새 대화</a>',
                unsafe_allow_html=True,
            )
    st.markdown(f'<div style="border-bottom:1px solid {PALETTE["border"]};margin:8px 0 1.4rem;"></div>',
                unsafe_allow_html=True)
    
    
# ── 서비스 이용 게이트: 로그인 + 필수 개인정보 동의 ────────────────
# 채팅/분석대시보드/이전대화기록/취업도우미처럼 실제로 대화·개인 데이터를
# 다루는 페이지 맨 위에서 호출한다. 로그인만 하고 사전 질문(4_설문.py)의
# 필수 동의(agreed_terms, agreed_sensitive_profile) 두 개를 아직 안 했으면
# 그 페이지 본문을 렌더링하지 않고 안내 후 st.stop() 한다.
# (이전엔 로그인 없이도 채팅이 되고, 세션 저장 조회만 막혀 있는 등 제한이
#  일관되지 않았음 — 이제 서비스 이용 자체를 필수 동의 뒤로 미룬다.)
def has_required_consent() -> bool:
    profile = st.session_state.get("user_profile") or {}
    privacy = profile.get("privacy") or {}
    return bool(privacy.get("agreed_terms")) and bool(privacy.get("agreed_sensitive_profile"))


def require_consent():
    if not st.session_state.get("is_logged_in"):
        st.warning("먼저 로그인해주세요.")
        if st.button("🔐 로그인하러 가기", key="require_consent_login_btn"):
            st.switch_page(resolve_page("pages/0_로그인.py"))
        st.stop()

    if not has_required_consent():
        st.warning("채팅, 마음 일기 등 서비스를 이용하려면 먼저 사전 질문의 필수 동의 항목을 완료해주세요.")
        if st.button("📝 사전 질문 하러 가기", key="require_consent_survey_btn"):
            st.switch_page(resolve_page("pages/4_설문.py"))
        st.stop()


def friendly_session_label(session_id: str, created_at: str | None = None) -> str:
    """긴 UUID 대신 생성 시각 기준 라벨 + 축약 ID로 표시."""
    short_id = (session_id or "")[:8]
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return f"{dt.strftime('%m/%d %H:%M')} 대화 (id: {short_id}…)"
        except ValueError:
            pass
    return f"대화 (id: {short_id}…)"

def safe_bubble_text(text: str) -> str:
    """메시지 안 실제 줄바꿈이 raw HTML 블록 파싱을 깨는 것 방지 — <br>로 치환."""
    return (text or "").replace("\r\n", "\n").replace("\n\n", "<br><br>").replace("\n", "<br>")
