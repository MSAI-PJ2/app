"""백엔드(gateway) API 호출 전담 — Streamlit 페이지들은 이 함수만 쓴다."""
import hashlib
import json
import os
from typing import Generator

import base64

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
# 게이트웨이가 API_KEY_REQUIRED=true 로 켜진 경우에만 필요 (로컬 기본값은 꺼짐).
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")


def virtual_user_id(email: str) -> str:
    """이메일 → 가상 ID(x-user-id) 로 변환.

    게이트웨이(app/api/v1.py [구획 2])의 가상 ID 형식은 영문/숫자/일부 기호 최대 64자
    (정규식 ^[A-Za-z0-9_.-]{1,64}$) — '@'가 포함된 이메일을 그대로 못 쓰므로 해시로
    변환한다. 같은 이메일이면 항상 같은 ID가 나와야 재로그인 시 같은 프로필을 찾는다
    (email 자체를 서버에 보내지 않아도 되는 부수 효과도 있음).
    """
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:32]


def _headers() -> dict:
    h = {"x-api-key": GATEWAY_API_KEY} if GATEWAY_API_KEY else {}
    # 로그인 페이지(0_로그인.py)가 st.session_state.user_id 에 virtual_user_id() 결과를
    # 저장해둔다 — 있으면 모든 호출(프로필은 물론 respond 도)에 실어 보내서, 위기 시
    # 프로필 지역으로 안내하는 백엔드 로직(profile.py + policy.resolve_region)이 동작한다.
    uid = st.session_state.get("user_id") if hasattr(st, "session_state") else None
    if uid:
        h["x-user-id"] = uid
    return h


# ── 프로필 / 설문 ─────────────────────────────────────────────────

def get_profile() -> dict | None:
    resp = requests.get(f"{BACKEND_URL}/v1/profile", headers=_headers(), timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def create_profile() -> dict:
    resp = requests.post(f"{BACKEND_URL}/v1/profile", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def submit_survey(payload: dict) -> dict:
    resp = requests.post(f"{BACKEND_URL}/v1/profile/survey", headers=_headers(), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()


# ── 상담 응답(SSE) ────────────────────────────────────────────────

def respond_stream(session_id: str, text: str) -> Generator[dict, None, None]:
    """POST /v1/respond 를 호출해 SSE 이벤트를 하나씩 dict 로 yield 한다.

    이벤트 type: meta | chunks | token | crisis | tts | input_required | done
    (API_CONTRACT.md §7~9 참고). 세션이 없으면 백엔드가 session_id 로 새로 만든다.
    """
    resp = requests.post(
        f"{BACKEND_URL}/v1/respond",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"session_id": session_id, "text": text},
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        yield json.loads(raw[6:])


# ── 세션(대화 기록) 조회 ─────────────────────────────────────────

def get_session(session_id: str) -> dict | None:
    """GET /v1/sessions/{session_id} — 저장된 턴 전체를 조회한다. 없으면 None."""
    resp = requests.get(f"{BACKEND_URL}/v1/sessions/{session_id}", headers=_headers(), timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# ── SHAP 설명("연산 과정 보기") ──────────────────────────────────

def list_sessions() -> list[dict]:
    """GET /v1/sessions — 로그인한 사용자(x-user-id)의 세션 목록(요약)을 최신순으로 가져온다.
    가상 ID 도입 이전에 만들어진 옛날 세션은 여기 안 잡힐 수 있음 — 그런 세션은
    5_이전대화기록.py 의 수동 ID 입력으로 여전히 조회 가능."""
    resp = requests.get(f"{BACKEND_URL}/v1/sessions", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def explain_turn(session_id: str, turn_index: int, label: str | None = None) -> dict:
    """GET /v1/sessions/{session_id}/turns/{turn_index}/explain — 캐싱 없이 매번 새로 계산됨.
    SHAP 계산이라 문장에 따라 수 초~수십 초 걸릴 수 있다 (호출부에서 spinner 권장)."""
    params = {"label": label} if label else {}
    resp = requests.get(
        f"{BACKEND_URL}/v1/sessions/{session_id}/turns/{turn_index}/explain",
        headers=_headers(), params=params, timeout=90,
    )
    resp.raise_for_status()
    return resp.json()

def respond_stream_audio(session_id: str, audio_bytes: bytes, mime_type: str = "audio/wav",
                         language: str = "ko-KR"):
    body = {
        "session_id": session_id,
        "input_type": "audio",
        "audio": {"kind": "base64", "data": base64.b64encode(audio_bytes).decode(),
                  "mime_type": mime_type, "language": language},
        "stt": {"provider": "azure", "language": language},
    }
    resp = requests.post(f"{BACKEND_URL}/v1/respond", headers={**_headers(), "Content-Type": "application/json"},
                         json=body, stream=True, timeout=120)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        yield json.loads(raw[6:])


def respond_stream_image(session_id: str, image_bytes: bytes, mime_type: str = "image/png",
                         ocr_profile: str = "generic", sender_names: list[str] | None = None):
    body = {
        "session_id": session_id,
        "input_type": "image",
        "image": {"kind": "base64", "data": base64.b64encode(image_bytes).decode(), "mime_type": mime_type},
        "ocr": {"profile": ocr_profile, "sender_names": sender_names or []},
    }
    resp = requests.post(f"{BACKEND_URL}/v1/respond", headers={**_headers(), "Content-Type": "application/json"},
                         json=body, stream=True, timeout=120)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        yield json.loads(raw[6:])
