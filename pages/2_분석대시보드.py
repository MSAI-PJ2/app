# ─────────────────────────────────────────────────────────────────
# pages/2_분석대시보드.py
# 채팅 이력을 바탕으로 인지왜곡 유형 분포, 변화 추이, 대화 이력 시각화
# ─────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="분석 대시보드", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #EEF0F3; }
    /* 뉴모피즘 지표 카드 - 홈 화면과 동일한 톤으로 통일 */
    .metric-card {
        background: #EEF0F3;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        box-shadow:
            6px 6px 13px rgba(163, 177, 198, 0.65),
            -6px -6px 13px rgba(255, 255, 255, 0.95);
        text-align: center;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A5F;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #6B7280;
        margin-top: 0.2rem;
    }
    .history-row {
        background: #EEF0F3;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin: 0.4rem 0;
        box-shadow:
            4px 4px 8px rgba(163, 177, 198, 0.55),
            -4px -4px 8px rgba(255, 255, 255, 0.9);
        font-size: 0.9rem;
    }
    /* 차트를 담는 카드 - 그림자 대비를 살짝 올려 카드 경계가 자연스럽게 드러나게 */
    div[data-testid="stPlotlyChart"] {
        background: #F8F9FB;
        border-radius: 16px;
        padding: 0.5rem;
        box-shadow:
            5px 5px 12px rgba(163, 177, 198, 0.45),
            -5px -5px 12px rgba(255, 255, 255, 0.85);
    }
