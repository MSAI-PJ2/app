import html
import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import explain_turn, get_session
from demo_data import DEMO_USER_ID, DEMO_LOGIN_UID, demo_stats_rows
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar, require_consent

st.set_page_config(page_title="마음 일기 · 마음숲", page_icon="📊", layout="wide")
apply_theme()
render_sidebar(active="analytics")
render_topbar()

# 로그인 + 필수 개인정보 동의(사전 질문) 없이는 분석 대시보드를 이용할 수 없음
require_consent()

CHART = P["chart"]
GRID_COLOR = P["border"]
FONT = dict(family="Nunito, sans-serif", color=P["muted_fg"], size=12)

# ── 기관 보고서 보기 (토글) — 예시 환자 1명 기준, 전부 목업 데이터 ──
# ⚠️ "관리자"라는 표현은 쓰지 않기로 결정 (유관기관에 가져가는 문서이므로 "보고서"로 통일)
# st.stop()으로 여기서 끝내기 때문에 아래 개인용 코드는 전혀 안 건드려도 된다.
admin_view = st.toggle("🏥 기관 제출용 보고서 보기 (환자)", key="report_view_toggle")
if admin_view:
    st.markdown(f"""
<span class="ac-chip chip-sky">🏥 기관 제출용 보고서</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">환자 기록 보고서</h1>
""", unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    _admin_plotly_layout = dict(margin=dict(t=10, b=10, l=10, r=10),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=FONT)

    # (1) 날짜별 이용 추이
    st.markdown('<div class="font-display" style="font-size:1.1rem;margin-bottom:6px;">📈 날짜별 서비스 이용 추이</div>',
               unsafe_allow_html=True)
    usage_df = pd.DataFrame([
        {"date": "2026-06-30", "count": 1}, {"date": "2026-07-01", "count": 2},
        {"date": "2026-07-02", "count": 0}, {"date": "2026-07-03", "count": 3},
        {"date": "2026-07-04", "count": 1}, {"date": "2026-07-05", "count": 2},
    ])
    fig_usage = go.Figure(go.Scatter(x=usage_df["date"], y=usage_df["count"],
                                     mode="lines+markers", line=dict(color=P["primary"], width=3),
                                     marker=dict(size=8)))
    fig_usage.update_layout(**_admin_plotly_layout, height=280)
    fig_usage.update_xaxes(gridcolor=GRID_COLOR, griddash="dash")
    fig_usage.update_yaxes(gridcolor=GRID_COLOR, griddash="dash", title="대화 횟수")
    st.plotly_chart(fig_usage, use_container_width=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # (2) 인지왜곡 유형 빈도
    st.markdown('<div class="font-display" style="font-size:1.1rem;margin-bottom:6px;">🧠 인지왜곡 유형 빈도</div>',
               unsafe_allow_html=True)
    dist_df = pd.DataFrame([
        {"label": "과잉일반화", "count": 5}, {"label": "흑백 사고", "count": 3},
        {"label": "감정적 추론", "count": 2},
    ])
    fig_dist = go.Figure(go.Bar(
        x=dist_df["label"], y=dist_df["count"],
        marker=dict(color=[CHART[i % len(CHART)] for i in range(len(dist_df))]),
    ))
    fig_dist.update_layout(**_admin_plotly_layout, height=280, barcornerradius=10, showlegend=False)
    fig_dist.update_xaxes(showgrid=False)
    fig_dist.update_yaxes(gridcolor=GRID_COLOR, griddash="dash")
    st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # (3) 사전 질문 응답 그대로 — 비율/통계가 아니라 실제 응답 형식으로
    st.markdown('<div class="font-display" style="font-size:1.1rem;margin-bottom:10px;">🏥 사전 질문 응답 (진료·상담 이력)</div>',
               unsafe_allow_html=True)
    survey_answers = [
        ("기존 상담 경험", "있음"),
        ("기존 진단/치료 경험", "없음"),
        ("현재 도움받는 사람/기관", "없음"),
        ("어느 정도로 이야기하고 싶어요?", "자세히"),
        ("위기 상황에서 선호하는 도움 방식", "가까운 기관 안내, 긴급전화 표시, 비상연락처 표시"),
    ]
    for title, answer in survey_answers:
        st.markdown(f"""
<div class="ac-card" style="padding:.9rem 1.2rem;margin-bottom:.6rem;display:flex;justify-content:space-between;align-items:center;">
  <span style="font-size:.85rem;color:{P['muted_fg']};">{title}</span>
  <b style="color:{P['primary']};">{answer}</b>
</div>""", unsafe_allow_html=True)

    st.stop()


# ── 샘플 데이터 (백엔드 세션이 없을 때만 사용) ────────────────────
# 유형별로 실제 발화처럼 보이는 예문을 매칭한다 ("샘플 발화 1"류의 자리표시자 대신).
SAMPLE_UTTERANCES = {
    "이분법적 사고": "완벽하게 해내지 못하면 그건 완전히 실패한 거나 마찬가지예요",
    "과잉일반화": "이번에도 망쳤으니까 저는 뭘 해도 항상 이런 식이에요",
    "심리적 여과": "다른 건 다 괜찮았는데 그 한마디만 계속 마음에 걸려요",
    "긍정 격하": "칭찬을 받긴 했지만 그냥 운이 좋았을 뿐 제 실력은 아니에요",
    "성급한 결론": "답장이 늦는 걸 보니 저한테 관심이 없는 게 분명해요",
    "과장/축소": "작은 실수 하나 했을 뿐인데 모든 게 다 무너진 기분이에요",
    "감정적 추론": "이렇게 불안한 걸 보면 분명 안 좋은 일이 생길 것 같아요",
    "당위적 진술": "저는 항상 완벽해야 하고 실수는 절대 하면 안 돼요",
    "잘못된 명명": "저는 원래 게으르고 무능한 사람이에요",
    "개인화": "회의가 잘 안 풀린 건 다 저 때문인 것 같아요",
}


def make_sample_data():
    distortions = list(SAMPLE_UTTERANCES.keys())
    rows = []
    base = datetime.now() - timedelta(days=14)
    for i in range(30):
        picked = random.choice(distortions)
        rows.append({
            "timestamp": (base + timedelta(hours=i * 10)).strftime("%Y-%m-%d %H:%M"),
            "user_text": SAMPLE_UTTERANCES[picked],
            "distortion": picked,
            "confidence": round(random.uniform(0.6, 0.98), 2),
            "route": random.choice(["STS", "RAG"]),
            "turn_index": None,
        })
    return rows


def load_session_turns(session_id: str) -> list[dict]:
    """Cosmos 에 저장된 세션 턴을 가져와 대시보드 행 형태로 변환.

    turn_index 를 함께 저장해둬야 "연산 과정 보기"에서 어떤 턴을 설명할지 정확히 특정할 수 있다
    (session.py 의 turns 배열 인덱스와 동일해야 GET .../turns/{turn_index}/explain 이 맞게 동작함).

    2026-07-04 게이트웨이 업데이트로 사용자 턴에 selected_labels(멀티라벨 전체 점수)와
    analysis(컨텍스트 병합 여부)가 추가로 저장된다 — confidence 는 이제 selected_labels 에서
    실제 값을 가져오고(예전엔 임시로 1.0 고정), context_merged 는 SHAP 경고 표시에 쓴다.
    """
    state = get_session(session_id)
    if not state:
        return []
    turns = state.get("turns", [])
    rows = []
    for i, t in enumerate(turns):
        if t.get("role") != "user" or not (t.get("text") or "").strip():
            continue
        primary = t.get("primary") or "미분류"
        selected = t.get("selected_labels") or []
        confidence = next((l["score"] for l in selected if l["label"] == primary), None)
        if confidence is None:
            confidence = 1.0  # 구버전 세션(selected_labels 없음) 폴백
        next_turn = turns[i + 1] if i + 1 < len(turns) else {}
        route = "RAG" if next_turn.get("rag_chunk_ids") else "STS"
        rows.append({
            "timestamp": t.get("ts") or state.get("updated_at"),
            "user_text": t.get("text", ""),
            "distortion": primary,
            "confidence": confidence,
            "route": route,
            "turn_index": i,
            "context_merged": bool((t.get("analysis") or {}).get("context_merged")),
        })
    return rows


# ── 세션 선택 (Cosmos 실데이터 vs 샘플) ────────────────────────────
default_session = st.session_state.get("session_id", "")
with st.expander("🔎 조회할 세션 ID", expanded=False):
    session_id_input = st.text_input(
        "세션 ID", value=default_session,
        help="비워두면 현재 대화 세션(방금 대화하기에서 쓰던 session_id)을 사용합니다.")
session_id = (session_id_input or default_session or "").strip()

# [데모 id 트리거] ① 데모 이메일로 로그인(user_id==DEMO_LOGIN_UID) ② 조회 세션 ID 에
# DEMO_USER_ID 입력 — 둘 중 하나면 그 사용자의 세션들을 가로지른 집계 통계를 프론트 내장
# 픽스처(실라벨·합성날짜)로 주입한다. 발화는 배포 분류기로 실제 라벨링했고 세션 볼륨·날짜만
# 합성 — 라이브 Cosmos 파이프라인은 아님. (기관 '보고서' 토글은 위에서 st.stop 으로 끝나는
# 별개 목업이라 데모 트리거가 아니다 — main 최신화로 관리자 토글→보고서 목업 채택)
is_demo = (session_id == DEMO_USER_ID
           or st.session_state.get("user_id") == DEMO_LOGIN_UID)
if is_demo:
    history = demo_stats_rows()
    using_sample = False
else:
    history = load_session_turns(session_id) if session_id else []
    using_sample = len(history) == 0
    if using_sample:
        history = make_sample_data()

df_all = pd.DataFrame(history)
df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], utc=True).dt.tz_localize(None)
df_all["date"] = df_all["timestamp"].dt.date

