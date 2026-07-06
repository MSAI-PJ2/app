"""[취업 준비] 공고 적합도 분석 · 자소서 초안 · 첨삭 — 마음갈피의 취준생 확장 페이지.

마음갈피의 CBT 상담과 이어지는 페이지다: "난 어디에도 못 붙을 거야" 같은
생각(과잉 일반화·파국화)에 대해, 실제 공고 분석 결과라는 **사실 근거**를 만들어 준다.

이 파일 하나만 pages/ 에 추가하면 된다. 팀원 코드는 건드리지 않는다.
(ui_theme.py 의 NAV 목록에 한 줄만 추가하면 사이드바에도 뜬다 — 없어도 동작은 함)

백엔드: gateway 의 /v1/career/* (career.py v5). api_client 의 주소/헤더 규약을 재사용.
"""
import json
import os

import requests
import streamlit as st
from dotenv import load_dotenv

from api_client import BACKEND_URL, _headers
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, require_consent

load_dotenv()

# 취준 기능 백엔드 주소 — 팀 게이트웨이와 분리 배포된 경우 .env 에
# CAREER_BACKEND_URL=https://maeumgalpi-api...  만 추가하면 된다.
# (없으면 팀 공용 BACKEND_URL 을 그대로 사용 → 나중에 게이트웨이가 합쳐지면 줄 삭제)
CAREER_URL = os.getenv("CAREER_BACKEND_URL", BACKEND_URL).rstrip("/")

st.set_page_config(page_title="취업 준비 · 마음갈피", page_icon="🌱", layout="wide")
apply_theme()
render_sidebar(active="career")
render_topbar()

# 로그인 + 필수 개인정보 동의(사전 질문) 없이는 취업 준비 기능을 이용할 수 없음
require_consent()


