import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import explain_turn, get_session
from demo_data import DEMO_USER_ID, demo_stats_rows
from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar

st.set_page_config(page_title="마음 일기 · 마음숲", page_icon="📊", layout="wide")
apply_theme()
render_sidebar(active="analytics")
render_topbar()

CHART = P["chart"]
GRID_COLOR = P["border"]
FONT = dict(family="Nunito, sans-serif", color=P["muted_fg"], size=12)

# ── 기관 관리자 보기 (토글) — 켜면 데모 사용자의 세션 집계(픽스처)를 아래 메인 대시보드로 보여준다 ──
# (기존 목업 차트/설문은 실데이터화 요청에 따라 제거 — 관리자 뷰도 메인 흐름의 픽스처 집계를 그대로 쓴다.)
admin_view = st.toggle("🏥 기관 관리자로 보기 (환자)", key="admin_view_toggle")
if admin_view:
    st.markdown("""
<span class="ac-chip chip-sky">🏥 기관 관리자용</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">환자 기록 (세션 집계)</h1>
""", unsafe_allow_html=True)
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)


# ── 샘플 데이터 (백엔드 세션이 없을 때만 사용) ────────────────────
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

# [데모] 특정 데모 id 를 조회하거나 관리자 토글이면, 그 사용자의 세션들을 가로지른 집계 통계를
# 프론트 내장 픽스처(실라벨·합성날짜)로 보여준다 — "데모 id 로 대시보드 사용 시 UI 반영".
# 발화는 배포 분류기로 실제 라벨링했고 세션 볼륨·날짜만 합성 — 라이브 Cosmos 파이프라인은 아님.
is_demo = admin_view or session_id == DEMO_USER_ID
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
               f"기록 {len(df_all)}건(왜곡 라벨 단위). 기간 필터·분포는 실제로 동작합니다.")
elif using_sample:
    if session_id:
        st.info(f"💡 세션 `{session_id[:8]}…` 에 저장된 대화 기록을 찾지 못했어요. 샘플 데이터로 미리 보여드려요.")
    else:
        st.info("💡 아직 대화 이력이 없어요. 샘플 데이터로 미리 보여드려요. **💬 대화하기**에서 대화하면 실제 데이터로 바뀝니다.")
else:
    st.caption(f"세션 `{session_id[:8]}…` 의 실제 대화 기록 {len(df_all)}건을 표시하고 있어요.")

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
      <div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
        {f'<span class="ac-chip chip-lilac">📁 {getattr(r, "session_name", "")}</span>' if getattr(r, "session_name", "") else ''}
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
