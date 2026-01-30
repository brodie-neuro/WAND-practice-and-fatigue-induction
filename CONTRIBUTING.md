# Contributing to WAND

Thank you for your interest in contributing to WAND. This document provides guidelines for contributions.

## Reporting Bugs

If you encounter a bug, please report it via [GitHub Issues](https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction/issues).

When reporting a bug, please include:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected behaviour vs. actual behaviour
- Your Python version and operating system
- Any error messages or logs (from `data/participant_*_log.txt`)

## Requesting Features

Feature requests are welcome. Please open a [GitHub Issue](https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction/issues) with the label `enhancement` and describe:

- The problem your feature would solve
- Your proposed solution
- Any alternatives you have considered

## Submitting Pull Requests

I welcome pull requests for bug fixes, documentation improvements, and new features.

### Workflow

1. **Fork** the repository
2. **Create a branch** from `main` for your changes
3. **Make your changes** following the code style guidelines below
4. **Add tests** if you are adding new functionality
5. **Run the test suite** to ensure all tests pass:
   ```bash
   python -m pytest
   ```
6. **Submit a pull request** with a clear description of your changes

### Code Style

- Use [Black](https://github.com/psf/black) for Python formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use UK English spelling in documentation and comments
- Follow PEP 8 conventions
- Add docstrings to new functions and classes

You can run the linters locally before submitting:
```bash
isort .
black .
```

## Seeking Support

For questions about using WAND in your research:

- Check the [README](README.md) documentation first
- Search existing [GitHub Issues](https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction/issues) for similar questions
- Open a new issue with the label `question` if you need further assistance

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE.txt).
