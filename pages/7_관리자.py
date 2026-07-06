"""운영자(개발자) 전용 관리자 페이지 — 사이드바 NAV에는 노출하지 않음.

접근: 주소창에 직접  /관리자  경로 입력.
인증: 환경변수 ADMIN_PASSWORD (미설정 시 기본값 maeum2026).
실서비스 전환 시 Entra ID(OIDC) + RBAC로 교체 예정.
개인 대화 내용은 어디에도 저장/표시하지 않음 — 익명 집계만 다룬다.

지도: assets/skorea_provinces.json (광역 17개 시·도 GeoJSON, 로컬 파일)
      파일이 없으면 자동으로 막대그래프로 대체(fallback).
"""
import hashlib
import json
import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_topbar

st.set_page_config(page_title="관리자 · 마음갈피", page_icon="🛠️", layout="wide")
apply_theme()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "maeum2026")

# ── 인증 게이트 ────────────────────────────────────────────────
if not st.session_state.get("is_admin"):
    st.markdown("""
<span class="ac-chip chip-coral">🛠️ 운영자 전용</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">관리자 콘솔</h1>
<p style="margin-bottom:1rem;">승인된 운영자만 접근할 수 있어요.</p>
""", unsafe_allow_html=True)
    with st.container(border=True):
        pw = st.text_input("관리자 비밀번호", type="password")
        if st.button("🔑 인증하기", type="primary"):
            if pw.strip() == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# ── 공통 스타일/데이터 ─────────────────────────────────────────
render_topbar(show_new_chat=False)
st.markdown("""
<span class="ac-chip chip-coral">🛠️ 운영자 전용</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">서비스 운영 현황</h1>
<p style="margin-bottom:.4rem;">익명 집계 데이터만 표시 — 개인 대화 내용은 저장·표시하지 않습니다.</p>
""", unsafe_allow_html=True)

if st.button("🚪 관리자 로그아웃"):
    st.session_state.pop("is_admin", None)
    st.rerun()

FONT = dict(family="Nunito, sans-serif", color=P["muted_fg"], size=12)
LAYOUT = dict(margin=dict(t=10, b=10, l=10, r=10),
              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=FONT)
GRID = P["border"]

REGIONS = {  # GeoJSON의 name → 표시명, 사용자 수
    "서울특별시": ("서울", 412), "경기도": ("경기", 357), "부산광역시": ("부산", 118),
    "인천광역시": ("인천", 96), "대구광역시": ("대구", 74), "경상남도": ("경남", 67),
    "대전광역시": ("대전", 61), "광주광역시": ("광주", 48), "경상북도": ("경북", 44),
    "충청남도": ("충남", 42), "강원도": ("강원", 39), "전라북도": ("전북", 35),
    "울산광역시": ("울산", 33), "충청북도": ("충북", 30), "전라남도": ("전남", 28),
    "세종특별자치시": ("세종", 21), "제주특별자치도": ("제주", 19),
}
AGES = ["10대", "20대", "30대", "40대", "50대", "60대+"]
GENDERS = ["여성", "남성"]
LABELS = ["파국화", "흑백논리", "과잉일반화", "당위진술", "개인화(자기비난)",
          "감정적 추론", "정신적 여과", "긍정 격하", "성급한 결론", "낙인찍기"]


@st.cache_data
def load_distribution() -> pd.DataFrame:
    """지역×연령×성별×10라벨 집계 분포 — 해시 기반 결정적 생성(항상 동일한 값)."""
    rows = []
    for gname, (short, users) in REGIONS.items():
        for age in AGES:
            for gender in GENDERS:
                for label in LABELS:
                    seed = int(hashlib.md5(f"{short}{age}{gender}{label}".encode()).hexdigest()[:6], 16)
                    base = 5 + seed % 40
                    weight = {"10대": .7, "20대": 1.5, "30대": 1.2, "40대": .8, "50대": .5, "60대+": .3}[age]
                    rows.append(dict(geo=gname, 지역=short, 연령대=age, 성별=gender,
                                     라벨=label, 건수=int(base * weight * users / 100) + 1))
    return pd.DataFrame(rows)


DIST = load_distribution()

# ── KPI ───────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("오늘 활성 사용자", "1,284", "+12.4%")
c2.metric("오늘 대화 세션", "3,907", "+8.1%")
c3.metric("응답 지연 p95", "2.4s", "-0.3s")
c4.metric("위기 감지 (24h)", "17건", "안내 완료 15건", delta_color="off")
st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

# ── ① 대한민국 지도 + 드릴다운 ─────────────────────────────────
st.markdown('<div class="font-display" style="font-size:1.15rem;margin-bottom:6px;">🗺️ 지역별 인지왜곡 분포 지도</div>',
            unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns([1.2, 1, 1])
with fc1:
    metric_label = st.selectbox("지도 색상 기준", ["전체 사용자 수"] + LABELS)
with fc2:
    f_age = st.selectbox("연령대", ["전체"] + AGES)
with fc3:
    f_gender = st.selectbox("성별", ["전체"] + GENDERS)

sub = DIST.copy()
if f_age != "전체":
    sub = sub[sub["연령대"] == f_age]
if f_gender != "전체":
    sub = sub[sub["성별"] == f_gender]
if metric_label == "전체 사용자 수":
    geo_val = sub.groupby("geo")["건수"].sum().reset_index(name="값")
else:
    geo_val = sub[sub["라벨"] == metric_label].groupby("geo")["건수"].sum().reset_index(name="값")
geo_val["지역"] = geo_val["geo"].map(lambda g: REGIONS[g][0])

GEOJSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "skorea_provinces.json")
map_col, drill_col = st.columns([1.1, 1])

