from fastapi import FastAPI

from app.api import routes
from app.db.session import Base, engine

app = FastAPI(title="ContractSync MVP", version="0.1.0")

Base.metadata.create_all(bind=engine)

app.include_router(routes.router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
