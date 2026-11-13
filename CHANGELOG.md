# Changelog

All notable changes to SherlskyyCommand will be documented here.

## [0.2.0](https://github.com/MutieWachira/Project-Manager/compare/v0.1.0...v0.2.0) (2026-11-13)


### Features

* add secure auth, project management, and release updates. ([476f217](https://github.com/MutieWachira/Project-Manager/commit/476f217552b63a1add0c71e130b000f04a378e04))

## [Unreleased]

### Added
- Account registration, email verification, sign-in, and protected dashboard flows.
- Project creation and listing for the signed-in user's workspace.
- TOTP multi-factor authentication challenges during sign-in, with encrypted authenticator secrets and replay protection.
- Database-backed user sessions and rotating refresh tokens, including refresh-token reuse detection and session revocation.
- Release Please automation that prepares a version and changelog pull request and publishes a GitHub Release when merged.
- A dashboard "What's New" dialog that presents the latest published changelog entry once per user and release.

### Changed
- Web refresh tokens are held in secure HttpOnly cookies; API authentication now associates access tokens with revocable sessions.
- The backend reports its application version from the root `version.txt` file managed by release automation.
- Browser API access is restricted to the configured frontend origin.

### Current status
- The project is in active development at version `0.1.0`; these unreleased changes have not yet been published as a GitHub Release.
- The release workflow is configured for the default branch. Its first release pull request requires pushing Conventional Commits to GitHub and allowing GitHub Actions to create pull requests.
- Backend MFA enrollment and verification services are present, but self-service MFA setup/management endpoints and dashboard UI are not yet wired up.

## [0.1.0] - 2026-11-11

### Added
- Initial project structure.
- Git version control initialization.
- Root README documentation.
- Environment variable template.
- Git ignore configuration.
- Initial development changelog.
- Initial PostgreSQL database schema.
- User model with UUID identifiers and unique email constraint.
- Project model with lifecycle status.
- Project membership model with role-based membership.
- Alembic migration management.