# ── 헤더 + 기간 필터 (analytics.tsx 상단) ────────────────────────
head_l, head_r = st.columns([3, 1.4])
with head_l:
    st.markdown(f"""
<span class="ac-chip chip-lilac">📓 마음 일기</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">이번 주 마을 소식</h1>
<p style="margin:0;font-size:.87rem;color:{P['muted_fg']};">
대화를 모아 살짝 들여다봤어요. 조금씩 초록으로 물들고 있어요 🌱</p>
""", unsafe_allow_html=True)
with head_r:
    period = st.radio("기간", ["이번 주", "이번 달", "전체"], horizontal=True, label_visibility="collapsed")

# 기간 필터 적용 (Lovable 필 버튼을 실제 기능으로 구현)
now = datetime.now()
if period == "이번 주":
    df = df_all[df_all["timestamp"] >= now - timedelta(days=7)]
elif period == "이번 달":
    df = df_all[df_all["timestamp"] >= now - timedelta(days=30)]
else:
    df = df_all
if df.empty:
    df = df_all  # 필터 결과가 없으면 전체 표시

if is_demo:
    from demo_data import DEMO_SESSION_COUNT
    st.caption(f"🧪 데모 통계 — 사용자 `{DEMO_USER_ID}` 의 세션 {DEMO_SESSION_COUNT}개를 가로질러 집계한 "
               f"기록 {len(df_all)}건(발화당 대표 왜곡). 기간 필터·분포는 실제로 동작합니다.")
