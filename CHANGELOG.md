# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-01

### Added

- **Text formatting support**: Send messages with markdown-like formatting using `text_mode` parameter
  - `normal` mode: Plain text (default for compatibility)
  - `styled` mode: Supports **bold**, *italic*, ~strikethrough~, `monospace`, ||spoiler||
- **Attachment support**: Send files via local paths or URLs
  - Local file attachments with automatic base64 encoding
  - URL-based attachments with download and verification
  - SSL verification control with `verify_ssl` parameter
  - File size validation (50 MB limit)
- **WebSocket support**: Listen for incoming Signal messages and fire Home Assistant events
  - Real-time message reception
  - Automatic reconnection handling
- **Config flow**: Easy setup through Home Assistant UI
  - User-friendly configuration interface
  - Service name customization
  - Default recipients configuration
- **Service parameter structure**: Compatible with official Signal Messenger integration
  - Nested `data` parameter for attachments, urls, verify_ssl, and text_mode
  - Easy migration path from/to official integration
- **CI/CD pipeline**: Automated testing and quality checks with GitHub Actions
- **Comprehensive test suite**: 93% code coverage with structured test organization
- **Code quality tools**: Full type checking (mypy), linting (pylint), formatting (black)

**Requirements**: Home Assistant 2024.12.0+, Python 3.13+, signal-cli-rest-api server
