# Contributing to IsMyPwdSafe

Thank you for considering contributing to IsMyPwdSafe! 

## Development Setup

To get started with local development, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/IsMyPwdSafe.git
   cd IsMyPwdSafe
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install the package in editable mode with development dependencies:**
   ```bash
   pip install -e ".[test,dev]"
   ```

## Running Tests and Linters

Before submitting a pull request, make sure everything passes:

```bash
# Run the test suite (must pass offline)
python -m pytest -v

# Run the linter
python -m ruff check .

# Run the type checker
python -m mypy ismypwdsafe/core.py ismypwdsafe/patterns.py
```

## Pull Request Guidelines

- Keep commits atomic and use conventional commit messages (e.g., `feat:`, `fix:`, `docs:`).
- Ensure the CI passes on all platforms (Windows, macOS, Linux).
- If you are adding a new feature, please add tests for it.
- If you change the engine's scoring or pattern detection, you will need to update the golden scores by running `python scripts/generate_golden.py`.