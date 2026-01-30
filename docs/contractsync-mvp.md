# ContractSync MVP Blueprint

## Working skeleton implementation
- **FastAPI API**: `app/main.py` provides a running API with tenant-scoped endpoints for tenants, vendor files, contracts, and reconciliation runs.
- **Postgres storage**: SQLAlchemy models in `app/db/models.py` auto-create tables on startup.
- **Local object storage**: uploads are saved under `STORAGE_ROOT` via `app/storage/files.py`.
- **Stub reconciliation job**: `app/jobs/reconciliation.py` generates a sample exception to demonstrate the workflow.
- **Docker compose**: `docker-compose.yml` boots API + Postgres for local development.

## 1) Repository structure
```
contractsync/
├── cmd/
│   ├── api/                     # REST API service (multi-tenant)
│   ├── worker/                  # background jobs + schedulers
│   └── agent/                   # optional on-prem connector agent
├── internal/
│   ├── auth/                    # RBAC, tenant context, JWT/OIDC
│   ├── connectors/
│   │   ├── odata/                # Prophet 21 OData client
│   │   ├── files/                # CSV/XLSX ingestion
│   │   └── registry/             # auth modes + connector registry
│   ├── domain/
│   │   ├── contracts/            # contracts, price lines, UOMs
│   │   ├── items/                # mapping vendor item <-> P21 item
│   │   ├── reconciliation/       # rules + exception generation
│   │   └── workflow/             # exception resolution flow
│   ├── jobs/                     # queue processors + schedules
│   ├── storage/                  # object storage adapters
│   ├── audit/                    # audit log writer
│   ├── tenancy/                  # row-level tenant isolation helpers
│   └── http/                     # routing, middleware, handlers
├── migrations/                   # DB migrations (Postgres)
├── pkg/
│   ├── api/                      # API request/response types
│   └── types/                    # shared domain types
├── web/
│   ├── app/                      # UI pages + components
│   └── public/
├── infra/
│   ├── docker/                   # local dev compose
│   ├── helm/                     # k8s charts
│   └── terraform/                # cloud infra
└── docs/
    ├── architecture.md
    ├── api.md
    ├── data-model.md
    └── runbooks.md
```

## 2) DB schema (tables + key fields + indexes)
```sql
-- Tenancy + auth
CREATE TABLE tenants (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  email CITEXT NOT NULL,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
CREATE INDEX users_tenant_id_idx ON users(tenant_id);

CREATE TABLE roles (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name TEXT NOT NULL,
  description TEXT,
  UNIQUE (tenant_id, name)
);
CREATE INDEX roles_tenant_id_idx ON roles(tenant_id);

CREATE TABLE user_roles (
  user_id UUID NOT NULL REFERENCES users(id),
  role_id UUID NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);

-- Connector configs
CREATE TABLE connectors (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name TEXT NOT NULL,
  provider TEXT NOT NULL, -- prophet21
  auth_mode TEXT NOT NULL, -- oauth, api_key, basic, agent
  config JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, name)
);
CREATE INDEX connectors_tenant_id_idx ON connectors(tenant_id);

CREATE TABLE connector_tokens (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  connector_id UUID NOT NULL REFERENCES connectors(id),
  token_encrypted BYTEA NOT NULL,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX connector_tokens_connector_id_idx ON connector_tokens(connector_id);

-- File ingestion
CREATE TABLE vendor_files (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  connector_id UUID REFERENCES connectors(id),
  vendor_name TEXT NOT NULL,
  filename TEXT NOT NULL,
  object_key TEXT NOT NULL,
  file_type TEXT NOT NULL, -- csv/xlsx
  status TEXT NOT NULL DEFAULT 'uploaded',
  uploaded_by UUID REFERENCES users(id),
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX vendor_files_tenant_id_idx ON vendor_files(tenant_id);
CREATE INDEX vendor_files_status_idx ON vendor_files(status);

CREATE TABLE vendor_contracts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  vendor_file_id UUID NOT NULL REFERENCES vendor_files(id),
  contract_number TEXT NOT NULL,
  vendor_name TEXT NOT NULL,
  effective_start DATE,
  effective_end DATE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX vendor_contracts_tenant_id_idx ON vendor_contracts(tenant_id);

CREATE TABLE vendor_contract_lines (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  vendor_contract_id UUID NOT NULL REFERENCES vendor_contracts(id),
  vendor_item_number TEXT NOT NULL,
  vendor_uom TEXT NOT NULL,
  vendor_description TEXT,
  contract_price NUMERIC(18, 4) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  effective_start DATE,
  effective_end DATE,
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX vendor_contract_lines_contract_idx ON vendor_contract_lines(vendor_contract_id);
CREATE INDEX vendor_contract_lines_tenant_id_idx ON vendor_contract_lines(tenant_id);

-- P21 item + UOM mapping
CREATE TABLE p21_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  p21_item_id TEXT NOT NULL,
  item_number TEXT NOT NULL,
  description TEXT,
  default_uom TEXT,
  last_synced_at TIMESTAMPTZ,
  UNIQUE (tenant_id, p21_item_id)
);
CREATE INDEX p21_items_tenant_id_idx ON p21_items(tenant_id);

CREATE TABLE vendor_item_mappings (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  vendor_item_number TEXT NOT NULL,
  vendor_uom TEXT NOT NULL,
  p21_item_id UUID NOT NULL REFERENCES p21_items(id),
  p21_uom TEXT NOT NULL,
  confidence_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active',
  UNIQUE (tenant_id, vendor_item_number, vendor_uom)
);
CREATE INDEX vendor_item_mappings_tenant_id_idx ON vendor_item_mappings(tenant_id);

-- Reconciliation
CREATE TABLE reconciliation_runs (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  vendor_contract_id UUID NOT NULL REFERENCES vendor_contracts(id),
  run_type TEXT NOT NULL, -- scheduled/manual
  status TEXT NOT NULL DEFAULT 'queued',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX reconciliation_runs_tenant_id_idx ON reconciliation_runs(tenant_id);

CREATE TABLE reconciliation_exceptions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  reconciliation_run_id UUID NOT NULL REFERENCES reconciliation_runs(id),
  vendor_contract_line_id UUID NOT NULL REFERENCES vendor_contract_lines(id),
  p21_item_id UUID REFERENCES p21_items(id),
  rule_code TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  message TEXT NOT NULL,
  context JSONB,
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX reconciliation_exceptions_tenant_id_idx ON reconciliation_exceptions(tenant_id);
CREATE INDEX reconciliation_exceptions_status_idx ON reconciliation_exceptions(status);

-- Workflow + audit
CREATE TABLE workflow_actions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  exception_id UUID NOT NULL REFERENCES reconciliation_exceptions(id),
  action_type TEXT NOT NULL, -- comment/resolve/reassign/override
  action_payload JSONB,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX workflow_actions_exception_id_idx ON workflow_actions(exception_id);

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  actor_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  diff JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_logs_tenant_id_idx ON audit_logs(tenant_id);
CREATE INDEX audit_logs_entity_idx ON audit_logs(entity_type, entity_id);
```

