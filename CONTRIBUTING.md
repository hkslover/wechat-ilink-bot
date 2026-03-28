# Contributing Guide

Thanks for contributing to `wechat-ilink-bot`.

This project is a Python SDK for the WeChat iLink Bot API. Contributions are welcome across runtime code, examples, tests, packaging, and public documentation. Please keep changes small, well-scoped, and aligned with current runtime behavior.

## Development Environment

### Requirements

- Python 3.10+
- A local environment that can install editable dependencies
- Optional: a real WeChat/iLink account only if you want to manually verify login or message delivery flows

### Install development dependencies

```bash
python -m pip install -e .[dev]
```

This installs the core SDK plus the development toolchain used in this repository:

- `pytest` / `pytest-asyncio`
- `ruff`
- `mypy`
- `build`
- `twine`
- webhook-related optional packages already included in `dev`

### Optional extras for focused development

If you are validating a specific distribution scenario, you may also want to test these install paths explicitly:

```bash
python -m pip install -e .[qrcode]
python -m pip install -e .[socks]
python -m pip install -e .[webhook]
```

## Repository Layout

```text
src/wechat_bot/     Core SDK implementation
examples/           Runnable usage examples
tests/              Automated test suite
plans/              Execution/research plans used during maintenance
dist/               Build artifacts
```

Some important modules:

- `src/wechat_bot/bot.py` — high-level user-facing bot API
- `src/wechat_bot/client.py` — low-level async iLink API client
- `src/wechat_bot/polling.py` — long-poll loop, retry, backoff, session recovery
- `src/wechat_bot/storage.py` — local state directory, credentials, sync cursor, context tokens
- `src/wechat_bot/webhook.py` — FastAPI webhook server integration
- `src/wechat_bot/context.py` — handler context helpers for reply, typing, media download

## What to Keep in Sync

When behavior changes, do not update code in isolation. Keep the following layers aligned:

- Runtime implementation in `src/wechat_bot/`
- Examples in `examples/`
- Tests in `tests/`
- Public docs such as `README.md`, `SECURITY.md`, and changelog entries

As a rule of thumb:

- If you change user-visible behavior, update `README.md`
- If you change example usage, update the corresponding script under `examples/`
- If you change runtime behavior, add or update tests
- If you change release-facing behavior, update `CHANGELOG.md` under `Unreleased`

## Development Workflow

A typical contribution flow looks like this:

1. Install the dev environment
2. Make a focused change
3. Add or update tests
4. Update examples/docs if behavior changed
5. Run the verification commands below
6. Update `CHANGELOG.md` when appropriate
7. Open a small, reviewable pull request

## Verification Commands

Run these checks before opening a PR:

```bash
python -m ruff check src tests examples
python -m pytest -q
python -m build
python -m twine check dist/*
```

If you are touching typing-sensitive areas, you may also run:

```bash
python -m mypy src
```

## Verification Matrix

Use the following matrix to decide what to run and what files to inspect.

### 1. Lint and import hygiene

Command:

```bash
python -m ruff check src tests examples
```

Use this for:

- formatting-adjacent issues
- unused imports/variables
- obvious correctness and style regressions

### 2. Behavior validation

Command:

```bash
python -m pytest -q
```

Use this for any runtime behavior change.

Particularly relevant test files:

- `tests/test_bot.py` — account loading, recipient resolution, send behavior, runtime helpers
- `tests/test_polling.py` — session expiry and recovery flow
- `tests/test_storage.py` — state persistence, permissions, current user behavior
- `tests/test_webhook.py` — webhook routing, auth, response format, error behavior
- `tests/test_auth.py` — QR login flow smoke behavior
- `tests/test_examples_smoke.py` — examples importability and basic callable paths

### 3. Packaging validation

Commands:

```bash
python -m build
python -m twine check dist/*
```

Use these when you modify:

- `pyproject.toml`
- package metadata
- README content that affects package rendering
- distribution-facing extras or entry points

## Change-Type Guidance

### If you modify bot runtime behavior

Examples:

- account selection
- owner-default recipient logic
- handler dispatch
- send APIs
- session recovery behavior

Expected follow-up:

- update `tests/test_bot.py`
- update `tests/test_polling.py` if polling/session behavior changed
- update `README.md` if user-facing behavior changed

### If you modify storage or local credential behavior

Examples:

- state directory layout
- `current_user.json`
- `credentials.json`
- file permissions
- atomic write strategy

Expected follow-up:

- update `tests/test_storage.py`
- update `README.md` if local state behavior is user-visible
- update `SECURITY.md` if the security posture changed

### If you modify webhook or CLI behavior

Examples:

- request schema
- response shape
- API key behavior
- host/port/default flags
- GET/POST route behavior

Expected follow-up:

- update `tests/test_webhook.py`
- update `tests/test_cli.py` if CLI behavior changed
- update `README.md`
- update `SECURITY.md` if exposure or auth behavior changed

### If you modify examples

Expected follow-up:

- keep examples runnable and consistent with the current public API
- ensure `tests/test_examples_smoke.py` still reflects the intended import/call path
- update `README.md` example references if script purpose or invocation changed

## Code Style Expectations

- Prefer small, focused pull requests
- Keep public API changes backward-compatible when possible
- Favor clear names and explicit behavior over implicit magic
- Preserve current async-first design unless a change is clearly justified
- Handle errors carefully, especially around auth, polling, storage, and webhook responses
- Avoid leaking sensitive implementation details in externally exposed error surfaces

## Documentation Expectations

This repository treats documentation as part of the product surface.

Please update docs when you change:

- installation flow
- example commands
- webhook usage
- account selection behavior
- state directory behavior
- security-relevant behavior

When updating terms, keep wording consistent across:

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`

Important terms that should stay consistent include:

- `account_id`
- `user_id`
- `owner-default`
- `current_user.json`
- `context_token`
- `webhook key`
- `session expired`

## Changelog Policy

If your change affects users, add an entry under `## [Unreleased]` in `CHANGELOG.md`.

Typical cases:

- new features
- behavior changes
- breaking or compatibility-sensitive adjustments
- docs that materially affect onboarding or operational use
- security-related changes

Try to place changes under the existing categories such as `Added` or `Changed`.

## Pull Request Checklist

Before opening a PR, confirm the following:

- [ ] The change is focused and reviewable
- [ ] Lint passes locally
- [ ] Tests pass locally
- [ ] Examples were updated if usage changed
- [ ] Public docs were updated if behavior changed
- [ ] `CHANGELOG.md` was updated under `Unreleased` when appropriate
- [ ] No sensitive local state or credentials were added to the repository

## Reporting Bugs

If you are opening a bug report, please include:

- Python version
- OS/platform
- minimal reproducible code
- relevant logs or error output
- whether the issue affects login, polling, sending, webhook, storage, or packaging

Open regular bugs in the repository issue tracker.

For suspected security vulnerabilities, do **not** open a public issue. Follow the private disclosure guidance in `SECURITY.md`.