# ══════════════════════════════════════════════════════════════════════════
# [구획 1] 이 페이지 전용 스타일 — 전부 ui_theme 팔레트 토큰만 사용 (색 통일)
# ══════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<style>
.career-hero {{
  background:{P['card']}; border:1px solid {P['border']}; border-radius:18px;
  padding:1.1rem 1.4rem; margin-bottom:1rem;
}}
.pill {{
  display:inline-block; padding:.22rem .7rem; border-radius:999px;
  font-size:.85rem; font-weight:600; margin-right:.35rem; margin-bottom:.3rem;
}}
.pill-sand  {{ background:{P['sand']};  color:{P['fg']}; }}
.pill-leaf  {{ background:{P['leaf']};  color:{P['fg_deep']}; }}
.pill-sunny {{ background:{P['sunny']}; color:{P['fg']}; }}
.pill-coral {{ background:{P['coral']}; color:#FFF; }}
.score-big  {{ font-size:2.4rem; font-weight:800; color:{P['leaf_deep']}; line-height:1; }}
.evidence-card {{
  background:{P['leaf']}; border-radius:14px; padding:.7rem .95rem;
  color:{P['fg_deep']}; margin-bottom:.5rem; font-size:.95rem;
}}
.match-row {{ background:{P['card']}; border:1px solid {P['border']}; border-radius:12px;
  padding:.55rem .8rem; margin-bottom:.4rem; font-size:.92rem; color:{P['fg']}; }}
.small-note {{ color:{P['muted_fg']}; font-size:.8rem; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="career-hero">
  <div style="font-size:1.25rem; font-weight:800; color:{P['fg_deep']};">🌱 취업 준비 — 근거로 확인하는 나의 자리</div>
  <div class="small-note" style="margin-top:.3rem;">
    "다 떨어질 거야" 같은 생각이 들 때, 실제 공고와 내 경험을 비교한 <b>사실 근거</b>를 만들어 드려요.
    여기서 나온 근거 문장은 <b>대화하기</b>에서 말랑이가 함께 봐요.
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# [구획 2] 백엔드 호출 — api_client 의 주소/헤더 규약 재사용 (api_client 은 수정 안 함)
# ══════════════════════════════════════════════════════════════════════════

def career_post(path: str, body: dict, timeout: int = 120) -> dict:
    """career JSON 엔드포인트 호출 (profile / analyze / resume)."""
    r = requests.post(f"{CAREER_URL}/v1/career/{path}",
                      headers={**_headers(), "Content-Type": "application/json"},
                      json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


def career_stream(path: str, body: dict):
    """career SSE 엔드포인트(cover-letter / review)의 token 텍스트를 하나씩 yield.

    이벤트 형식이 /v1/respond 와 동일해서(meta→token→done) 채팅 페이지와 같은 방식으로 읽는다.
    """
    resp = requests.post(f"{CAREER_URL}/v1/career/{path}",
                         headers={**_headers(), "Content-Type": "application/json"},
                         json=body, stream=True, timeout=300)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        evt = json.loads(raw[6:])
        if evt.get("type") == "token":
            yield evt.get("text", "")
        elif evt.get("type") == "error":
            yield f"\n\n⚠️ 오류: {evt.get('message')}"


def show_api_error(exc: Exception):
    """실패 시 사용자에게 다음 행동을 알려준다 (막연한 사과 금지)."""
    detail = ""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text[:200]
    st.error(f"요청이 처리되지 않았어요. {detail or exc}")
    st.caption(f"서버 상태 확인: {CAREER_URL}/v1/career/diag")


# ══════════════════════════════════════════════════════════════════════════
# [구획 3] ① 내 이야기 입력 (프로필 저장)
# ══════════════════════════════════════════════════════════════════════════

st.subheader("① 내 이야기 입력")
st.caption("초안·첨삭은 여기 적은 경험 **안에서만** 만들어져요. 없는 이야기는 지어내지 않아요.")

with st.form("career_profile_form"):
    c1, c2 = st.columns(2)
    education = c1.text_input("학력/전공", placeholder="예: OO대학교 통계학과 4학년")
    target_role = c2.text_input("희망 직무", placeholder="예: 데이터 분석가")
    skills_raw = st.text_input("보유 기술 (쉼표로 구분)", placeholder="예: SQL, Python, Power BI")
    experiences = []
    for i in (1, 2, 3):
        e1, e2 = st.columns([1, 2])
        t = e1.text_input(f"경험{i} 제목", key=f"exp_t{i}",
                          placeholder="예: 공공데이터 공모전 장려상" if i == 1 else "")
        d = e2.text_input(f"경험{i} 내용", key=f"exp_d{i}",
                          placeholder="무엇을 해서 어떤 결과를 냈는지" if i == 1 else "")
        if t.strip():
            experiences.append({"title": t.strip(), "detail": d.strip()})
    saved = st.form_submit_button("내 이야기 저장", type="primary")

if saved:
    if not experiences:
        st.warning("경험을 1개 이상 적어주세요 — 초안과 첨삭의 재료가 돼요.")
    else:
        try:
            res = career_post("profile", {
                "education": education or None, "target_role": target_role or None,
                "skills": [s.strip() for s in skills_raw.split(",") if s.strip()],
                "experiences": experiences,
            })
            st.session_state.career_profile_id = res["profile_id"]
            st.success(f"저장했어요 — 경험 {res['experiences']}개")
        except Exception as exc:
            show_api_error(exc)

pid = st.session_state.get("career_profile_id")
if pid:
    st.markdown(f'<span class="pill pill-leaf">내 이야기 저장됨</span>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# [구획 4] ② 공고 분석 — 적합도 · 키워드 · 근거
# ══════════════════════════════════════════════════════════════════════════

st.subheader("② 채용공고 붙여넣기")
posting = st.text_area("공고 전문을 그대로 붙여넣어 주세요", height=180, key="career_posting",
                       placeholder="사람인·원티드 등에서 공고 본문을 복사해 붙여넣기")
if st.button("적합도 분석", type="primary", disabled=not pid):
    if len((posting or "").strip()) < 30:
        st.warning("공고 전문을 붙여넣어 주세요 (너무 짧아요).")
    else:
        with st.spinner("공고와 내 이야기를 비교하는 중..."):
            try:
                st.session_state.career_analysis = career_post(
                    "analyze", {"posting": posting, "profile_id": pid})
            except Exception as exc:
                show_api_error(exc)
if not pid:
    st.caption("먼저 ①에서 내 이야기를 저장해 주세요.")

a = st.session_state.get("career_analysis")
if a and "fit_score" in a:
    s1, s2 = st.columns([1, 2])
    with s1:
        st.markdown(f'<div class="score-big">{a["fit_score"]}<span style="font-size:1rem;">점</span></div>',
                    unsafe_allow_html=True)
        st.markdown(f'<span class="pill pill-sunny">{a.get("recommendation", "")}</span>',
                    unsafe_allow_html=True)
        st.caption(a.get("summary", ""))
    with s2:
        st.markdown("**이 공고의 키워드** — 자소서·이력서에 녹일 것")
        st.markdown("".join(f'<span class="pill pill-sand">{k}</span>'
                            for k in a.get("keywords", [])), unsafe_allow_html=True)
        js = a.get("job_summary") or {}
        if js.get("main_tasks"):
            st.caption("핵심 업무: " + " · ".join(js["main_tasks"]))

    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**이미 갖춘 것** ✅")
        for m in a.get("matched", []):
            st.markdown(f'<div class="match-row">✅ <b>{m.get("requirement","")}</b><br>'
                        f'<span class="small-note">{m.get("evidence","")}</span></div>',
                        unsafe_allow_html=True)
    with m2:
        st.markdown("**보완하면 좋은 것** 🌱")
        for g in a.get("gaps", []):
            st.markdown(f'<div class="match-row">🌱 <b>{g.get("requirement","")}</b><br>'
                        f'<span class="small-note">{g.get("how_to_fill","")}</span></div>',
                        unsafe_allow_html=True)

    if a.get("reframe_evidence"):
        st.markdown("**말랑이가 기억할 사실 근거** — \"다 안 될 거야\"라는 생각이 들 때 함께 봐요")
        for ev in a["reframe_evidence"]:
            st.markdown(f'<div class="evidence-card">🍃 {ev}</div>', unsafe_allow_html=True)
    st.caption(a.get("caveat", ""))
elif a:  # parse_error 등
    st.warning("분석 결과를 읽지 못했어요. 다시 한번 시도해 주세요.")


# ══════════════════════════════════════════════════════════════════════════
# [구획 5] ③ 자소서 초안 / 첨삭
# ══════════════════════════════════════════════════════════════════════════

st.subheader("③ 자소서")
tab_draft, tab_review = st.tabs(["초안 만들기", "내 글 첨삭받기"])

with tab_draft:
    q = st.text_input("자소서 문항", value="지원 동기와 입사 후 포부를 기술하시오.")
    mc = st.number_input("글자수 제한(공백 포함)", 300, 3000, 1000, step=100)
    if st.button("초안 만들기", type="primary", disabled=not (pid and posting)):
        box = st.empty()
        acc = ""
        try:
            for tok in career_stream("cover-letter",
                                     {"posting": posting, "question": q,
                                      "max_chars": int(mc), "profile_id": pid}):
                acc += tok
                box.markdown(acc + "▌")
            box.markdown(acc)
        except Exception as exc:
            show_api_error(exc)
    if not (pid and posting):
        st.caption("①(내 이야기)과 ②(공고)를 먼저 채워주세요.")
    st.markdown('<div class="small-note">초안 끝의 [근거 매핑]에서 어떤 경험을 썼는지 확인하고, 반드시 직접 다듬어 주세요.</div>',
                unsafe_allow_html=True)

with tab_review:
    doc_type = st.radio("무엇을 첨삭할까요?", ["자소서", "이력서"], horizontal=True)
    draft = st.text_area("내가 쓴 글을 붙여넣어 주세요", height=200, key="career_draft")
    if st.button("첨삭받기", type="primary", disabled=not pid):
        if len((draft or "").strip()) < 50:
            st.warning("첨삭할 글을 붙여넣어 주세요 (너무 짧아요).")
        else:
            box = st.empty()
            acc = ""
            try:
                for tok in career_stream("review", {
                        "draft": draft, "posting": posting or None,
                        "doc_type": "resume" if doc_type == "이력서" else "cover_letter",
                        "profile_id": pid}):
                    acc += tok
                    box.markdown(acc + "▌")
                box.markdown(acc)
            except Exception as exc:
                show_api_error(exc)
    st.markdown('<div class="small-note">첨삭은 수정 제안만 드려요 — [사실 확인 필요]가 뜨면 그 문장은 꼭 확인하세요.</div>',
                unsafe_allow_html=True)
