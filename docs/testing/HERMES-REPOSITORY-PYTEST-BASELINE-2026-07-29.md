# Hermes Repository Pytest Baseline - 2026-07-29

This engineering baseline tracks repo-wide validation debt separately from the
Executive Planning Engine milestone.

Known baseline before this milestone:

- Focused Orchestrator, Reasoning, Intelligence, deployment and trace tests
  pass in the project `.venv`.
- A current repo-wide pytest attempt using
  `.venv/bin/python -m pytest -q --maxfail=20` was interrupted after reaching
  roughly 6% of the suite. Unrelated failures were visible before interruption,
  outside the touched planning path, and no focused planning failure was
  observed.
- Repo-wide `ruff format --check .` has pre-existing formatting debt,
  especially in large legacy modules such as `hermes_cli/main.py`.

Rule for this milestone:

- No new failures are allowed in touched areas.
- Full-suite failures outside touched areas must be recorded, not silently
  fixed through unrelated cleanup.
