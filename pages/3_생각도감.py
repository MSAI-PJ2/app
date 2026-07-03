import streamlit as st

from ui_theme import PALETTE as P
from ui_theme import apply_theme, render_sidebar, render_topbar

st.set_page_config(page_title="생각도감 · 마음숲", page_icon="📖", layout="wide")
apply_theme()
render_sidebar(active="types")
render_topbar()

# types.tsx 의 types[] 그대로 이식 (No./이름/설명/이모지/톤)
TYPES = [
    (1,  "이분법적 사고", "흑백논리. \"완벽하지 않으면 실패야\"",        "⚖️", "chip-coral"),
    (2,  "과잉일반화",   "한 번의 실패로 \"항상 그렇다\"고 결론",       "🔁", "chip-lilac"),
    (3,  "심리적 여과",  "부정적인 것만 걸러내서 봄",                 "🌧️", "chip-sky"),
    (4,  "긍정 격하",    "좋은 일을 \"별거 아니다\"라고 무시",         "🙈", "chip-sunny"),
    (5,  "성급한 결론",  "근거 없이 최악을 가정",                    "💭", "chip-leaf"),
    (6,  "과장 · 축소",  "단점은 크게, 장점은 작게",                  "🔍", "chip-coral"),
    (7,  "감정적 추론",  "\"이렇게 느끼니까 사실이야\"",              "💧", "chip-sky"),
    (8,  "당위적 진술",  "\"~해야만 해\"로 스스로를 압박",            "📏", "chip-lilac"),
    (9,  "잘못된 명명",  "\"나는 실패자야\" 식의 극단적 낙인",         "🏷️", "chip-sunny"),
    (10, "개인화",      "내 잘못이 아닌 것도 내 탓으로",              "🎯", "chip-leaf"),
]

st.markdown(f"""
<span class="ac-chip chip-sunny">📖 도감</span>
<h1 style="margin:.4rem 0 .1rem;font-size:1.9rem;">생각도감 · 10가지 인지왜곡</h1>
<p style="margin:0 0 1.4rem;font-size:.87rem;color:{P['muted_fg']};">
마음숲에 자주 놀러오는 생각 친구들이에요. 하나씩 만나볼까요?</p>
""", unsafe_allow_html=True)

# 3열 그리드 (types.tsx grid sm:2 lg:3)
cols = st.columns(3, gap="medium")
for i, (n, name, desc, emoji, tone) in enumerate(TYPES):
    with cols[i % 3]:
        st.markdown(f"""
<div class="ac-card" style="padding:1.2rem 1.3rem;margin-bottom:1rem;">
  <div style="display:flex;align-items:flex-start;gap:14px;">
    <div class="ac-chip {tone}" style="width:52px;height:52px;justify-content:center;
         border-radius:18px;font-size:24px;padding:0;flex-shrink:0;">{emoji}</div>
    <div style="min-width:0;">
      <div style="font-size:.7rem;font-weight:800;color:{P['muted_fg']};">No. {n:02d}</div>
      <div class="font-display" style="font-size:1.05rem;">{name}</div>
      <div style="margin-top:2px;font-size:.83rem;color:{P['muted_fg']};">{desc}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
