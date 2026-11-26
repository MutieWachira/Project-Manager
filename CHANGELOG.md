# Changelog

All notable changes to SherlskyyCommand will be documented here.
## [0.5.0](https://github.com/MutieWachira/Project-Manager/compare/v0.4.1...v0.5.0) (2026-11-26)


### Features

* add project operations and GitHub App integration. ([431cdad](https://github.com/MutieWachira/Project-Manager/commit/431cdadd34a0d424c87444b4d5ea159746cf16f0))

## [0.5.0]
### Added

- Introduced the project operations foundation, including project environments, integrations, events, and incidents.
- Added project environment management with primary and active environment constraints.
- Added project integration management with role-based access control and protected configuration data.
- Implemented GitHub App installation and OAuth callback workflows.
- Added secure, single-use GitHub installation state validation with expiration and replay protection.
- Added GitHub integration connection and reconnection workflows to the web dashboard.
- Added project operations API schemas, models, routes, and database migrations.

### Changed

- Improved authentication dependencies, email delivery, login handling, and project API behavior.
- Updated the web dashboard, registration page, project integration interface, and What's New component.
- Consolidated backend application, testing, and development dependencies into `backend/requirements.txt`.
- Updated Expo mobile dependencies and registered the Expo Web Browser plugin.

### Security

- Added validation of GitHub App installation ownership and application identity.
- Prevented OAuth access tokens and sensitive integration configuration from being exposed through API responses.
- Added protection against expired, replayed, or invalid GitHub installation callback states.

### Tests and Verification

- Expanded backend tests for authentication, email delivery, login, project operations, and GitHub App integration.
- Verified the backend test suite successfully.
- Verified frontend and mobile TypeScript checks.
- Verified Expo dependency compatibility.
- Verified Alembic migration consistency and dependency health.

### Current Status

- The project is in active development following version `0.4.1`.
- Project operations and GitHub App integration are implemented, with the GitHub integration connection flow available through the web dashboard.
- GitHub repository synchronization is not yet implemented.
- Release Please is configured to prepare release pull requests from Conventional Commits and publish GitHub Releases when those pull requests are merged.

## [0.4.1](https://github.com/MutieWachira/Project-Manager/compare/v0.4.0...v0.4.1) (2026-11-14)

### Bug Fixes

- Fixed release bug issue. ([0adf775](https://github.com/MutieWachira/Project-Manager/commit/0adf775808963d088d76a733f9caa2308ed4d8bb))

## [0.4.0](https://github.com/MutieWachira/Project-Manager/compare/v0.3.0...v0.4.0) (2026-11-14)

### Features

- **dashboard:** Redesign web and mobile dashboards ([edeb0d9](https://github.com/MutieWachira/Project-Manager/commit/edeb0d960dc42171862088ae3c2fc98cae226551))
- **mobile:** Implement authentication and protected navigation ([b12bb08](https://github.com/MutieWachira/Project-Manager/commit/b12bb08c17ab9f221ec51e701e506be2fabcd67c))

## [0.3.0](https://github.com/MutieWachira/Project-Manager/compare/v0.2.0...v0.3.0) (2026-11-13)

### Features

- Add secure authentication, project management, and release updates. ([476f217](https://github.com/MutieWachira/Project-Manager/commit/476f217552b63a1add0c71e130b000f04a378e04))

## [0.2.0](https://github.com/MutieWachira/Project-Manager/compare/v0.1.0...v0.2.0) (2026-11-13)

### Features

- Add secure authentication, project management, and release updates. ([476f217](https://github.com/MutieWachira/Project-Manager/commit/476f217552b63a1add0c71e130b000f04a378e04))


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
