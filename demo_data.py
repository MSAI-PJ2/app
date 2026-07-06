# -*- coding: utf-8 -*-
"""[데모 데이터] 대시보드 시연용 가상 통계 — 발화는 배포 분류기(/v1/classify)로
실제 라벨링(라벨 진짜), 세션 볼륨·날짜만 합성. 데모 id 로 대시보드를 열면 df_all 로 주입돼
기간필터·분포·추이가 실집계처럼 동작. (라이브 Cosmos 파이프라인 아님 — 시연 픽스처)"""

import hashlib

DEMO_USER_ID = "demo-마음숲"
DEMO_SESSION_COUNT = 20

# 데모 id 트리거(로그인): 이 이메일로 로그인하면 0_로그인.py 가 st.session_state.user_id 를
# virtual_user_id(email)=sha256[:32] 로 저장한다. 대시보드가 그 uid 를 감지해 데모 통계를
# 자동 표시한다. (데모 세션 레코드 시더와 동일 이메일 — 계정 일관성)
DEMO_LOGIN_EMAIL = "demo@maeumsup.kr"
DEMO_LOGIN_UID = hashlib.sha256(DEMO_LOGIN_EMAIL.strip().lower().encode("utf-8")).hexdigest()[:32]

# load_session_turns() 반환과 같은 행 형태 + session_name. distortion=selected 라벨 단위(동시 왜곡=여러 행).
DEMO_ROWS = [
    {"timestamp": "2026-07-06 11:20:49", "user_text": "내일 발표만 생각하면 분명히 크게 망칠 것 같고 사람들이 다 저를 비웃을 게 뻔해요", "distortion": "성급한 판단", "confidence": 0.9998, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-00-발표 불안", "session_name": "발표 불안"},
    {"timestamp": "2026-07-05 11:20:49", "user_text": "상담 이후로 마음이 한결 편해진 것 같아 다시 힘을 내볼게요", "distortion": "불충분", "confidence": 0.8998, "route": "STS", "turn_index": 0, "context_merged": False, "session_id": "demo-01-회복의 하루", "session_name": "회복의 하루"},
    {"timestamp": "2026-07-05 11:20:49", "user_text": "이번 프로젝트가 실패해서 제 커리어 전체가 완전히 끝나버린 것 같아요", "distortion": "과잉 일반화", "confidence": 0.9383, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-02-프로젝트 실패", "session_name": "프로젝트 실패"},
    {"timestamp": "2026-07-05 11:20:49", "user_text": "이번 프로젝트가 실패해서 제 커리어 전체가 완전히 끝나버린 것 같아요", "distortion": "확대와 축소", "confidence": 0.6718, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-02-프로젝트 실패", "session_name": "프로젝트 실패"},
    {"timestamp": "2026-07-05 11:20:49", "user_text": "이번 프로젝트가 실패해서 제 커리어 전체가 완전히 끝나버린 것 같아요", "distortion": "흑백 사고", "confidence": 0.9701, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-02-프로젝트 실패", "session_name": "프로젝트 실패"},
    {"timestamp": "2026-07-04 11:20:49", "user_text": "회의에서 나온 문제들이 전부 결국 저 때문에 생긴 일이라는 생각을 지울 수가 없어요", "distortion": "개인화", "confidence": 0.9979, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-03-자기비난", "session_name": "자기비난"},
    {"timestamp": "2026-07-04 11:20:49", "user_text": "회의에서 나온 문제들이 전부 결국 저 때문에 생긴 일이라는 생각을 지울 수가 없어요", "distortion": "성급한 판단", "confidence": 0.6078, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-03-자기비난", "session_name": "자기비난"},
    {"timestamp": "2026-07-04 11:20:49", "user_text": "오늘 산책을 다녀왔는데 날씨가 맑아서 기분이 참 좋았어요", "distortion": "불충분", "confidence": 0.9968, "route": "STS", "turn_index": 0, "context_merged": False, "session_id": "demo-04-산책", "session_name": "산책"},
    {"timestamp": "2026-07-03 11:20:49", "user_text": "저는 뭘 해도 항상 실패하고 되는 일이 하나도 없어요", "distortion": "과잉 일반화", "confidence": 0.9495, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-05-반복되는 실패", "session_name": "반복되는 실패"},
    {"timestamp": "2026-07-03 11:20:49", "user_text": "저는 뭘 해도 항상 실패하고 되는 일이 하나도 없어요", "distortion": "부정적 편향", "confidence": 0.7762, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-05-반복되는 실패", "session_name": "반복되는 실패"},
    {"timestamp": "2026-07-02 11:20:49", "user_text": "친구가 오늘 제 인사를 안 받아준 걸 보니 저를 싫어하는 게 분명해요", "distortion": "성급한 판단", "confidence": 0.9991, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-06-관계 불안", "session_name": "관계 불안"},
    {"timestamp": "2026-07-01 11:20:49", "user_text": "완벽하게 해내지 못할 거라면 아예 시작도 안 하는 게 낫다고 생각해요", "distortion": "흑백 사고", "confidence": 0.9928, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-07-완벽주의", "session_name": "완벽주의"},
    {"timestamp": "2026-06-30 11:20:49", "user_text": "저는 원래 게으르고 한심한 실패자예요", "distortion": "낙인찍기", "confidence": 0.9718, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-08-자기낙인", "session_name": "자기낙인"},
    {"timestamp": "2026-06-30 11:20:49", "user_text": "그냥 좀 그래요 잘 모르겠어요", "distortion": "불충분", "confidence": 0.9962, "route": "STS", "turn_index": 0, "context_merged": False, "session_id": "demo-09-모호한 마음", "session_name": "모호한 마음"},
    {"timestamp": "2026-06-29 11:20:49", "user_text": "친구랑 맛있는 저녁을 먹으며 즐겁게 이야기했어요", "distortion": "불충분", "confidence": 0.9949, "route": "STS", "turn_index": 0, "context_merged": False, "session_id": "demo-10-친구와 식사", "session_name": "친구와 식사"},
    {"timestamp": "2026-06-28 11:20:49", "user_text": "이렇게 불안한 걸 보면 분명히 나쁜 일이 생길 게 확실해요", "distortion": "감정적 추론", "confidence": 0.9844, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-11-불안", "session_name": "불안"},
    {"timestamp": "2026-06-28 11:20:49", "user_text": "이렇게 불안한 걸 보면 분명히 나쁜 일이 생길 게 확실해요", "distortion": "성급한 판단", "confidence": 0.9855, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-11-불안", "session_name": "불안"},
    {"timestamp": "2026-06-26 11:20:49", "user_text": "저는 언제나 완벽해야만 하고 실수는 절대로 하면 안 돼요", "distortion": "'해야 한다' 진술", "confidence": 0.3747, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-12-완벽 강박", "session_name": "완벽 강박"},
    {"timestamp": "2026-06-24 11:20:49", "user_text": "사람들이 칭찬해줬지만 그건 그냥 운이 좋았을 뿐 제 실력은 아니에요", "distortion": "긍정 축소화", "confidence": 0.9994, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-13-칭찬 앞에서", "session_name": "칭찬 앞에서"},
    {"timestamp": "2026-06-21 11:20:49", "user_text": "오늘 좋은 일도 많았는데 자꾸 나빴던 한 가지만 계속 떠올라요", "distortion": "부정적 편향", "confidence": 0.963, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-14-나쁜 것만", "session_name": "나쁜 것만"},
    {"timestamp": "2026-06-18 11:20:49", "user_text": "작은 실수 하나 했을 뿐인데 모든 게 다 무너진 기분이에요", "distortion": "확대와 축소", "confidence": 0.9965, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-15-작은 실수", "session_name": "작은 실수"},
    {"timestamp": "2026-06-18 11:20:49", "user_text": "작은 실수 하나 했을 뿐인데 모든 게 다 무너진 기분이에요", "distortion": "흑백 사고", "confidence": 0.7997, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-15-작은 실수", "session_name": "작은 실수"},
    {"timestamp": "2026-06-16 11:20:49", "user_text": "이번에도 떨어졌어요 저는 어디에도 붙지 못할 사람이에요", "distortion": "불충분", "confidence": 0.6051, "route": "STS", "turn_index": 0, "context_merged": False, "session_id": "demo-16-취업 좌절", "session_name": "취업 좌절"},
    {"timestamp": "2026-06-14 11:20:49", "user_text": "친구들이 약속을 취소한 건 분명 제가 뭔가 잘못했기 때문이에요", "distortion": "개인화", "confidence": 0.9365, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-17-약속 취소", "session_name": "약속 취소"},
    {"timestamp": "2026-06-14 11:20:49", "user_text": "친구들이 약속을 취소한 건 분명 제가 뭔가 잘못했기 때문이에요", "distortion": "성급한 판단", "confidence": 0.5949, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-17-약속 취소", "session_name": "약속 취소"},
    {"timestamp": "2026-06-06 11:20:49", "user_text": "한 번 다이어트를 어겼으니 오늘 하루는 완전히 망친 거예요", "distortion": "과잉 일반화", "confidence": 0.5664, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-18-다이어트", "session_name": "다이어트"},
    {"timestamp": "2026-06-06 11:20:49", "user_text": "한 번 다이어트를 어겼으니 오늘 하루는 완전히 망친 거예요", "distortion": "흑백 사고", "confidence": 0.9941, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-18-다이어트", "session_name": "다이어트"},
    {"timestamp": "2026-05-29 11:20:49", "user_text": "답장이 늦는 걸 보니 저한테 완전히 관심이 없는 거예요", "distortion": "성급한 판단", "confidence": 0.9984, "route": "RAG", "turn_index": 0, "context_merged": False, "session_id": "demo-19-소개팅", "session_name": "소개팅"},
]

def demo_stats_rows():
    """데모 픽스처 행 리스트(복사본)."""
    return [dict(r) for r in DEMO_ROWS]
