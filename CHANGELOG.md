# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI workflow for lint, tests, build, and package checks.
- Contributing guide and security policy documentation.
- Additional tests for polling/session behavior, storage security behavior, client config caching,
  auth flow smoke, context behavior smoke, and examples import smoke.
- Webhook extension with one-command startup and GET/POST `/send` API.
- CLI command `wechat-bot webhook` for URL-triggered text sending.

### Changed

- Storage writes now use atomic replacement and tightened file/directory permissions where supported.
- `current_user.json` no longer stores token by default.
- Polling session-expiry handling now prefers explicit recovery and clear failure signaling.
- Version source unified via `src/wechat_bot/_version.py`.
- README and examples reorganized for open-source onboarding.

## [0.1.0] - 2026-03-28

### Added

- Initial public SDK release with QR login, long polling, text/media send, and media download.
