# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-02

### Added

- Support for mobile device login links (`?client=ios` format)
- New i18n message `auth_mobile_link_header` for mobile login notifications
- Separate emoji icon (📱) for mobile login links

## [1.0.0] - 2024-12-31

### Added

- Initial release
- Gmail API integration with OAuth 2.0 authentication
- Automatic extraction of Claude magic-link URLs
- Support for 6-digit verification codes
- Telegram bot notifications
- Multi-user support via `ALLOWED_USER_IDS` config
- Configurable check interval (default: 15 seconds)
- Auto mark emails as read after processing
- Docker and Docker Compose support
- Comprehensive README with setup instructions

### Security

- OAuth 2.0 for secure Gmail access
- Token-based authentication (no password storage)
- Read-only Gmail permissions (gmail.modify for marking as read)

## [Unreleased]

### Planned

- Environment variables support for Docker secrets
- Webhook mode for instant notifications (Gmail Push)
- Web UI for configuration
- Multiple email accounts support
- Prometheus metrics endpoint

---

[1.2.0]: https://github.com/deniskoleda/claude-auth-forwarder/releases/tag/v1.2.0
[1.0.0]: https://github.com/deniskoleda/claude-auth-forwarder/releases/tag/v1.0.0
[Unreleased]: https://github.com/deniskoleda/claude-auth-forwarder/compare/v1.2.0...HEAD
