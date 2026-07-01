# Contributing to Kannada RAG Agent

Thank you for your interest in the Kannada RAG Agent project! This is currently a solo-maintained repository, but I'm always open to feedback, bug reports, and suggestions.

## How Can I Contribute?

### Reporting Bugs
If you find a bug, please check the existing GitHub Issues first. 
- If you're unable to find an open issue addressing the problem, open a new one. 
- Be sure to include a clear description, as much relevant information as possible, and a code sample or steps demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements
- Open a new issue with the `enhancement` label.
- Provide a clear and detailed explanation of the feature.
- Explain why this enhancement would be useful.

### Pull Requests
Since I maintain this project solo, I greatly appreciate pull requests that fix bugs or add value.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests to the `scripts/eval/` directory.
3. Ensure the test suite passes (`python scripts/eval/eval_ragas.py`).
4. Make sure your code is clean and follows standard Python conventions (PEP 8).
5. Submit the pull request!

## Architecture Guidelines
Please review the `docs/architecture.md` file before proposing any major changes to the Retrieval pipeline or LLM routing logic. The project maintains strict latency and memory thresholds (see `docs/benchmarks.md`).
