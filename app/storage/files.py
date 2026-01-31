import os
import uuid
from pathlib import Path

from fastapi import UploadFile


def save_upload(file: UploadFile) -> str:
    storage_root = Path(os.getenv("STORAGE_ROOT", "./storage"))
    storage_root.mkdir(parents=True, exist_ok=True)
    object_key = f"{uuid.uuid4()}-{file.filename}"
    destination = storage_root / object_key
    with destination.open("wb") as buffer:
        buffer.write(file.file.read())
    return object_key
