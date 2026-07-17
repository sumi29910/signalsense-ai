# SignalSense AI

AI agent for traffic violation detection, congestion analysis, and emergency
vehicle priority — built for the HiDevs Google Agent Builder Series 2026,
Smart Cities track.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [How the Chat Agent Works](#how-the-chat-agent-works)
6. [Setup & Installation](#setup--installation)
7. [API Endpoints Reference](#api-endpoints-reference)
8. [Pushing to GitHub](#pushing-to-github)
9. [Submission Form Mapping](#submission-form-mapping)
10. [What Makes This Different](#what-makes-this-different)


## Real-world traffic lookup (Google Maps)
Genie can now answer questions about ANY real place — not just monitored
junctions — using live Google Maps data:
- "How's traffic at Sunaliya Chowk, Korba?" → Genie calls `check_real_world_traffic`
- The Location Search page also has a direct Origin/Destination form for quick lookups
- Requires `GOOGLE_MAPS_API_KEY` in `.env` (Distance Matrix API enabled + billing on that GCP project — see `.env.example` for the setup link)
- Without a key, this gracefully tells the operator it isn't configured yet, instead of crashing

Genie's tool-calling now uses Gemini's built-in function calling
(`agents/genie_agent.py`), not Google ADK — ADK caused repeated server
crashes during testing on Windows, so this is the stable replacement.
`agents/adk_agent.py` is still in the project if you want to test/demo it
separately with `adk web`, but it isn't wired into the live app.

## Bug fixes applied (from real testing)
- **Qdrant index error** — filtering by `junction_id` needs a payload index; `init_qdrant()` now creates one automatically
- **Gemini quota errors (429)** — switched all agents from `gemini-2.0-flash` to `gemini-1.5-flash` (the free-tier key used for testing had zero quota on 2.0)
- **`google.adk` not found** — remember to run `pip install -r requirements.txt` after pulling changes so `google-adk` installs

## New features
- **Sidebar navigation** — Overview, Analyze, Live Feed, History, Corridor & Forecast, Location Search, AI Assistant, each as its own page
- **Voice input** — click 🎤 in the chat to speak your question (Chrome/Edge, uses the Web Speech API, no backend needed)
- **Voice output** — toggle "Read replies aloud" in the chat panel to have the analyst's answers spoken back
- **Location search** — ask general traffic questions about any city worldwide (`agents/location_agent.py`, `/location-query` endpoint) — clearly separate from the control-room chat, which only answers about your monitored junctions

## Overview

SignalSense AI is built around 4 pillars — the first 3 work per-junction,
the 4th works at the **network/city scale**, which is what makes this a
genuine Smart Cities submission rather than a single-camera demo:

1. **Detect** — Gemini vision reads traffic camera frames for violations & emergency vehicles
2. **Decide** — Qdrant memory + a safety guardrail so low-confidence detections are never falsely flagged
3. **Converse** — a control-room chat agent an operator can ask questions to, grounded in real logged data
4. **Coordinate & Predict** — a corridor agent sequences signals across multiple connected junctions for a "green wave", and a forecasting agent flags junctions trending toward congestion before it happens

## Architecture

Traffic camera frames (multiple junctions)
        │
        ▼
 Coordinator Agent  (agents/coordinator.py)
        │
        ├──► Violation Detection Agent  (Gemini vision)
        ├──► Congestion Agent           (Gemini vision)
        └──► Emergency Priority Agent   (Gemini vision)
        │
        ▼
 Qdrant Memory Layer   (network-wide, every junction's history)
        │
        ├──► Corridor Coordination Agent   (green-wave sequencing across junctions)
        ├──► Predictive Forecasting Agent  (trend detection per junction)
        │
        ▼
 Safety Guardrail      (drops low-confidence flags, Enkrypt AI hook)
        │
        ▼
 Response ──► Dashboard (static/dashboard.html — network view, corridor plan, forecast)
        │
        └──► logged back into Qdrant for future pattern learning

Separately:
 Operator question ──► Chat Agent (agents/chat_agent.py)
        │
        ├──► pulls summary of ALL logged events from Qdrant
        └──► Gemini answers, grounded only in that real data
```

## Technology Stack

### Backend
| Tool | Purpose | Status |
|---|---|---|
| **FastAPI** | Python web framework — serves all API routes | ✅ used |
| **Gemini API** | Vision + language model powering all detection agents | ✅ used |
| **Google ADK** | Real `Agent` + tool-calling for the control-room chat (`agents/adk_agent.py`) | ✅ used |
| **Vertex AI** | Set `GOOGLE_GENAI_USE_VERTEXAI=True` in `.env` to route the ADK agent's Gemini calls through Vertex AI instead of an AI Studio key | ✅ used (opt-in) |
| **Google Cloud Storage** | Every analyzed frame is stored permanently (`storage/gcs_store.py`) — needed to audit a flagged violation later | ✅ used (opt-in, falls back to local disk) |
| **Qdrant** | Vector database — memory layer for junction history | ✅ used |
| **Enkrypt AI** | Safety/guardrail layer | ⚠️ hook ready, add your key to activate |

### Frontend
| Tool | Purpose |
|---|---|
| **Plain HTML/CSS/JS** | No build step — `static/dashboard.html` is the main UI |
| **Fetch API** | Talks to the FastAPI backend |

### Not yet used (remove from form unless you add them)
Firebase, Cloud Run, MCP, GCP (beyond Vertex AI) — these are documented as
"next steps" below, not implemented yet. Only tick what's genuinely in the code.


## About the camera

There's no live camera feed here — frames are uploaded (manually, or via
the **Live Feed Simulation** panel which auto-replays a batch of uploaded
images on a timer, mimicking a real camera stream). In production these
frames would arrive automatically from junction cameras; for the hackathon
demo, upload/simulation stands in for that. Say this explicitly in your
pitch — judges understand hardware access isn't feasible in a hackathon.


## Project Structure

signalsense-ai/
├── main.py                     # FastAPI app — all API routes live here. Start here.
├── requirements.txt            # Python dependencies
├── .env.example                # Copy to .env and fill in your real API keys
├── .gitignore                  # Keeps .env and venv/ out of GitHub
├── README.md                   # This file
│
├── agents/                     # Each file = one agent, one job
│   ├── __init__.py
│   ├── coordinator.py          # Routes a frame through all agents in order
│   ├── violation_detection.py  # Gemini vision — red-light jump, no-helmet, wrong lane, etc.
│   ├── congestion_agent.py     # Gemini vision — density estimate + signal timing suggestion
│   ├── emergency_agent.py      # Gemini vision — detects ambulance/fire/police vehicles
│   ├── chat_agent.py           # Simple fallback — direct Gemini call, used if ADK isn't configured
│   ├── adk_agent.py            # REAL Google ADK agent with tools — primary chat engine
│   ├── corridor_agent.py       # Pillar 4 — green-wave signal sequencing across junctions
│   └── predictive_agent.py     # Pillar 4 — trend forecasting from historical Qdrant data
│
├── memory/
│   ├── __init__.py
│   └── qdrant_store.py         # All Qdrant read/write logic
│
├── safety/
│   ├── __init__.py
│   └── guardrail.py            # Confidence-threshold filter + Enkrypt AI integration point
│
├── storage/
│   ├── __init__.py
│   ├── local_store.py          # Always-on local backup — saves frames to uploads/
│   └── gcs_store.py            # Google Cloud Storage — permanent frame storage (opt-in)
│
├── uploads/                     # Local frame backups, organized by junction_id (gitignored)
│   └── .gitkeep
│
└── static/
    ├── dashboard.html          # MAIN deliverable — overview cards, upload panel, chat widget
    └── index.html              # Minimal test page (optional, for quick debugging)
```


## How the Chat Agent Works

This is the part most people get confused about, so here's the exact mechanism:

1. Every time a frame is analyzed, the result is logged into Qdrant **tagged with its `junction_id`** (`memory/qdrant_store.py → log_event()`)
2. When the operator asks a question, `get_all_junctions_summary()` pulls **every logged event across all junctions** and formats it as plain text, e.g.:
   ```
   - Junction junction_01: violations=[red_light_jump], congestion=medium, emergency=False
   - Junction junction_03: violations=[no_helmet, wrong_lane], congestion=high, emergency=False
   ```
3. This text is passed to Gemini as grounding context along with the question
4. Gemini reads the real logged text and answers — it is explicitly instructed to **never invent numbers or junctions that aren't in the data**

**Practical implication:** the chat agent is only as good as the data you've logged.
Before recording your demo video, upload **5–10 varied test frames** across a
few different junction IDs so the chat answers have real substance.


## Setup & Installation

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your keys
cp .env.example .env
# then open .env and fill in:
#   GEMINI_API_KEY   -> https://aistudio.google.com/apikey (free)
#   QDRANT_URL / QDRANT_API_KEY -> https://cloud.qdrant.io (free tier)
#   ENKRYPT_API_KEY  -> https://enkryptai.com (optional — has local fallback)

# 4. Run the server
python main.py
```

Open **http://localhost:8000/static/dashboard.html** — the main control-room view.
API docs (auto-generated): **http://localhost:8000/docs**

### Testing the ADK agent standalone (optional but worth doing)

Because `agents/adk_agent.py` defines a real `root_agent`, ADK's own dev
UI can talk to it directly — useful for debugging tool calls before you
rely on it through the dashboard:

```bash
cd agents
adk web
```

This opens a browser UI where you can chat with `signalsense_control_room_agent`
and watch exactly which tool it calls for each question.

### Using Vertex AI instead of an AI Studio key

In `.env`, set:
```
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```
Then run `gcloud auth application-default login` once. The ADK agent's
Gemini calls will now route through Vertex AI.

---

## API Endpoints Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Health check |
| POST | `/analyze-junction` | Upload a frame (`junction_id` + `frame` file) → runs full agent pipeline |
| GET | `/junction/{junction_id}/history` | Past events for one junction |
| GET | `/junction/{junction_id}/forecast` | Predictive agent — congestion trend for one junction |
| POST | `/corridor/optimize` | `{"junction_ids": ["a","b","c"]}` → green-wave signal timing plan |
| POST | `/chat` | `{"question": "..."}` → conversational analyst answer |
| GET | `/overview` | Summary text used for dashboard stat cards |

---

## Pushing to GitHub

```bash
cd signalsense-ai
git init
git add .
git commit -m "Initial SignalSense AI agent"

# create a new empty repo on github.com first, then:
git remote add origin https://github.com/<your-username>/signalsense-ai.git
git branch -M main
git push -u origin main
```

The included `.gitignore` already excludes `.env`, `venv/`, and `__pycache__/`
so your real API keys never get pushed publicly. Double check `git status`
before your first commit to confirm `.env` is not listed.


## Submission Form Mapping

Tick: Gemini Models, Agent Development Kit (ADK), AI Studio, MCP, Vertex AI
(once added), Firebase, Cloud Run, Google Cloud (GCP), Qdrant, Enkrypt AI.
In "Other tech stack" write: `FastAPI, Python`

---

## What Makes This Different

- Not a manual-control dashboard (that's operations tooling, not an agent)
- Not just sensor-failure resilience (that's a narrower reliability problem)
- This one **detects, reasons about confidence, and lets a human converse
  with it** — the combination of automation + a safety-first "don't
  false-flag" guardrail + a conversational memory layer is the differentiator.
