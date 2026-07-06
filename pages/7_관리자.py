"""운영자(개발자) 전용 관리자 페이지 — 사이드바 NAV에는 노출하지 않음.

접근 방법: 브라우저 주소창에 직접  /관리자  경로로 접속.
인증: 환경변수 ADMIN_PASSWORD (미설정 시 기본값 maeum2026).
⚠️ 데모용 게이트. 실서비스는 Entra ID(OIDC) + RBAC로 교체 예정.
전 데이터 목업 — 개인 대화 내용은 어디에도 저장/표시하지 않음.
"""
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

# ── 대시보드 ──────────────────────────────────────────────────
render_topbar(show_new_chat=False)
st.markdown("""
<span class="ac-chip chip-coral">🛠️ 운영자 전용</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">서비스 운영 현황</h1>
<p style="margin-bottom:.4rem;">익명 집계 데이터만 표시 — 개인 대화 내용은 저장·표시하지 않습니다. (전체 목업)</p>
""", unsafe_allow_html=True)

if st.button("🚪 관리자 로그아웃"):
    st.session_state.pop("is_admin", None)
    st.rerun()

FONT = dict(family="Nunito, sans-serif", color=P["muted_fg"], size=12)
LAYOUT = dict(margin=dict(t=10, b=10, l=10, r=10),
              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=FONT)
GRID = P["border"]

# KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("오늘 활성 사용자", "1,284", "+12.4%")
c2.metric("오늘 대화 세션", "3,907", "+8.1%")
c3.metric("응답 지연 p95", "2.4s", "-0.3s")
c4.metric("위기 감지 (24h)", "17건", "안내 완료 15건", delta_color="off")

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
left, right = st.columns(2)

# 지역별 사용자 분포
with left:
    st.markdown('<div class="font-display" style="font-size:1.1rem;margin-bottom:6px;">🗺️ 지역별 사용자 분포 (7일)</div>',
                unsafe_allow_html=True)
    region = pd.DataFrame({
        "지역": ["서울", "경기", "부산", "인천", "대구", "경남", "대전", "광주",
               "충남", "경북", "강원", "전북", "울산", "충북", "전남", "세종", "제주"],
        "사용자": [412, 357, 118, 96, 74, 67, 61, 48, 42, 44, 39, 35, 33, 30, 28, 21, 19],
    }).sort_values("사용자")
    fig = go.Figure(go.Bar(x=region["사용자"], y=region["지역"], orientation="h",
                           marker_color=P["primary"]))
    fig.update_layout(**LAYOUT, height=420)
    fig.update_xaxes(gridcolor=GRID, griddash="dash")
    st.plotly_chart(fig, use_container_width=True)

# 연령대 분포
with right:
    st.markdown('<div class="font-display" style="font-size:1.1rem;margin-bottom:6px;">🎂 연령대 분포 (설문 응답 기준)</div>',
                unsafe_allow_html=True)
    age = pd.DataFrame({"연령대": ["10대", "20대", "30대", "40대", "50대", "60대+"],
                        "사용자": [142, 486, 331, 178, 89, 58]})
    fig = go.Figure(go.Bar(x=age["연령대"], y=age["사용자"],
                           marker_color=P["chart"][: len(age)]))
    fig.update_layout(**LAYOUT, height=190)
    fig.update_yaxes(gridcolor=GRID, griddash="dash")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="font-display" style="font-size:1.1rem;margin:6px 0;">⏰ 시간대별 대화량 (오늘)</div>',
                unsafe_allow_html=True)
    hour = pd.DataFrame({"시": [0, 3, 6, 9, 12, 15, 18, 21, 23],
                         "대화": [95, 142, 48, 110, 187, 231, 286, 412, 308]})
    fig = go.Figure(go.Scatter(x=hour["시"], y=hour["대화"], mode="lines+markers",
                               line=dict(color=P["leaf_deep"], width=3), marker=dict(size=7)))
    fig.update_layout(**LAYOUT, height=190)
    fig.update_yaxes(gridcolor=GRID, griddash="dash")
    st.plotly_chart(fig, use_container_width=True)

# 인지왜곡 라벨 분포
st.markdown('<div class="font-display" style="font-size:1.1rem;margin:8px 0 6px;">🧠 인지왜곡 라벨 상위 6개 (분류기 집계)</div>',
            unsafe_allow_html=True)
label = pd.DataFrame({"라벨": ["파국화", "흑백논리", "과잉일반화", "당위진술", "자기비난", "감정적추론"],
                      "건수": [612, 547, 489, 402, 377, 298]}).sort_values("건수")
fig = go.Figure(go.Bar(x=label["건수"], y=label["라벨"], orientation="h",
                       marker_color=P["chart"][: len(label)]))
fig.update_layout(**LAYOUT, height=240)
fig.update_xaxes(gridcolor=GRID, griddash="dash")
st.plotly_chart(fig, use_container_width=True)

# 위기 감지 로그 (익명)
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

st.caption(f"모든 수치는 시연용 목업입니다 · 프롬프트 내용 로깅 비활성화 정책 유지 · 갱신 {datetime.now():%H:%M}")
