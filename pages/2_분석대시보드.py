import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar

st.set_page_config(page_title="마음 일기 · 마음숲", page_icon="📊", layout="wide")
apply_theme()
render_sidebar(active="analytics")
render_topbar()

CHART = P["chart"]
GRID_COLOR = P["border"]
FONT = dict(family="Nunito, sans-serif", color=P["muted_fg"], size=12)


# ── 샘플 데이터 (기존 함수 유지) ──────────────────────────────────
def make_sample_data():
    distortions = ["이분법적 사고", "과잉일반화", "심리적 여과", "긍정 격하", "성급한 결론",
                   "과장/축소", "감정적 추론", "당위적 진술", "잘못된 명명", "개인화"]
    rows = []
    base = datetime.now() - timedelta(days=14)
    for i in range(30):
        rows.append({
            "timestamp": (base + timedelta(hours=i * 10)).strftime("%Y-%m-%d %H:%M"),
            "user_text": f"샘플 발화 {i+1}",
            "distortion": random.choice(distortions),
            "confidence": round(random.uniform(0.6, 0.98), 2),
            "route": random.choice(["STS", "RAG"]),
        })
    return rows


history = st.session_state.get("distortion_history", [])
using_sample = len(history) == 0
if using_sample:
    history = make_sample_data()

df_all = pd.DataFrame(history)
df_all["timestamp"] = pd.to_datetime(df_all["timestamp"])
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

if using_sample:
    st.info("💡 아직 대화 이력이 없어요. 샘플 데이터로 미리 보여드려요. **💬 대화하기**에서 대화하면 실제 데이터로 바뀝니다.")

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

# ── 통계 필 4개 (analytics.tsx Stat pills) ───────────────────────
top_distortion = df["distortion"].value_counts().index[0]
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

    dist_counts = df["distortion"].value_counts().head(7).reset_index()
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


letters = "".join(
    f"""<div style="border:1px solid {P['border']};background:rgba(255,248,231,0.6);
         border-radius:20px;padding:14px 16px;">
      <div style="display:flex;justify-content:space-between;gap:10px;">
        <div style="font-weight:700;font-size:.9rem;">{(r.user_text[:28] + '…') if len(r.user_text) > 28 else r.user_text}</div>
        <span style="font-size:.72rem;color:{P['muted_fg']};white-space:nowrap;">{rel_date(r.timestamp)}</span>
      </div>
      <div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;">
        <span class="ac-chip chip-coral">{r.distortion}</span>
        <span class="ac-chip chip-sky">{r.route}</span>
      </div>
    </div>"""
    for r in recent.itertuples()
)
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
    all_types = ["전체"] + sorted(df["distortion"].unique().tolist())
    selected_type = st.selectbox("왜곡 유형 필터", all_types)

    filtered_df = df if selected_type == "전체" else df[df["distortion"] == selected_type]

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
