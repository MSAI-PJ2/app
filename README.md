# 마음갈피 (Maeum-galpi) — Streamlit Frontend

A Korean-language CBT (Cognitive Behavioral Therapy) companion chatbot with a warm, village-themed UI. This repository contains the **Streamlit frontend** of the 마음갈피 service — a multipage web app that talks to a separate gateway backend for AI inference, crisis detection, and session storage.

> 마음갈피 helps users notice cognitive distortions in their thoughts through gentle, empathy-first conversations, and connects them to real crisis-support institutions when needed.

---

## Architecture Overview

This app is the **frontend / monitoring UI layer only**. All AI inference runs on the backend:

```
[Streamlit app (this repo)]
        │  REST + SSE
        ▼
[Gateway Backend  /v1/*]
   ├── Azure AI Content Safety   → crisis / safety gate
   ├── Cognitive distortion classifier (klue/roberta-large, Azure Container Apps)
   ├── Azure AI Search (RAG)     → CBT/DBT/MI knowledge corpus
   ├── Azure OpenAI              → empathetic response generation
   └── Azure Cosmos DB           → sessions, profiles, crisis-center data
```

Supporting Azure services used directly from this app:

- **Azure AI Content Safety** (`crisis_gate.py`) — text severity analysis for crisis detection
- **Azure Cosmos DB** (`get_centers.py`) — lookup of 400+ Korean crisis support centers (KFSP data)
- **Kakao Local API** (`kakao_geo.py`) — GPS coordinates → administrative region conversion

## Project Structure

```
app/
├── app.py                  # Home page ("마을 광장" / Village Square)
├── api_client.py           # All backend REST/SSE calls live here
├── ui_theme.py             # Shared palette, theme CSS, sidebar/topbar renderers
├── crisis_gate.py          # Azure Content Safety wrapper (crisis check)
├── get_centers.py          # Crisis support center recommendations (Cosmos DB)
├── kakao_geo.py            # Kakao API: coordinates → sido/sigungu
├── requirements.txt
├── assets/
│   ├── bookmark-hero.svg   # Home hero illustration
│   ├── village-hero.jpg
│   └── skorea_provinces.json  # GeoJSON of 17 Korean provinces (admin map)
└── pages/
    ├── 0_로그인.py          # Login (email → virtual hashed user ID)
    ├── 1_채팅.py            # Chat — main CBT conversation (SSE streaming)
    ├── 2_분석대시보드.py     # Analytics dashboard ("마음 일기", Plotly charts)
    ├── 3_생각도감.py         # Encyclopedia of 10 cognitive distortion types
    ├── 4_설문.py            # Pre-survey: profile, consents, emergency contact
    ├── 5_이전대화기록.py     # Past conversation history browser
    ├── 6_취업도우미.py       # Job-seeker helper: posting fit analysis, cover letters
    └── 7_관리자.py          # Admin console (password-gated, not in sidebar nav)
```

## Pages

| Page | Description |
|------|-------------|
| **마을 광장** (`app.py`) | Home. Hero banner, session stats, menu cards, Azure service status checks. |
| **로그인** (`0_로그인.py`) | Email-based login. Email is hashed (SHA-256, 32 chars) into a virtual `x-user-id` — the raw email is never sent to the server. |
| **대화하기** (`1_채팅.py`) | Core CBT chat. Streams responses via SSE. Supports text, voice (STT), and KakaoTalk screenshot (OCR) input. On crisis detection, shows nearby support centers using GPS (with consent) or manual region selection. |
| **마음 일기** (`2_분석대시보드.py`) | Per-user analytics: distortion distribution and trends over time. |
| **생각도감** (`3_생각도감.py`) | Card-style guide to the 10 cognitive distortion types. |
| **사전 질문** (`4_설문.py`) | Profile survey with granular privacy consents (required + optional items). |
| **이전 대화 기록** (`5_이전대화기록.py`) | Lists the user's past sessions; reopen or continue any conversation. |
| **취업 준비** (`6_취업도우미.py`) | Job-posting fit analysis, cover-letter drafting, and resume review — generates factual evidence to counter distortions like "I'll never get hired." |
| **관리자** (`7_관리자.py`) | Operator-only console (direct URL access). Anonymous aggregate stats, regional choropleth map, crisis-detection log. No personal conversation content is stored or displayed. |

## Getting Started

### Prerequisites

- Python 3.11+
- A running gateway backend (default: `http://localhost:8000`)
- Azure resource keys (see Environment Variables)

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the app root:

```dotenv
# Gateway backend
BACKEND_URL=http://localhost:8000
GATEWAY_API_KEY=                  # only if the gateway requires it
CAREER_BACKEND_URL=               # optional, defaults to BACKEND_URL

# Azure AI Content Safety
CONTENT_SAFETY_ENDPOINT=
CONTENT_SAFETY_KEY=

# Azure AI Search (RAG)
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=

# Cognitive distortion classifier (Azure ML / Container Apps)
AZURE_ML_ENDPOINT=
AZURE_ML_KEY=

# Cosmos DB (crisis center lookup)
COSMOS_ENDPOINT=
COSMOS_KEY=

# Kakao Local API (GPS → region)
KAKAO_REST_API_KEY=

# Admin console
ADMIN_PASSWORD=
```

The home page shows a live "open / closed" status for each Azure service based on whether its variables are configured.

### Run

```bash
streamlit run app.py
```

Then open `http://localhost:8501`.

## Key Design Notes

- **Backend separation** — Streamlit never calls Azure OpenAI or the classifier directly for chat; everything goes through `api_client.py` → gateway (`/v1/respond` SSE, `/v1/profile`, `/v1/sessions`, `/v1/career/*`).
- **Privacy by design** — emails are hashed client-side into virtual IDs; emergency contact display and GPS use each require explicit opt-in consent; the admin console handles anonymous aggregates only.
- **Crisis safety flow** — Content Safety severity thresholds (self-harm ≥ 2, or any category ≥ 4) trigger the crisis path: RAG is bypassed and verified KFSP crisis-center contacts are shown, prioritized by institution type and filtered for night/weekend availability.
- **macOS note** — Korean page filenames must be NFC-normalized for `st.page_link()` to resolve correctly (`ui_theme.resolve_page()` handles this).

## Tech Stack

Streamlit · Plotly · pandas · Azure AI Content Safety · Azure Cosmos DB · Kakao Local API · python-dotenv · requests (SSE streaming)

## Team

Built by **Team 3**, 대한상공회의소 AI School (10th cohort), as the second team project — GitHub org: [MSAI-PJ2](https://github.com/MSAI-PJ2).

## License

For educational / portfolio purposes.
