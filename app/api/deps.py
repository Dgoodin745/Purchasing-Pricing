from typing import Generator
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_id(x_tenant_id: str = Header(...)) -> UUID:
    try:
        return UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID") from exc
