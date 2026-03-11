# Golden Flower Poker AI

A web-based **炸金花 (Three Card Poker)** game where you play against multiple AI opponents, each powered by a different LLM (OpenAI / Anthropic / Gemini). Every AI has its own personality, talks trash at the table, learns from past rounds, and keeps a detailed "thought journal" you can read after each game.

## Highlights

- **Multi-model AI opponents** — 1-5 AI players, each driven by a different LLM API via LiteLLM
- **Distinct personalities** — Aggressive, conservative, analytical, intuitive, bluffer — each plays and talks differently
- **Table talk** — AI trash-talks, bluffs verbally, and responds to your chat messages in character
- **Experience learning** — AI reviews past rounds and adjusts strategy (triggered by losing streaks, big losses, chip crises, etc.)
- **Thought journal** — Structured decision records + first-person narratives for every AI, viewable after each round and at game end

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS, Framer Motion, Zustand |
| Backend | Python 3.11+, FastAPI, LiteLLM, SQLAlchemy |
| Database | SQLite |
| Communication | WebSocket + REST API |

## Game Rules (炸金花)

- Standard 52-card deck, 3 cards per player
- Hand rankings (high to low): **豹子** (Three of a Kind) > **同花顺** (Straight Flush) > **同花** (Flush) > **顺子** (Straight) > **对子** (Pair) > **散牌** (High Card)
- Blind/seen betting system — unseen players bet at half the rate of seen players
- Actions: fold, call, raise, check cards (peek), compare hands
- Round ends when only one player remains, a compare is won, or max turns reached

## Project Structure

```
Golden_Flower_Poker_AI/
├── docs/
│   ├── PRD.md              # Product requirements
│   ├── TECH_DESIGN.md      # Technical design
│   └── TASKS.md            # Task breakdown (29 tasks, 8 phases)
├── backend/                # FastAPI backend (planned)
│   ├── app/
│   │   ├── models/         # Data models (card, player, game, chat, thought)
│   │   ├── engine/         # Game engine (deck, evaluator, rules, game flow)
│   │   ├── agents/         # AI agents (decision, chat, experience learning)
│   │   ├── thought/        # Thought journal (recorder, reporter)
│   │   ├── api/            # REST + WebSocket endpoints
│   │   └── db/             # SQLite persistence
│   └── tests/
└── frontend/               # React SPA (planned)
    └── src/
        ├── components/     # Lobby, Table, Cards, Player, Actions, Thought, Settlement
        ├── stores/         # Zustand state management
        ├── hooks/          # WebSocket, game logic hooks
        └── services/       # API client
```

## Development Status

The project is in the **planning phase**. All documentation is complete:

- [PRD](docs/PRD.md) — Full requirements with game rules, 8 feature sections, user flows
- [Technical Design](docs/TECH_DESIGN.md) — Architecture, data models, AI agent design, API specs, DB schema
- [Task Breakdown](docs/TASKS.md) — 29 tasks across 8 phases with dependency tracking

Implementation has not started yet. See [TASKS.md](docs/TASKS.md) for the development roadmap.

## License

Private project.
