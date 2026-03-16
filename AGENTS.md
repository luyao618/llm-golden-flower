# Agentic Coding Guidelines

This document provides essential instructions for AI agents operating within the `golden-flower-poker-ai` repository.

## 1. Project Overview

This is a full-stack application consisting of:
- **Backend**: Python (FastAPI) with `uv`/`hatchling` build system.
- **Frontend**: TypeScript (React + Vite) with `npm`.

## 2. Backend (Python)

### Commands
Run these commands from the `backend/` directory.

- **Install Dependencies**: `uv sync` (or `pip install -e .[dev]`)
- **Start Server**: `uvicorn app.main:app --reload`
- **Run All Tests**: `pytest`
- **Run Single Test File**: `pytest tests/path/to/test_file.py`
- **Run Single Test Case**: `pytest tests/path/to/test_file.py::test_function_name`
- **Lint/Format**: `ruff check .` (add `--fix` to auto-fix)

### Code Style & Conventions
- **Type Hints**: Mandatory for all function signatures (e.g., `def fn(x: int) -> str:`).
- **Async/Await**: Use `async def` for route handlers and DB operations.
- **Docstrings**: Use triple-quoted strings (`"""`) for module and function documentation.
  - Language: Chinese (preferred for business logic explanations based on existing code).
  - Format: Summary line, blank line, detailed description.
- **Imports**: Sorted by: Standard Library -> Third Party -> Local Application (`app.*`).
- **Path Handling**: Use absolute imports from the `app` root (e.g., `from app.models import User`).

## 3. Frontend (TypeScript/React)

### Commands
Run these commands from the `frontend/` directory.

- **Install Dependencies**: `npm install`
- **Start Dev Server**: `npm run dev`
- **Build**: `npm run build`
- **Lint**: `npm run lint`

### Code Style & Conventions
- **Framework**: React 19+ (Functional Components with Hooks).
- **Language**: TypeScript (Strict mode enabled).
- **Formatting**:
  - **Semicolons**: Avoid semicolons (ASI style).
  - **Quotes**: Single quotes preferred for strings.
  - **Indentation**: 2 spaces.
- **Components**:
  - PascalCase for component filenames and function names.
  - Export components as default exports: `export default function MyComponent() { ... }`.
- **State Management**: Use `zustand` for global state.
- **Styling**: Tailwind CSS (utility-first).
- **Imports**: Omit file extensions for `.ts`/`.tsx`/`.js`/`.jsx` files.

## 4. General Agent Guidelines

- **File Paths**: Always verify file paths before editing. The backend code resides in `backend/app/`, and frontend source in `frontend/src/`.
- **Safety**:
  - Always run tests (`pytest` for backend) after modifications.
  - Use `ruff` to verify Python code quality before committing.
  - Use `npm run lint` to verify Frontend code quality.
- **Refactoring**: When modifying existing code, strictly adhere to the surrounding style (naming, spacing, patterns).
- **Dependencies**: Do not add new libraries without first checking `pyproject.toml` or `package.json` to see if an equivalent already exists.
