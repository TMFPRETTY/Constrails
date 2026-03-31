# Contributing

Thanks for your interest in contributing to Constrails.

## Development setup

```bash
git clone https://github.com/TMFPRETTY/Constrails.git
cd Constrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

Run tests:

```bash
.venv/bin/python -m pytest -q tests
```

## Contribution guidelines

Please prefer:
- small, focused pull requests
- clear commit messages
- updated tests when behavior changes
- updated docs when operator/developer workflows change

## Areas especially worth improving

- policy-as-code coverage
- auth hardening
- sandbox hardening
- deployment ergonomics
- observability and audit tooling

## Reporting bugs

Please include:
- expected behavior
- actual behavior
- reproduction steps
- relevant logs or screenshots
- environment details

## Security-sensitive issues

If the issue relates to sandbox escapes, approval bypass, policy bypass, capability escalation, or audit tampering, prefer private disclosure over a detailed public report.
