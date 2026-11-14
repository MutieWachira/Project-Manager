# Releases

SherlskyyCommand uses [Conventional Commits](https://www.conventionalcommits.org/)
and Release Please to prepare independent web and mobile GitHub Releases. Push
commits to the repository's default branch to create or update release pull
requests. Review the version and changelog in each release PR, then merge it to
publish the corresponding tag and GitHub Release.

Use commit prefixes such as:

- `feat(web): add project filters` for a web feature release.
- `fix(mobile): correct dashboard layout` for a mobile patch release.
- `feat(web)!: change the project API` for a breaking web release.

Release Please selects components by changed file paths, not commit scope.
Keep mobile-only changes under `mobile/`; changes outside that directory belong
to the web release stream. A commit touching both areas may trigger both release
pull requests.

Before version `1.0.0`, breaking changes bump the minor version. The release
pull request for the web app updates `version.txt`; the backend API reads its
version from that file, and the frontend login page displays the same version
at build time. The mobile release pull request independently updates
`mobile/package.json` and the Expo app version in `mobile/app.json`. Web releases
use `vX.Y.Z` tags; mobile releases use `mobile-vX.Y.Z` tags and their own
`mobile/CHANGELOG.md`.

The dashboard's **What's new** dialog reads the latest web release from
`CHANGELOG.md` and automatically appears once for each new web version.

In the repository's Actions settings, allow GitHub Actions to create pull
requests so Release Please can open both release PRs.