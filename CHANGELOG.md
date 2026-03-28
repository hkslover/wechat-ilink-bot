# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Placeholder for upcoming changes.

## [0.1.0] - 2026-03-28

### Added

- Initial public release of `wechat-ilink-bot`.
- QR login flow with local credential persistence.
- Long-polling runtime with handler registration and first-match dispatch model.
- Proactive send APIs:
  - `send_text`
  - `send_image`
  - `send_video`
  - `send_file`
- Message-context reply APIs:
  - `reply`
  - `reply_image`
  - `reply_video`
  - `reply_file`
  - `send_typing`
- Media upload and download helpers.
- Webhook server (`/healthz`, `/send`) with API key support.
- CLI command: `wechat-bot webhook`.
- Owner-default recipient behavior with explicit `to` override support.
- Account switching and local account listing support.
- Read the Docs documentation scaffold (`MkDocs + mkdocstrings`).
- CI/testing/lint/build packaging checks.

### Changed

- Unified package version source in `src/wechat_bot/_version.py`.
- Standardized webhook response format:
  - success: `{"status": 200}`
  - error: `{"status": <code>, "detail": "..."}`
- Improved recipient resolution and error clarity for missing owner state.
- Improved local storage safety with atomic JSON writes and strict file permissions when supported.
