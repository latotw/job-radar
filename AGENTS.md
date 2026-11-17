# Repository Guidelines

## Project Structure & Module Organization

This repository is currently a clean starting point: it contains no application source, tests, assets, or package/build configuration yet. As the project grows, keep production code in a clearly named source directory (such as `src/`), tests in `tests/` or beside the modules they cover, and static assets in a dedicated directory. Update this guide when the actual layout is established.

## Build, Test, and Development Commands

No build, test, or local development commands are configured yet. Before introducing a framework, document its setup and standard commands here. Once available, run the relevant checks locally before submitting changes; do not add a command that the repository cannot execute.

## Coding Style & Naming Conventions

Follow the formatter and linter selected for each language, and commit their configuration with the code. Use descriptive, consistent names: `PascalCase` for types, `camelCase` for functions and variables, and `kebab-case` for standalone filenames unless the language ecosystem has a stronger convention. Keep modules focused and avoid adding dependencies without a clear need.

## Testing Guidelines

There is no test framework or coverage target in the repository yet. Add tests alongside new behavior using the chosen framework's standard naming pattern (for example, `*.test.ts` or `test_*.py`), and document how to run them when test tooling is added.

## Commit & Pull Request Guidelines

No Git commits are available to establish a commit-message convention. Use short, imperative commit subjects (for example, `Add job source parser`) until the project adopts a documented standard. Pull requests should explain the change and its motivation, list validation performed, link related issues when applicable, and include screenshots for user-visible changes.

## Security & Configuration

Keep credentials and machine-specific settings out of version control. Provide safe example configuration with placeholders and document required environment variables when the application introduces them.