with map_col:
    if os.path.exists(GEOJSON_PATH):
        with open(GEOJSON_PATH, encoding="utf-8") as f:
            geojson = json.load(f)
        fig = go.Figure(go.Choropleth(
            geojson=geojson, featureidkey="properties.name",
            locations=geo_val["geo"], z=geo_val["값"],
            colorscale=[[0, P["leaf"]], [1, P["fg_deep"]]],
            marker_line_color=P["card"], marker_line_width=1,
            colorbar=dict(thickness=10, len=.7, tickfont=FONT),
            customdata=geo_val[["지역"]],
            hovertemplate="%{customdata[0]}: %{z}건<extra></extra>",
        ))
        fig.update_geos(fitbounds="locations", visible=False,
                        bgcolor="rgba(0,0,0,0)")
        fig.update_layout(**LAYOUT, height=460)
        st.plotly_chart(fig, use_container_width=True)
    else:
        bar = geo_val.sort_values("값")
        fig = go.Figure(go.Bar(x=bar["값"], y=bar["지역"], orientation="h",
                               marker_color=P["primary"]))
        fig.update_layout(**LAYOUT, height=460)
        fig.update_xaxes(gridcolor=GRID, griddash="dash")
        st.plotly_chart(fig, use_container_width=True)

# ── 드릴다운: 선택 지역의 연령대×성별 인지왜곡 분포 ─────────────
with drill_col:
    shorts = [v[0] for v in REGIONS.values()]
    sel_region = st.selectbox("지역 상세 보기", shorts, index=0)
    rsub = DIST[DIST["지역"] == sel_region]
    if f_age != "전체":
        rsub = rsub[rsub["연령대"] == f_age]
    if f_gender != "전체":
        rsub = rsub[rsub["성별"] == f_gender]

    top = (rsub.groupby(["라벨", "성별"])["건수"].sum().reset_index())
    order = top.groupby("라벨")["건수"].sum().sort_values().index.tolist()
    fig = go.Figure()
    for i, g in enumerate(GENDERS):
        gsub = top[top["성별"] == g].set_index("라벨").reindex(order).reset_index()
        fig.add_bar(x=gsub["건수"], y=gsub["라벨"], orientation="h", name=g,
                    marker_color=[P["coral"], P["sky"]][i])
    fig.update_layout(**LAYOUT, height=400, barmode="stack",
                      legend=dict(orientation="h", y=1.08, font=FONT))
    fig.update_xaxes(gridcolor=GRID, griddash="dash")
    st.plotly_chart(fig, use_container_width=True)

    age_sub = DIST[DIST["지역"] == sel_region].groupby("연령대")["건수"].sum().reindex(AGES).reset_index()
    fig = go.Figure(go.Bar(x=age_sub["연령대"], y=age_sub["건수"],
                           marker_color=P["chart"][: len(AGES)]))
    fig.update_layout(**LAYOUT, height=170)
    fig.update_yaxes(gridcolor=GRID, griddash="dash")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{sel_region} · 연령대별 표본 수")

# ── ② 시간대별 대화량 ─────────────────────────────────────────
st.markdown('<div class="font-display" style="font-size:1.1rem;margin:8px 0 6px;">⏰ 시간대별 대화량 (오늘)</div>',
            unsafe_allow_html=True)
hour = pd.DataFrame({"시": [0, 3, 6, 9, 12, 15, 18, 21, 23],
                     "대화": [95, 142, 48, 110, 187, 231, 286, 412, 308]})
fig = go.Figure(go.Scatter(x=hour["시"], y=hour["대화"], mode="lines+markers",
                           line=dict(color=P["leaf_deep"], width=3), marker=dict(size=7)))
fig.update_layout(**LAYOUT, height=200)
fig.update_yaxes(gridcolor=GRID, griddash="dash")
st.plotly_chart(fig, use_container_width=True)

# ── ③ 위기 감지 로그 (익명) ────────────────────────────────────
st.markdown('<div class="font-display" style="font-size:1.1rem;margin:8px 0 6px;">🛡️ 위기 감지 로그 (24h · 익명)</div>',
            unsafe_allow_html=True)
crisis = pd.DataFrame([
    ["14:32", "키워드 감지", "서울 노원구", "서울시자살예방센터", "안내 완료"],
    ["13:58", "Content Safety (self-harm 6)", "경기 수원시", "수원시정신건강복지센터", "안내 완료"],
    ["12:41", "Content Safety (self-harm 4)", "부산 해운대구", "—", "검토 필요"],
    ["11:07", "키워드 감지", "대전 유성구", "1393 안내", "안내 완료"],
    ["09:23", "Content Safety (self-harm 7)", "서울 관악구", "관악구정신건강복지센터", "고위험"],
], columns=["시각", "감지 경로", "지역(시군구)", "안내된 기관", "상태"])
st.dataframe(crisis, use_container_width=True, hide_index=True)

st.caption(f"프롬프트 내용 로깅 비활성화 정책 유지 · 갱신 {datetime.now():%H:%M}")
