# LLM Golden Flower

A web-based **Zha Jin Hua (炸金花 / Three-Card Poker)** game where you play against up to 5 AI opponents, each powered by a different LLM. Every AI has its own personality, talks trash at the table, learns from past rounds, and keeps a detailed "thought journal" you can read after each game.

## Features

- **Multi-Model AI Opponents** — 1-5 AI players, each driven by a different LLM provider (OpenRouter, GitHub Copilot, Azure OpenAI, SiliconFlow). Mix and match models at the table.
- **Distinct Personalities** — Aggressive, Conservative, Analytical, Intuitive, Bluffer — each shapes how the AI bets, bluffs, and talks.
- **Table Talk** — AI trash-talks, reacts to other players as a bystander, and responds to your messages in character. Chat feeds back into decision-making.
- **Experience Learning** — AI reviews its own play and adjusts strategy on losing streaks, big losses, chip crises, or opponent shifts.
- **Thought Journal** — Structured decision records (hand eval, risk, confidence, emotion) + first-person narratives per round + full game summary with stats and self-reflection.
- **Cyberpunk Theme** — Neon glow, glassmorphism, 3D poker table, full-body character illustrations.

## Game Rules (炸金花)

Standard 52-card deck, 3 cards per player. Hand rankings (high to low): **豹子** Three of a Kind > **同花顺** Straight Flush > **同花** Flush > **顺子** Straight > **对子** Pair > **散牌** High Card. Unseen players bet at half rate. Actions: Fold, Call, Raise, Peek, Compare.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS 4, Framer Motion, Zustand |
| Backend | Python, FastAPI, LiteLLM, SQLAlchemy (async), SQLite |
| Communication | WebSocket + REST |

### LLM Providers

OpenRouter, GitHub Copilot (OAuth Device Flow), Azure OpenAI, SiliconFlow — all configurable in-app.

## Getting Started

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

API keys are managed in the in-app Model Config Panel — no `.env` needed. Keys are memory-only, never persisted to disk.

## Architecture

```
Browser (React SPA)
  ↕ WebSocket + REST
FastAPI Backend
  ├── Game Engine — deck, evaluator, rules, game lifecycle
  ├── AI Agents — LLM decision, chat, experience learning
  ├── Thought Journal — structured records, narratives, summaries
  └── SQLite — 8 tables (async)
  ↕ LLM APIs (OpenRouter, Copilot, Azure, SiliconFlow)
```

**Information hiding**: frontend never sees other players' cards. **Fault tolerance**: non-JSON LLM responses trigger multi-layer fallback; illegal actions degrade to call/fold; API timeouts auto-fold after retries.

## Documentation

- [PRD](docs/PRD.md) — Requirements, game rules, feature specs
- [Technical Design](docs/TECH_DESIGN.md) — Architecture, data models, API specs
- [Tasks](docs/TASKS.md) — 30 tasks across 8 phases

## License

[MIT](LICENSE)
