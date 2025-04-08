# Contributing

We welcome contributions in several forms, e.g.

- Documenting
- Testing
- Coding
- Reproducing Bugs

Please check [Issues](https://github.com/siemens/vilocify-sdk/issues) and look for unassigned ones or create a new one.

## Guidelines

### Workflow

- Base pull requests on top of the latest `main` branch.
- Pull requests must be rebased to the main branch before merging.
    We use fast-forward merges and squashing without creating merge commits to achieve a linear history.
- Follow our [commit message](#commit-message) style for the title and description of your pull request.
    This allows maintainers to use your title and description of the pull request as commit message.
- We tag releases on the main branch.
- CI checks must succeed before merging to `main`
- A maintainer listed in [CODEOWNERS](/docs/CODEOWNERS) must review and merge the pull request

### Commit Message

We follow the commit message style of [cbeams](https://cbea.ms/git-commit/). The style in summary is:

1. Separate subject from body with a blank line
2. Limit the subject line to 50 characters
3. Capitalize the subject line
4. Do not end the subject line with a period
5. Use the imperative mood in the subject line
6. Wrap the body at 72 characters
7. Use the body to explain what and why vs. how

Commit messages on pull requests can deviate from this style, because commits get squashed when merged to `main` and maintainers can override the commit message.
However, give your pull request a subject and body in this style.
Commits on the main branch must follow this styleguide!
