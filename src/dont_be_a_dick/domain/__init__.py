"""Pure domain layer: schemas, rubrics, ports and scoring.

Nothing in this package may import a framework (langchain, tavily, fastapi) or
any other layer of the project. `tests/test_architecture.py` enforces that.
"""
