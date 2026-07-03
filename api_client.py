"""백엔드(gateway) API 호출 전담 — Streamlit 페이지들은 이 함수만 쓴다."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# 지금은 인증 헤더 없이 호출 (백엔드 api_key 모드, current_user = anonymous 고정).

def get_profile() -> dict | None:
    resp = requests.get(f"{BACKEND_URL}/v1/profile", timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def create_profile() -> dict:
    resp = requests.post(f"{BACKEND_URL}/v1/profile", timeout=15)
    resp.raise_for_status()
    return resp.json()


def submit_survey(payload: dict) -> dict:
    resp = requests.post(f"{BACKEND_URL}/v1/profile/survey", json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()