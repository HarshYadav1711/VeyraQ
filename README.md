# VeyraQ

**AI-Assisted Pharmaceutical Complaint Intelligence**

VeyraQ is an AI-powered customer complaint intake module for pharmaceutical manufacturing (API and FDF). It helps QA personnel turn unstructured complaint text or documents into structured, reviewable complaint records—with human commit as the final control.

> Assessment project for the AI Product Engineer internship at AIVOA.

## What it does

1. Accepts raw complaint text/email or an uploaded document
2. Extracts structured complaint fields via a LangGraph + Groq workflow
3. Populates a Log Customer Complaint form (Redux-backed)
4. Produces an advisory initial risk assessment
5. Supports conversational field corrections that patch **only** the fields the user changes
6. Checks completeness and readiness
7. Commits only when a human explicitly approves

## Stack (mandatory)

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Redux Toolkit, CSS Modules, Inter |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic |
| AI | LangGraph StateGraph, Groq |
| Database | PostgreSQL |
| Documents | PyMuPDF (PDF text); TXT/EML where practical |
| Testing | Pytest, Vitest, Playwright (one critical E2E path) |

## Documentation

| Document | Purpose |
| --- | --- |
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | Authoritative non-negotiable project context |
| [docs/PRD.md](docs/PRD.md) | Product requirements and acceptance criteria |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System boundaries and data flow |
| [docs/DOMAIN.md](docs/DOMAIN.md) | Domain terminology and assumptions |
| [docs/DESIGN.md](docs/DESIGN.md) | UI/UX direction and design tokens |
| [docs/RULES.md](docs/RULES.md) | Strict rules for future coding assistants |
| [docs/PHASES.md](docs/PHASES.md) | Incremental implementation plan |
| [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) | LangGraph workflow, provenance, reliability |
| [docs/DEMO.md](docs/DEMO.md) | Product and code walkthrough demo plan |

## Status

Documentation phase complete. Application scaffolding has not started.

## Core principle

AI assists QA. AI must never silently invent complaint facts. Source, user, inferred, and missing values remain distinguishable. Final commit authority stays with the human.
