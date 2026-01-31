import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VendorFile(Base):
    __tablename__ = "vendor_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    object_key = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="uploaded")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class VendorContract(Base):
    __tablename__ = "vendor_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_file_id = Column(UUID(as_uuid=True), ForeignKey("vendor_files.id"), nullable=False)
    contract_number = Column(String, nullable=False)
    vendor_name = Column(String, nullable=False)
    effective_start = Column(DateTime(timezone=True))
    effective_end = Column(DateTime(timezone=True))
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VendorContractLine(Base):
    __tablename__ = "vendor_contract_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_contract_id = Column(
        UUID(as_uuid=True), ForeignKey("vendor_contracts.id"), nullable=False
    )
    vendor_item_number = Column(String, nullable=False)
    vendor_uom = Column(String, nullable=False)
    vendor_description = Column(Text)
    contract_price = Column(Numeric(18, 4), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    effective_start = Column(DateTime(timezone=True))
    effective_end = Column(DateTime(timezone=True))
    raw_payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_contract_id = Column(
        UUID(as_uuid=True), ForeignKey("vendor_contracts.id"), nullable=False
    )
    run_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReconciliationException(Base):
    __tablename__ = "reconciliation_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    reconciliation_run_id = Column(
        UUID(as_uuid=True), ForeignKey("reconciliation_runs.id"), nullable=False
    )
    vendor_contract_line_id = Column(
        UUID(as_uuid=True), ForeignKey("vendor_contract_lines.id"), nullable=False
    )
    rule_code = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    message = Column(Text, nullable=False)
    context = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
