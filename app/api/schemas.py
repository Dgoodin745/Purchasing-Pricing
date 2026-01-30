from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str


class TenantRead(BaseModel):
    id: UUID
    name: str
    status: str
    created_at: datetime


class VendorFileRead(BaseModel):
    id: UUID
    vendor_name: str
    filename: str
    object_key: str
    file_type: str
    status: str
    uploaded_at: datetime


class VendorContractCreate(BaseModel):
    vendor_file_id: UUID
    contract_number: str
    vendor_name: str


class VendorContractRead(BaseModel):
    id: UUID
    vendor_file_id: UUID
    contract_number: str
    vendor_name: str
    status: str


class ReconciliationRunCreate(BaseModel):
    vendor_contract_id: UUID
    run_type: str = Field(default="manual")


class ReconciliationRunRead(BaseModel):
    id: UUID
    vendor_contract_id: UUID
    run_type: str
    status: str
    created_at: datetime


class ReconciliationExceptionRead(BaseModel):
    id: UUID
    reconciliation_run_id: UUID
    vendor_contract_line_id: UUID
    rule_code: str
    severity: str
    status: str
    message: str
    created_at: datetime


class ExceptionStatusUpdate(BaseModel):
    status: str
    message: Optional[str] = None
