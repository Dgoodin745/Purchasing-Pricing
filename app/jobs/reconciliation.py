from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import models


def create_reconciliation_run(
    db: Session, tenant_id: UUID, vendor_contract_id: UUID, run_type: str
) -> models.ReconciliationRun:
    run = models.ReconciliationRun(
        tenant_id=tenant_id,
        vendor_contract_id=vendor_contract_id,
        run_type=run_type,
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()

    line = (
        db.query(models.VendorContractLine)
        .filter_by(tenant_id=tenant_id, vendor_contract_id=vendor_contract_id)
        .first()
    )
    if line:
        exception = models.ReconciliationException(
            tenant_id=tenant_id,
            reconciliation_run_id=run.id,
            vendor_contract_line_id=line.id,
            rule_code="PRICE_MISMATCH",
            severity="high",
            status="open",
            message="Contract price does not match P21 price (stubbed).",
            context={"contract_price": str(line.contract_price)},
        )
        db.add(exception)

    db.commit()
    return run
