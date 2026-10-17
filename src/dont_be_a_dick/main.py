from fastapi import FastAPI

from dont_be_a_dick.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/dick-score")
def dick_score(name: str) -> None:
    raise NotImplementedError()
