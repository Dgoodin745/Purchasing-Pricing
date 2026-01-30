# ContractSync MVP (Working Skeleton)

This repo contains a minimal working FastAPI-based skeleton for the ContractSync MVP. It includes a Postgres-backed API, basic multi-tenant scoping via `X-Tenant-ID`, vendor file uploads to local storage, and a stub reconciliation flow that emits a sample exception.

## Quick start (Docker)
```
docker-compose up --build
```

API available at: `http://localhost:8000`

## Sample flow
1. Create a tenant:
```
curl -X POST http://localhost:8000/api/v1/tenants \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme"}'
```
2. Upload a vendor file:
```
curl -X POST "http://localhost:8000/api/v1/vendor-files/upload?vendor_name=Acme" \
  -H "X-Tenant-ID: <tenant_id>" \
  -F "file=@sample.csv"
```
3. Create a vendor contract:
```
curl -X POST http://localhost:8000/api/v1/vendor-contracts \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: <tenant_id>" \
  -d '{"vendor_file_id":"<file_id>","contract_number":"C-001","vendor_name":"Acme"}'
```
4. Trigger reconciliation:
```
curl -X POST http://localhost:8000/api/v1/reconciliation-runs \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: <tenant_id>" \
  -d '{"vendor_contract_id":"<contract_id>","run_type":"manual"}'
```
5. Fetch exceptions:
```
curl -X GET http://localhost:8000/api/v1/exceptions \
  -H "X-Tenant-ID: <tenant_id>"
```

## Notes
- Database tables are created automatically on startup for this skeleton.
- This is an MVP scaffold and does not yet implement Prophet 21 OData, RBAC, or workflow UI.
