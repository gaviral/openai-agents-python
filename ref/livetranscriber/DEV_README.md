## Version Update Instructions

1. Check existing git tags using `git tag` to identify the last used version.
2. Evaluate the required version bump based on the [Versioning](#versioning) section below.
3. `pyproject.toml`: Line 3
4. `livetranscriber.py`: Line 2
5. after updating the versions above, run `uv lock` to update the `uv.lock` file
6. commit and push the changes
7. create a new tag `git tag vx.x.x` (the v is important for CI/CD to work)
8. push the tag `git push --tags`

## Versioning

`livetranscriber` follows [Semantic Versioning](https://semver.org/). The version number is managed in the following locations:

*   `pyproject.toml`
*   `uv.lock`
*   The package docstring in `livetranscriber.py`

When making changes that require a version bump:

1.  Update the version number in all three locations according to Semantic Versioning principles.
2.  Commit the changes using a [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/) message.
3.  Push the commit to the remote repository.
4.  Create a Git tag corresponding to the new version number (e.g., `v0.2.2`).
5.  Push the tag to the remote repository.