elif using_sample:
    pass
else:
    st.caption(f"세션 `{session_id[:8]}…` 의 실제 대화 기록 {len(df_all)}건을 표시하고 있어요.")

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

# '불충분'(신호 부족)·'정상'·'미분류'는 인지왜곡 유형이 아니므로, 왜곡 지표
# (최다 감지 왜곡·왜곡 유형 분포)에서는 제외한다. '대화' 총계·신뢰도는 전체 기준.
NON_DISTORTIONS = ("불충분", "정상", "미분류")
df_distortion = df[~df["distortion"].isin(NON_DISTORTIONS)]


def distortion_label(d):
    """왜곡이 아닌 분류(불충분/정상/미분류)는 화면에 '왜곡 없음'으로 표기한다 —
    이력 표·편지 칩에서 이들이 '왜곡 유형'처럼 보이지 않게 하려는 것. (대화 자체는
    이력에 남기되, 왜곡으로 오분류하지 않는다.)"""
    return "왜곡 없음" if d in NON_DISTORTIONS else d


# ── 통계 필 4개 (analytics.tsx Stat pills) ───────────────────────
_dist_vc = df_distortion["distortion"].value_counts()
top_distortion = _dist_vc.index[0] if not _dist_vc.empty else "—"
avg_conf = df["confidence"].mean()
rag_ratio = (df["route"] == "RAG").mean()
n_days = df["date"].nunique()