</style>
""", unsafe_allow_html=True)

# 뉴모피즘 톤(회색/티얼/라벤더 계열)에 맞춘 차분한 색상 팔레트 - 기본 Plotly 원색 대신 사용
NEU_PALETTE = ["#5EC9B0", "#A78BFA", "#93A8C7", "#D4A5A5", "#B8C9A3",
               "#C9A9DD", "#8FBFA8", "#A8B8D8", "#D9B48F", "#9FB4C7"]

# ── 샘플 데이터 생성 함수 ─────────────────────
# Azure 연결 전, 또는 대화 이력이 없을 때 차트를 보여주기 위한 더미 데이터예요
def make_sample_data():
    """데모용 샘플 데이터를 만들어요"""
    distortions = ["이분법적 사고","과잉일반화","심리적 여과","긍정 격하","성급한 결론",
                   "과장/축소","감정적 추론","당위적 진술","잘못된 명명","개인화"]
    rows = []
    base = datetime.now() - timedelta(days=14)
    for i in range(30):
        rows.append({
            "timestamp": (base + timedelta(hours=i*10)).strftime("%Y-%m-%d %H:%M"),
            "user_text": f"샘플 발화 {i+1}",
            "distortion": random.choice(distortions),
            "confidence": round(random.uniform(0.6, 0.98), 2),
            "route": random.choice(["STS","RAG"]),
        })
    return rows

# ── 데이터 준비 ───────────────────────────────
# 채팅 페이지에서 쌓인 실제 이력을 가져와요
history = st.session_state.get("distortion_history", [])

# 이력이 없으면 샘플 데이터 사용
using_sample = len(history) == 0
if using_sample:
    history = make_sample_data()
    st.info("💡 아직 대화 이력이 없어요. 샘플 데이터로 대시보드를 미리 보여드려요. **💬 채팅** 메뉴에서 대화하면 실제 데이터로 바뀝니다.")

# pandas DataFrame으로 변환 (표, 차트 만들 때 편해요)
df = pd.DataFrame(history)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date  # 날짜만 추출

# ── 페이지 타이틀 ─────────────────────────────
st.title("📊 인지왜곡 분석 대시보드")
st.caption(f"{'샘플 데이터' if using_sample else '실제 대화 이력'} 기준 · 총 {len(df)}개 발화 분석")

st.divider()

# ── 요약 지표 (상단 숫자 카드) ───────────────
col1, col2, col3, col4 = st.columns(4)

# 가장 많이 나온 왜곡 유형
top_distortion = df["distortion"].value_counts().index[0]
top_count = df["distortion"].value_counts().iloc[0]

# 평균 신뢰도
avg_confidence = df["confidence"].mean()

# RAG 사용 비율
rag_ratio = (df["route"] == "RAG").mean()

# 분석 기간
date_range = (df["timestamp"].max() - df["timestamp"].min()).days

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="value">{len(df)}</div>
        <div class="label">총 분석 발화 수</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="value" style="font-size:1.3rem">{top_distortion}</div>
        <div class="label">최다 감지 왜곡 ({top_count}회)</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="value">{avg_confidence:.0%}</div>
        <div class="label">평균 분류 신뢰도</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="value">{rag_ratio:.0%}</div>
        <div class="label">RAG 라우팅 비율</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── 차트 영역 ─────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🥧 인지왜곡 유형 분포")
    st.caption("전체 대화에서 각 왜곡 유형이 얼마나 감지됐는지")

    # 파이 차트
    dist_counts = df["distortion"].value_counts().reset_index()
    dist_counts.columns = ["distortion", "count"]

    fig_pie = px.pie(
        dist_counts,
        values="count",
        names="distortion",
        color_discrete_sequence=NEU_PALETTE,
        hole=0.4,  # 도넛 모양
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=1.05),
        margin=dict(t=20, b=20, l=20, r=20),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("📊 왜곡 유형별 빈도")
    st.caption("막대 차트로 한눈에 비교")

    fig_bar = px.bar(
        dist_counts.sort_values("count", ascending=True),
        x="count",
        y="distortion",
        orientation="h",  # 가로 막대
        color="count",
        color_continuous_scale=["#D9E8E3", "#5EC9B0", "#2F8C77"],
        labels={"count": "감지 횟수", "distortion": "왜곡 유형"},
    )
    fig_bar.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=20, l=20, r=20),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
    )
    fig_bar.update_xaxes(gridcolor="#DDE1E6", zerolinecolor="#DDE1E6")
    fig_bar.update_yaxes(showgrid=False)
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ── 변화 추이 ─────────────────────────────────
st.subheader("📈 날짜별 변화 추이")
st.caption("시간에 따라 어떤 왜곡이 많이 나타났는지 추적해요")

# 날짜 × 왜곡유형 별 카운트
daily = df.groupby(["date", "distortion"]).size().reset_index(name="count")

fig_line = px.line(
    daily,
    x="date",
    y="count",
    color="distortion",
    markers=True,
    labels={"date": "날짜", "count": "감지 횟수", "distortion": "왜곡 유형"},
    color_discrete_sequence=NEU_PALETTE,
)
fig_line.update_layout(
    margin=dict(t=20, b=20, l=20, r=20),
    height=350,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#6B7280", size=12),
)
fig_line.update_xaxes(gridcolor="#DDE1E6", zerolinecolor="#DDE1E6")
fig_line.update_yaxes(gridcolor="#DDE1E6", zerolinecolor="#DDE1E6")
st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ── 신뢰도 분포 ───────────────────────────────
col_conf, col_route = st.columns(2)

with col_conf:
    st.subheader("🎯 분류 신뢰도 분포")
    st.caption("분류기가 얼마나 확신을 갖고 분류했는지")

    fig_hist = px.histogram(
        df, x="confidence",
        nbins=20,
        color_discrete_sequence=["#5EC9B0"],
        labels={"confidence": "신뢰도", "count": "빈도"},
    )
    fig_hist.update_layout(
        margin=dict(t=20,b=20,l=20,r=20), height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
    )
    fig_hist.update_xaxes(gridcolor="#DDE1E6", zerolinecolor="#DDE1E6")
    fig_hist.update_yaxes(gridcolor="#DDE1E6", zerolinecolor="#DDE1E6")
    st.plotly_chart(fig_hist, use_container_width=True)

with col_route:
    st.subheader("🔀 LLM 라우팅 분포")
    st.caption("STS(짧은 응답) vs RAG(문서 검색) 비율")

    route_counts = df["route"].value_counts().reset_index()
    route_counts.columns = ["route","count"]

    fig_route = px.pie(
        route_counts, values="count", names="route",
        color_discrete_map={"STS": "#A78BFA", "RAG": "#5EC9B0"},
        hole=0.5,
    )
    fig_route.update_layout(
        margin=dict(t=20,b=20,l=20,r=20), height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
    )
    st.plotly_chart(fig_route, use_container_width=True)

st.divider()

# ── 대화 이력 테이블 ──────────────────────────
st.subheader("📋 대화 이력 조회")
st.caption("전체 분석 이력을 표로 확인하고 필터링할 수 있어요")

# 필터
all_types = ["전체"] + sorted(df["distortion"].unique().tolist())
selected_type = st.selectbox("왜곡 유형 필터", all_types)

if selected_type == "전체":
    filtered_df = df
else:
    filtered_df = df[df["distortion"] == selected_type]

# 표시용 컬럼 정리
display_df = filtered_df[["timestamp", "distortion", "confidence", "route", "user_text"]].copy()
display_df.columns = ["시간", "왜곡 유형", "신뢰도", "라우팅", "발화 내용"]
display_df["신뢰도"] = display_df["신뢰도"].apply(lambda x: f"{x:.0%}")
display_df = display_df.sort_values("시간", ascending=False)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=300,
)

# CSV 다운로드 버튼
csv = display_df.to_csv(index=False).encode("utf-8-sig")  # 한글 깨짐 방지
st.download_button(
    label="⬇️ CSV로 다운로드",
    data=csv,
    file_name=f"cbt_history_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)