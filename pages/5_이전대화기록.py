"""이전 대화 기록 — 로그인한 사용자의 세션 목록을 카드로 보여주고, 클릭하면 그 대화를 다시 연다.

카드 제목은 세션 ID가 아니라 "그 대화방의 첫 발화 미리보기 + 상대적 날짜"로 표시한다
(session.py 의 preview 필드, 오늘 이후 새로 시작한 대화부터 채워짐).
가상 ID 도입 이전에 만들어진 옛날 세션(user_id 없음)은 목록 API에 안 잡힐 수 있다 —
그런 세션은 "세션 ID로 직접 조회" expander로 여전히 찾을 수 있게 남겨둔다.
"""
from datetime import datetime

import streamlit as st

from api_client import get_session, list_sessions
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, require_consent, safe_bubble_text

st.set_page_config(page_title="이전 대화 기록 · 마음숲", page_icon="🗂️", layout="wide")
apply_theme()
render_sidebar(active="history")
render_topbar(show_new_chat=False)

# 로그인 + 필수 개인정보 동의(사전 질문) 없이는 이전 대화 기록을 이용할 수 없음
require_consent()

st.markdown(f"""
<span class="ac-chip chip-sky">🗂️ 이전 대화</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">지난 대화를 다시 열어볼게요</h1>
<p style="margin:0;font-size:.87rem;color:{P['muted_fg']};">
내 대화방 목록에서 골라서 다시 볼 수 있어요.</p>
""", unsafe_allow_html=True)

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)


def rel_date(iso_str: str | None) -> str:
    """ISO 시각 문자열 → "오늘"/"어제"/"N일 전" (파싱 실패하면 빈 문자열)."""
    if not iso_str:
        return ""
    try:
        d = (datetime.now().date() - datetime.fromisoformat(iso_str).date()).days
    except (ValueError, TypeError):
        return ""
    return "오늘" if d == 0 else "어제" if d == 1 else f"{d}일 전"


# ── 내 세션 목록 (가상 ID 기준) ────────────────────────────────────
try:
    my_sessions = list_sessions()
except Exception as e:
    my_sessions = []
    st.warning(f"세션 목록을 불러오지 못했어요. 아래 직접 조회를 이용해주세요. ({e})")

selected_session_id = None

if my_sessions:
    for s in my_sessions:
        preview = (s.get("preview") or "").strip() or "(첫 발화 없음)"
        title = preview[:28] + "…" if len(preview) > 28 else preview
        col_l, col_r = st.columns([4, 1])
        with col_l:
            st.markdown(f"""
<div class="ac-card" style="padding:.9rem 1.1rem;">
  <div class="font-display" style="font-size:.95rem;">{title}</div>
  <div style="font-size:.75rem;color:{P['muted_fg']};margin-top:2px;">
    {rel_date(s.get('created_at'))} · 총 {s.get('turn_count', 0)}개 발화</div>
</div>""", unsafe_allow_html=True)
        with col_r:
            if st.button("열기", key=f"open_{s['session_id']}", use_container_width=True):
                selected_session_id = s["session_id"]
else:
    st.info("아직 목록에 잡히는 대화방이 없어요. 대화를 시작하면 여기 쌓여요.")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ── 옛날 세션(가상 ID 도입 이전) 대비 — 직접 ID로 조회 ─────────────
with st.expander("🔎 세션 ID로 직접 조회하기 (옛날 대화방 등)"):
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        manual_id = st.text_input("대화방 ID (session_id)", value="",
                                  placeholder="예: 3f1c9e2a-...", label_visibility="collapsed")
    with col_btn:
        search_clicked = st.button("🔍 조회하기", use_container_width=True)
    if search_clicked and manual_id.strip():
        selected_session_id = manual_id.strip()

if selected_session_id:
    st.session_state["history_last_session"] = selected_session_id
    with st.spinner("불러오는 중…"):
        st.session_state["history_state"] = get_session(selected_session_id)

state = st.session_state.get("history_state")

if state is None:
    if st.session_state.get("history_last_session"):
        st.error("세션을 찾을 수 없어요. ID를 다시 확인해주세요.")
else:
    turns = state.get("turns", [])
    meta_l, meta_r = st.columns([2, 1])
    with meta_l:
        preview = (state.get("preview") or "").strip()
        title = (preview[:28] + "…" if len(preview) > 28 else preview) if preview else "대화방"
        st.markdown(f"""
<div class="ac-card" style="padding:1.1rem 1.3rem;">
  <div class="font-display" style="font-size:1rem;">{title}</div>
  <div style="font-size:.78rem;color:{P['muted_fg']};margin-top:4px;">
    {rel_date(state.get('created_at'))} · 총 {state.get('turn_count', len(turns))}개 발화</div>
</div>""", unsafe_allow_html=True)
    with meta_r:
        if st.button("💬 이 세션으로 계속 대화하기", use_container_width=True):
            st.session_state.session_id = state["session_id"]
            st.switch_page("pages/1_채팅.py")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    if not turns:
        st.info("이 대화방에는 아직 저장된 발화가 없어요.")
    else:
        # 메시지마다 개별 st.markdown 호출 — 1_채팅.py와 동일한 이유로 격리 렌더링.
        # 시간 표시는 raw HTML(<div class="msg-time">)이 아니라 st.caption()으로 —
        # HTML 파싱을 안 거쳐서 코드가 텍스트로 노출되는 문제가 구조적으로 불가능해짐.
        st.markdown('<div class="chat-body">', unsafe_allow_html=True)
        for i, t in enumerate(turns):
            role = t.get("role")
            text = (t.get("text") or "").strip()
            ts = t.get("ts", "")
            try:
                time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M") if ts else ""
            except ValueError:
                time_str = ts

            if t.get("event") == "crisis":
                st.markdown(f"""
<div class="msg-row">
  <div class="msg-avatar bot">🚨</div>
  <div class="msg-col">
    <div class="bubble bot" style="border:1px solid #E39A86;">{safe_bubble_text(text) or '(위기 대응 메시지)'}</div>
  </div>
</div>""", unsafe_allow_html=True)
                st.caption(f"{time_str} · 위기 대응")
                continue

            if not text:
                continue  # STT/OCR 실패, 빈 입력 등 텍스트 없는 기록은 목록에서 생략

            if role == "user":
                badge = f' · 🧠 {t["primary"]}' if t.get("primary") else ""
                st.markdown(f"""
<div class="msg-row me">
  <div class="msg-col me">
    <div class="bubble me">{safe_bubble_text(text)}</div>
  </div>
  <div class="msg-avatar me">🐰</div>
</div>""", unsafe_allow_html=True)
                st.caption(f"#{i} · {time_str}{badge}")
            else:
                rag_badge = f' · 📚 참고자료 {len(t["rag_chunk_ids"])}개' if t.get("rag_chunk_ids") else ""
                st.markdown(f"""
<div class="msg-row">
  <div class="msg-avatar bot">🍃</div>
  <div class="msg-col">
    <div class="bubble bot">{safe_bubble_text(text)}</div>
  </div>
</div>""", unsafe_allow_html=True)
                st.caption(f"#{i} · {time_str}{rag_badge}")
        st.markdown('</div>', unsafe_allow_html=True)