stats = [
    ("💬", str(len(df)), "대화", "rgba(192,248,229,0.5)"),
    ("🧠", top_distortion, "최다 감지 왜곡", "rgba(227,154,134,0.28)"),
    ("🌟", f"{avg_conf:.0%}", "평균 분류 신뢰도", "rgba(243,221,143,0.5)"),
    ("🌱", f"{n_days}일", "기록된 날", "rgba(217,184,232,0.4)"),
]
cols = st.columns(4, gap="medium")
for col, (emoji, num, label, tone) in zip(cols, stats):
    with col:
        st.markdown(f"""
<div class="ac-card" style="display:flex;align-items:center;gap:14px;padding:1.1rem 1.2rem;">
  <div style="width:52px;height:52px;border-radius:18px;background:{tone};
       display:flex;align-items:center;justify-content:center;font-size:24px;">{emoji}</div>
  <div>
    <div class="font-display" style="font-size:{'1rem' if len(num) > 5 else '1.5rem'};">{num}</div>
    <div style="font-size:.72rem;color:{P['muted_fg']};">{label}</div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 차트: [왜곡 유형 분포 3/5 | 변화의 흐름 2/5] ─────────────────
c_bar, c_line = st.columns([3, 2], gap="medium")

_plotly_layout = dict(
    margin=dict(t=10, b=10, l=10, r=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=FONT,
)

with c_bar:
    st.markdown(f"""
<div class="ac-card" style="padding:1.3rem 1.4rem .2rem;border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom:none;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div class="font-display" style="font-size:1.05rem;">왜곡 유형 분포</div>
      <div style="font-size:.72rem;color:{P['muted_fg']};">가장 자주 찾아온 생각들</div>
    </div>
    <span class="ac-chip chip-sunny">🏆 상위 7</span>
  </div>
</div>""", unsafe_allow_html=True)

    dist_counts = df_distortion["distortion"].value_counts().head(7).reset_index()
    dist_counts.columns = ["distortion", "count"]
    fig_bar = go.Figure(go.Bar(
        x=dist_counts["distortion"], y=dist_counts["count"],
        marker=dict(color=[CHART[i % len(CHART)] for i in range(len(dist_counts))]),
    ))
    fig_bar.update_layout(**_plotly_layout, height=300, barcornerradius=10, showlegend=False)
    fig_bar.update_xaxes(tickangle=-15, tickfont=dict(size=11), showgrid=False)
    fig_bar.update_yaxes(gridcolor=GRID_COLOR, griddash="dash", zerolinecolor=GRID_COLOR)
    st.plotly_chart(fig_bar, use_container_width=True)

with c_line:
    st.markdown(f"""
<div class="ac-card" style="padding:1.3rem 1.4rem .2rem;border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom:none;">
  <div class="font-display" style="font-size:1.05rem;">변화의 흐름</div>
  <div style="font-size:.72rem;color:{P['muted_fg']};">날짜별 왜곡 감지와 RAG 심화 재구성</div>
</div>""", unsafe_allow_html=True)

    # 날짜별: 왜곡 = 감지 건수 전체, 심화 재구성 = RAG 라우팅되어 문서 기반 재구성을 받은 건수
    daily = df.groupby("date").agg(왜곡=("distortion", "size")).reset_index()
    rag_daily = df[df["route"] == "RAG"].groupby("date").size()
    daily["심화 재구성"] = daily["date"].map(rag_daily).fillna(0).astype(int)
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=daily["date"], y=daily["왜곡"], name="왜곡",
                                  mode="lines+markers", line=dict(color=P["coral"], width=3),
                                  marker=dict(size=7)))
    fig_line.add_trace(go.Scatter(x=daily["date"], y=daily["심화 재구성"], name="심화 재구성",
                                  mode="lines+markers", line=dict(color=P["primary"], width=3),
                                  marker=dict(size=7)))
    fig_line.update_layout(**_plotly_layout, height=300,
                           legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    fig_line.update_xaxes(gridcolor=GRID_COLOR, griddash="dash")
    fig_line.update_yaxes(gridcolor=GRID_COLOR, griddash="dash")
    st.plotly_chart(fig_line, use_container_width=True)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 최근 대화 편지 (analytics.tsx Recent sessions) ───────────────
recent = df.sort_values("timestamp", ascending=False).head(4)


def rel_date(ts: datetime) -> str:
    d = (datetime.now().date() - ts.date()).days
    return "오늘" if d == 0 else "어제" if d == 1 else f"{d}일 전"


def safe_preview(text: str, limit: int = 28) -> str:
    """실제 사용자 발화를 HTML 카드에 안전하게 삽입한다.

    사용자가 '<', '>', '&' 같은 문자를 입력하면 이스케이프 없이 그대로 HTML에 꽂아 넣던
    기존 코드가 마크업을 깨뜨려 태그/코드가 화면에 그대로 노출되는 버그가 있었다. 자르기는
    원문 기준으로 먼저 하고, 그 다음에 이스케이프해서 엔티티가 잘리지 않게 한다.
    """
    truncated = (text[:limit] + "…") if len(text) > limit else text
    return html.escape(truncated)


def build_letter_card(r) -> str:
    """편지 카드 하나를 만든다.

    ⚠️ 반드시 줄바꿈 없이 한 줄짜리 조각만 이어붙일 것. 예전 코드는 여러 줄 f-string 안에
    `{조건부 표현식}`을 한 줄 통째로 넣었는데, session_name이 없는(=거의 항상) 경우 그 표현식이
    빈 문자열로 치환되면서 그 줄 전체가 "공백만 있는 줄"이 돼버렸다. Streamlit 마크다운
    파서는 공백 줄을 만나면 거기서 HTML 블록이 끝났다고 판단해서, 그 다음에 오는 태그들을
    HTML이 아니라 들여쓰기된 텍스트(코드)로 그대로 노출시켰다 — 이게 "코드 노출" 버그의
    근본 원인이었다. 한 줄 문자열만 이어붙이면 애초에 공백 줄이 생길 수 없다.
    """
    session_name = getattr(r, "session_name", "")
    session_chip = (
        f'<span class="ac-chip chip-lilac">📁 {html.escape(session_name)}</span>'
        if session_name else ""
    )
    return (
        f'<div style="border:1px solid {P["border"]};background:rgba(255,248,231,0.6);'
        f'border-radius:20px;padding:14px 16px;">'
        f'<div style="display:flex;justify-content:space-between;gap:10px;">'
        f'<div style="font-weight:700;font-size:.9rem;">{safe_preview(r.user_text)}</div>'
        f'<span style="font-size:.72rem;color:{P["muted_fg"]};white-space:nowrap;">{rel_date(r.timestamp)}</span>'
        f'</div>'
        f'<div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;align-items:center;">'
        f'{session_chip}'
        f'<span class="ac-chip chip-coral">{distortion_label(r.distortion)}</span>'
        f'<span class="ac-chip chip-sky">{r.route}</span>'
        f'</div>'
        f'</div>'
    )


letters = "".join(build_letter_card(r) for r in recent.itertuples())
st.markdown(f"""
<div class="ac-card" style="padding:1.4rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <div class="font-display" style="font-size:1.05rem;">최근 대화 편지</div>
    <span class="ac-chip">📬 {len(recent)}개</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">{letters}</div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 전체 이력 표 + CSV 다운로드 (기존 기능 유지 — expander로 정리) ──
with st.expander("📋 전체 대화 이력 조회 · 필터 · CSV 다운로드"):
    hist = df.copy()
    hist["distortion"] = hist["distortion"].apply(distortion_label)  # 불충분/정상 → '왜곡 없음'
    all_types = ["전체"] + sorted(hist["distortion"].unique().tolist())
    selected_type = st.selectbox("왜곡 유형 필터", all_types)

    filtered_df = hist if selected_type == "전체" else hist[hist["distortion"] == selected_type]

    display_df = filtered_df[["timestamp", "distortion", "confidence", "route", "user_text"]].copy()
    display_df.columns = ["시간", "왜곡 유형", "신뢰도", "라우팅", "발화 내용"]
    display_df["신뢰도"] = display_df["신뢰도"].apply(lambda x: f"{x:.0%}")
    display_df = display_df.sort_values("시간", ascending=False)

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)

    csv = display_df.to_csv(index=False).encode("utf-8-sig")  # 한글 깨짐 방지
    st.download_button(
        label="⬇️ CSV로 다운로드",
        data=csv,
        file_name=f"cbt_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── 연산 과정 보기 (SHAP) — 실제 세션 데이터가 있을 때만 노출 ─────
# 캐싱하지 않고 버튼을 누를 때마다 백엔드(cogdist)에서 새로 계산한다 (팀 결정: 구현 단순성 우선).
if not using_sample and not is_demo:  # SHAP은 실제 게이트웨이 세션이 필요 — 데모 픽스처엔 미노출
    with st.expander("🔬 연산 과정 보기 — 분류기가 어떤 단어에 주목했는지"):
        st.caption("특정 발화를 골라 SHAP 값을 계산합니다. 매 요청마다 새로 계산되어 몇 초~수십 초 걸릴 수 있어요.")
        turn_rows = [r for r in history if r.get("turn_index") is not None]
        if not turn_rows:
            st.caption("설명할 수 있는 발화가 없어요.")
        else:
            options = {
                f"[{r['distortion']}] {r['user_text'][:40]}{'…' if len(r['user_text']) > 40 else ''}"
                f"{' ⚠️병합' if r.get('context_merged') else ''}": r["turn_index"]
                for r in turn_rows
            }
            picked_label = st.selectbox("발화 선택", list(options.keys()), key="shap_turn_pick")
            picked_index = options[picked_label]
            if "⚠️병합" in picked_label:
                st.caption("⚠️ 이 발화는 직전 대화와 합쳐서 분류됐어요(문맥 병합). "
                          "아래 SHAP은 원문 단독 기준이라 실제 판단 근거와 다르게 보일 수 있어요.")

            if st.button("⚡ 연산 과정 계산하기", key="shap_run_btn"):
                try:
                    with st.spinner("SHAP 계산 중… (문장 길이에 따라 몇 초~수십 초 걸릴 수 있어요)"):
                        result = explain_turn(session_id, picked_index)
                    st.session_state["shap_result"] = result
                except Exception as e:
                    st.error(f"SHAP 계산 실패: {e}")
                    st.session_state.pop("shap_result", None)

            shap_result = st.session_state.get("shap_result")
            if shap_result:
                if shap_result.get("context_merged"):
                    st.warning("⚠️ 이 턴은 문맥 병합으로 분류됐어요 — 아래 결과는 원문 단독 기준입니다.")
                st.markdown(f"**설명 대상 라벨:** `{shap_result['label']}` · 기준값(base value, logit): {shap_result['base_value']:.3f}")
                tok_df = pd.DataFrame(shap_result["tokens"])
                if not tok_df.empty:
                    tok_df = tok_df.reindex(tok_df["shap_value"].abs().sort_values(ascending=True).index)
                    # 색상은 팀 SHAP 리포트(tests/SHAP/shap_visual.py)와 동일하게 통일:
                    # 빨강(#E8534A)=해당 라벨 쪽으로 강화, 파랑(#4A90D9)=약화
                    fig_shap = go.Figure(go.Bar(
                        x=tok_df["shap_value"], y=tok_df["token"], orientation="h",
                        marker=dict(color=["#E8534A" if v > 0 else "#4A90D9" for v in tok_df["shap_value"]]),
                    ))
                    fig_shap.update_layout(
                        margin=dict(t=10, b=10, l=10, r=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=FONT, height=max(220, 26 * len(tok_df)),
                    )
                    fig_shap.update_xaxes(gridcolor=GRID_COLOR, griddash="dash", zerolinecolor=P["muted_fg"],
                                          title="라벨 판단에 대한 영향(logit) — 오른쪽=강화, 왼쪽=약화")
                    st.plotly_chart(fig_shap, use_container_width=True)
                else:
                    st.caption("토큰 기여도를 계산하지 못했어요.")
