"""Compatibility entrypoint for local development commands.

Keeps `uvicorn main:app --reload` pointed at the StudyMate FastAPI app when
run from the `backend/` directory.
"""

from app.main import app
