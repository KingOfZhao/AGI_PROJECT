# AGI_PROJECT - Development Context

This is a **software development project** for building an AI-assisted automation system.
The assistant (Cascade/Windsurf) is a standard coding assistant helping with development tasks.

## Project Overview
- Python-based backend with API services
- Integrates with Zhipu GLM LLM API and local Ollama models
- Uses SQLite databases for logging and deduction tracking
- Includes WeChat bot integration for notifications

## Key Directories
- `core/` — Core business logic
- `scripts/` — Utility and startup scripts
- `api/` — FastAPI service layer
- `skills/` — Reusable code skills library
- `data/` — Training data and knowledge feeds
- `logs/` — Runtime logs

## Development Guidelines
- All sensitive credentials (API keys) are stored in `.env` only — never hardcoded
- Use `python3 -m pytest tests/` to run the test suite
- Main entry point: `start.sh` or `python3 -m uvicorn api.main:app`

## Scope
This is a standard software engineering workspace. All tasks here are legitimate
software development activities: writing code, debugging, refactoring, testing,
and documentation.