## 3) API endpoints (REST)
- **Auth & tenancy**
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/tenants/:tenantId`
  - `POST /api/v1/tenants`
- **Users & roles**
  - `GET /api/v1/users`
  - `POST /api/v1/users`
  - `GET /api/v1/roles`
  - `POST /api/v1/roles`
  - `POST /api/v1/users/:userId/roles`
- **Connectors**
  - `GET /api/v1/connectors`
  - `POST /api/v1/connectors`
  - `POST /api/v1/connectors/:id/test`
  - `POST /api/v1/connectors/:id/sync/p21-items`
- **Contracts & files**
  - `POST /api/v1/vendor-files/upload`
  - `GET /api/v1/vendor-files`
  - `GET /api/v1/vendor-contracts`
  - `GET /api/v1/vendor-contracts/:id`
- **Mappings**
  - `GET /api/v1/item-mappings`
  - `POST /api/v1/item-mappings`
  - `PATCH /api/v1/item-mappings/:id`
- **Reconciliation**
  - `POST /api/v1/reconciliation-runs`
  - `GET /api/v1/reconciliation-runs`
  - `GET /api/v1/reconciliation-runs/:id`
  - `GET /api/v1/exceptions`
  - `PATCH /api/v1/exceptions/:id`
- **Workflow**
  - `POST /api/v1/exceptions/:id/actions`
  - `GET /api/v1/exceptions/:id/actions`
- **Audit**
  - `GET /api/v1/audit-logs`

## 4) Background jobs and scheduling approach
- **Job runner**: Dedicated worker service, backed by a queue (e.g., PostgreSQL + advisory locks, or Redis-based queue). Each job is tenant-scoped.
- **Schedules**
  - `sync_p21_items`: nightly per connector, or on-demand.
  - `ingest_vendor_file`: triggered after upload; parses CSV/XLSX, normalizes, stores lines.
  - `map_vendor_items`: on ingestion completion; suggests mappings and flags unmapped.
  - `reconcile_contract`: on schedule or manual trigger; generates exceptions.
  - `audit_retention`: weekly cleanup.

## 5) UI page list + component outline
- **Login**
  - Components: `LoginForm`, `SSOButton`, `TenantSelector`.
- **Dashboard**
  - Components: `KPIStats`, `ExceptionsByStatusChart`, `RecentRunsTable`.
- **Connectors**
  - Components: `ConnectorList`, `ConnectorForm`, `ConnectorAuthModePicker`, `ConnectionTestModal`.
- **Vendor Files**
  - Components: `FileUpload`, `FileIngestionStatus`, `ContractTable`.
- **Item Mapping**
  - Components: `MappingTable`, `MappingEditor`, `MatchSuggestions`, `BulkApproveBar`.
- **Reconciliation Runs**
  - Components: `RunsTable`, `RunDetailPanel`, `RunActionMenu`.
- **Exceptions Queue**
  - Components: `ExceptionsTable`, `FilterBar`, `ExceptionDetailDrawer`, `ResolutionForm`.
- **Audit Log**
  - Components: `AuditLogTable`, `AuditFilterBar`.
- **Settings**
  - Components: `TenantProfile`, `RoleManager`, `FeatureFlagList`.

## 6) Reconciliation rule engine design + pseudocode
**Rule engine design**
- **Inputs**: vendor contract line, mapped P21 item record, current P21 price/UOM, effective dates, tenant policy.
- **Rules**:
  - `MISSING_MAPPING`: no P21 mapping exists.
  - `UOM_MISMATCH`: vendor UOM differs from P21 UOM.
  - `PRICE_MISMATCH`: contract price differs from P21 price above tolerance.
  - `EXPIRED_CONTRACT`: contract line outside effective dates.
  - `INACTIVE_ITEM`: P21 item inactive.
- **Outputs**: exception records with severity + suggested actions.

**Pseudocode**
```
for contract_line in contract_lines:
    mapping = mapping_store.get(contract_line.vendor_item_number, contract_line.vendor_uom)

    if not mapping:
        emit_exception("MISSING_MAPPING", severity="high")
        continue

    p21_item = p21_client.get_item(mapping.p21_item_id)
    p21_price = p21_client.get_price(p21_item, mapping.p21_uom)

    if contract_line.vendor_uom != mapping.p21_uom:
        emit_exception("UOM_MISMATCH", severity="medium")

    if abs(contract_line.contract_price - p21_price) > tenant_policy.price_tolerance:
        emit_exception("PRICE_MISMATCH", severity="high")

    if contract_line.effective_end and contract_line.effective_end < today():
        emit_exception("EXPIRED_CONTRACT", severity="low")

    if p21_item.status != "active":
        emit_exception("INACTIVE_ITEM", severity="medium")
