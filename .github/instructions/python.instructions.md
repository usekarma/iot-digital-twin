---
description: Python implementation and test conventions for this repository.
applyTo: "**/*.py"
---

- Target Python 3.12+.
- Add type hints to public functions and methods.
- Prefer pure domain logic and dependency injection.
- Keep network, filesystem, database, and cloud calls behind interfaces where practical.
- Use pytest for tests.
- Prefer deterministic tests; mock only external boundaries.
- Do not catch `Exception` unless adding meaningful context and re-raising or deliberately translating it.
- Do not use mutable default arguments.
- Avoid hidden global state.
