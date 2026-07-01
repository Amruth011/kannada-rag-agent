# Contributing to Kannada RAG Agent

First off, thank you for considering contributing to the Kannada RAG Agent project! It's people like you that make the open-source AI community such a fantastic place to learn, inspire, and create.

## How Can I Contribute?

### Reporting Bugs
This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.
- Ensure the bug was not already reported by searching on GitHub under Issues.
- If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements
This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.
- Open a new issue with the `enhancement` label.
- Provide a clear and detailed explanation of the feature.
- Explain why this enhancement would be useful to most users.

### Pull Requests
The process described here has several goals:
- Maintain Kannada RAG Agent's quality.
- Fix problems that are important to users.
- Engage the community in working toward the best possible product.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests to the `scripts/eval/` directory.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes (`python scripts/eval/eval_ragas.py`).
5. Make sure your code lints.
6. Issue that pull request!

## Code Style
- **Python**: Follow PEP 8 guidelines. Use Black for formatting.
- **Markdown**: Ensure your documentation changes are clear, concise, and spell-checked.

## Architecture Guidelines
Please review the `docs/architecture.md` file before proposing any major changes to the Retrieval pipeline or LLM routing logic. We maintain strict latency and memory thresholds (see `docs/benchmarks.md`).
