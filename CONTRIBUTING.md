# Contributing Guide

Thanks for contributing to the CCTV AMC Platform. This document describes how we
work so development stays smooth and `main` stays deployable.

## Golden Rule

**Never commit directly to `main`.** All changes go through a branch and a pull
request that passes CI and review.

## Branching

Branch off the latest `main` for every change:

```bash
git checkout main
git pull
git checkout -b <type>/<short-description>
```

Use these branch prefixes:

| Prefix      | Use for                                      |
| ----------- | -------------------------------------------- |
| `feat/`     | A new feature                                |
| `fix/`      | A bug fix                                     |
| `chore/`    | Tooling, deps, config, housekeeping          |
| `docs/`     | Documentation only                           |
| `refactor/` | Code change that neither fixes a bug nor adds a feature |
| `test/`     | Adding or fixing tests                        |

Examples: `feat/invoice-pdf-export`, `fix/login-token-refresh`.

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary in imperative mood>

<optional body explaining what and why>
```

Examples:

```
feat: add PDF export to invoices page
fix: prevent aborted RLS transaction leaking into connection pool
chore: bump bcrypt to 4.x
docs: document local setup in README
```

Keep commits small and focused — one logical change per commit.

## Pull Requests

1. Push your branch: `git push -u origin <your-branch>`
2. Open a PR against `main` on GitHub.
3. Fill in the PR template (it appears automatically).
4. Ensure **CI passes** (lint, tests, build) and **gitleaks** finds no secrets.
5. Request a review. Address feedback with follow-up commits.
6. Once approved and green, **squash and merge**, then delete the branch.

## Code Quality

Before pushing, run the same checks CI runs:

```bash
# Backend
cd backend
ruff check app tests
pytest tests/ --cov=app

# Frontend
cd frontend
npm run lint
npm test
```

## Database Migrations

Any schema change must include an Alembic migration in the same PR:

```bash
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head   # verify it applies cleanly
```

Never modify a shared database schema by hand.

## Secrets

- **Never** commit real secrets (DB passwords, `JWT_SECRET_KEY`, API tokens).
- Configuration belongs in `.env`, which is git-ignored.
- Add new config keys to `.env.example` with placeholder values.
- CI runs **gitleaks** on every PR and will fail if a secret is detected.
