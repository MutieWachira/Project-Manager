# Releases

SherlskyyCommand uses [Conventional Commits](https://www.conventionalcommits.org/)
and Release Please to prepare versioned GitHub Releases. Push commits to the
repository's default branch to create or update a release pull request. Review
its version and generated `CHANGELOG.md`, then merge it to publish the `vX.Y.Z`
tag and GitHub Release.

Use commit prefixes such as:

- `feat: add project filters` for a feature release.
- `fix: correct project status display` for a patch release.
- `feat!: change the project API` for a breaking release.

Before version `1.0.0`, breaking changes bump the minor version. The release
pull request updates `version.txt`; the backend API reads its version from that
file. The dashboard's **What's new** dialog reads the latest dated release from
`CHANGELOG.md` and automatically appears once for each new version.

In the repository's Actions settings, allow GitHub Actions to create pull
requests so Release Please can open the release PR.