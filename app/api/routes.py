from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import get_db, get_tenant_id
from app.db import models
from app.jobs.reconciliation import create_reconciliation_run
from app.storage.files import save_upload

router = APIRouter()


@router.post("/tenants", response_model=schemas.TenantRead)
def create_tenant(payload: schemas.TenantCreate, db: Session = Depends(get_db)):
    tenant = models.Tenant(name=payload.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/tenants/{tenant_id}", response_model=schemas.TenantRead)
def get_tenant(tenant_id: UUID, db: Session = Depends(get_db)):
    tenant = db.get(models.Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/vendor-files/upload", response_model=schemas.VendorFileRead)
def upload_vendor_file(
    vendor_name: str,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    object_key = save_upload(file)
    file_type = Path(file.filename).suffix.lstrip(".")
    vendor_file = models.VendorFile(
        tenant_id=tenant_id,
        vendor_name=vendor_name,
        filename=file.filename,
        object_key=object_key,
        file_type=file_type,
        status="uploaded",
    )
    db.add(vendor_file)
    db.commit()
    db.refresh(vendor_file)
    return vendor_file


@router.get("/vendor-files", response_model=list[schemas.VendorFileRead])
def list_vendor_files(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(models.VendorFile).filter_by(tenant_id=tenant_id).all()


@router.post("/vendor-contracts", response_model=schemas.VendorContractRead)
def create_vendor_contract(
    payload: schemas.VendorContractCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    contract = models.VendorContract(
        tenant_id=tenant_id,
        vendor_file_id=payload.vendor_file_id,
        contract_number=payload.contract_number,
        vendor_name=payload.vendor_name,
        status="active",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/vendor-contracts", response_model=list[schemas.VendorContractRead])
def list_vendor_contracts(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(models.VendorContract).filter_by(tenant_id=tenant_id).all()


@router.post("/vendor-contract-lines", response_model=schemas.VendorContractLineRead)
def create_vendor_contract_line(
    payload: schemas.VendorContractLineCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    contract = db.get(models.VendorContract, payload.vendor_contract_id)
    if not contract or contract.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Contract not found")
    line = models.VendorContractLine(
        tenant_id=tenant_id,
        vendor_contract_id=payload.vendor_contract_id,
        vendor_item_number=payload.vendor_item_number,
        vendor_uom=payload.vendor_uom,
        vendor_description=payload.vendor_description,
        contract_price=payload.contract_price,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.post("/reconciliation-runs", response_model=schemas.ReconciliationRunRead)
def run_reconciliation(
    payload: schemas.ReconciliationRunCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    run = create_reconciliation_run(db, tenant_id, payload.vendor_contract_id, payload.run_type)
    db.refresh(run)
    return run


@router.get("/reconciliation-runs", response_model=list[schemas.ReconciliationRunRead])
def list_reconciliation_runs(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(models.ReconciliationRun).filter_by(tenant_id=tenant_id).all()


@router.get("/exceptions", response_model=list[schemas.ReconciliationExceptionRead])
def list_exceptions(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(models.ReconciliationException).filter_by(tenant_id=tenant_id).all()


@router.patch("/exceptions/{exception_id}", response_model=schemas.ReconciliationExceptionRead)
def update_exception(
    exception_id: UUID,
    payload: schemas.ExceptionStatusUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    exception = db.get(models.ReconciliationException, exception_id)
    if not exception or exception.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    exception.status = payload.status
    if payload.message:
        exception.message = payload.message
    db.commit()
    db.refresh(exception)
    return exception