```

## 7) Testing plan and sample test fixtures
- **Unit tests**
  - CSV/XLSX normalization: fixtures for vendor samples.
  - Rule engine: contract line inputs to validate exception outputs.
- **Integration tests**
  - OData connector mock server: validate P21 pulls.
  - Background jobs: end-to-end reconciliation run using a seeded tenant.
- **API tests**
  - Auth/RBAC: permissions checks for exceptions.
  - Multi-tenant isolation: ensure tenant scoping on all endpoints.

**Sample fixtures**
- `fixtures/vendor_contracts/sample_vendor_contract.csv`
- `fixtures/p21/odata_items.json`
- `fixtures/reconciliation/price_mismatch_case.json`

## 8) Deployment plan (dev/stage/prod)
- **Dev**: Docker Compose with Postgres, MinIO, local worker, and mocked P21 OData service.
- **Stage**: Kubernetes (single region), managed Postgres, object storage, feature flags enabled for writeback.
- **Prod**: Kubernetes (multi-AZ), managed Postgres with PITR, object storage, secrets via Vault or cloud KMS, on-prem agent deployment option.

## Architecture diagram (text)
```
[Vendor CSV/XLSX] -> [Upload API] -> [Object Storage]
                          |                |
                          v                v
                    [Ingestion Job] -> [Normalized Contract Lines]
                          |
                          v
[P21 OData] -> [Connector Service] -> [P21 Item Cache]
                          |
                          v
                   [Reconciliation Job]
                          |
                          v
                   [Exceptions DB]
                          |
                          v
                  [Workflow UI/API]
```

## Service interfaces (high-level)
- **ConnectorRegistry**
  - `Register(provider, authModes)`
  - `TestConnection(connectorId)`
  - `FetchItems(connectorId, sinceTimestamp)`
- **IngestionService**
  - `ParseFile(fileId)`
  - `NormalizeLines(fileId)`
  - `CreateContracts(fileId)`
- **MappingService**
  - `SuggestMappings(contractId)`
  - `UpsertMapping(vendorItem, vendorUom, p21Item, p21Uom)`
- **ReconciliationService**
  - `Run(contractId, options)`
  - `ListExceptions(filters)`
  - `ResolveException(exceptionId, resolution)`
- **WorkflowService**
  - `CreateAction(exceptionId, actionType, payload)`
  - `ListActions(exceptionId)`
```

## MVP backlog
1. **Tenant + auth**: JWT auth, tenant scoping middleware, RBAC model.
2. **Connector config**: CRUD + test for P21 OData.
3. **File ingestion**: upload API, object storage integration, CSV/XLSX parser.
4. **Normalization pipeline**: map vendor columns to canonical schema.
5. **P21 sync**: item cache via OData pull.
6. **Item mapping UI**: manual mapping + suggested mappings.
7. **Reconciliation engine**: rule runner + exception generation.
8. **Exceptions workflow UI**: queue, detail view, resolve action.
9. **Audit logs**: capture data changes and workflow actions.
10. **Feature flags**: writeback and advanced rules.
