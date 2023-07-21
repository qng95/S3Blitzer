# Contributing to S3Blitzer

Thank you for considering contributing to S3Blitzer! We appreciate your interest in making this tool better for the community. Before contributing, please take a moment to review the guidelines outlined below.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Contributing Guidelines](#contributing-guidelines)
  - [Creating Issues](#creating-issues)
  - [Creating Pull Requests](#creating-pull-requests)
- [Style Guide](#style-guide)
- [Conventional Commit Message](#git-commit-prefixes)
- [License](#license)

## Code of Conduct

Please note that this project has adopted a [Code of Conduct](CODE_OF_CONDUCT.md). We expect all contributors to abide by its terms. Be kind, respectful, and considerate of others. Harassment or any harmful behavior will not be tolerated.

## Getting Started

1. Fork the repository and clone it to your local machine.

   ```
   git clone https://github.com/qng95/S3Blitzer.git
   ```

2. Create a new branch for your changes.

   ```
   git checkout -b my-feature-branch
   ```

3. Set up the development environment as described in the [Installation](README.md#installation) section of the README.

4. Make your changes and test them thoroughly.

5. Commit your changes using [Conventional Commit Message](#git-commit-prefixes) format.

6. Push your changes to your forked repository.

   ```
   git push origin my-feature-branch
   ```

7. Open a pull request against the `main` branch of this repository.

## Contributing Guidelines

### Creating Issues

If you encounter any bugs, have feature requests, or find any areas of improvement, feel free to open a new issue. When creating an issue, please provide detailed information, steps to reproduce (if applicable), and any relevant logs or error messages.

### Creating Pull Requests

We welcome contributions from the community. When creating a pull request, please ensure the following:

1. Follow the [Conventional Commit Message](#git-commit-prefixes) format for your commits.

2. Provide a clear and concise description of your changes in the pull request.

3. Reference any related issues using the `#issue-number` syntax.

4. Ensure that your code adheres to the [Style Guide](#style-guide).

5. Include tests if your changes involve new features or modify existing functionality.

## Style Guide

To maintain consistency and readability of the codebase, we follow the [Python PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide. Please ensure your code adheres to these guidelines.

## Conventional Commit Message

Git commit prefixes are not a standard feature in Git itself, but they are commonly used by development teams to provide meaningful information and structure to commit messages. The prefixes are usually added to the commit subject line to indicate the type or purpose of the commit. 

Here are some common commit prefixes and their meanings:

- **feat:** A new feature or functionality added.
- **fix:** A bug fix.
- **docs:** Documentation updates or additions.
- **style:** Code style changes (e.g., formatting, indentation).
- **refactor:** Code refactoring without changing functionality.
- **test:** Adding or updating test cases.
- **chore:** Maintenance tasks, build process, or other non-functional changes.

Example of a conventional commit message:
```
feat: Add user authentication feature

Implemented user authentication using JWT tokens for secure logins.
```

By using commit prefixes and following a commit message convention, it becomes easier to understand the purpose of each commit in a version control history, especially when browsing through commit logs or reviewing changes.

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache License](LICENSE).
