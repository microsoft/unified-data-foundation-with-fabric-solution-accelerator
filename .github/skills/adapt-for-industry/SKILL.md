---
name: adapt-for-industry
description: Adapt Unified Data Foundation with Fabric for a target industry by mapping entities, producing synthetic data packs, updating Fabric notebooks, Data Agent and report terminology, and preparing safe activation.
---

# Adapt for Industry — Unified Data Foundation with Fabric

## Context

Unified Data Foundation with Fabric currently demonstrates shared customer/product, finance, and sales analytics. Industry adaptation changes the sample data, schema/table mappings, Fabric transformation notebooks, Data Agent prompts/examples, and Power BI report terminology while preserving stable Fabric contract keys unless an intentional migration is documented and validated.

Adapting this accelerator for a new industry means coordinating:

- Entity mappings from customer/product/order/invoice/payment/location to target-industry equivalents.
- Synthetic CSV samples for Fabric, and optionally Databricks or Snowflake source paths.
- Schema and transformation notebooks under `src/fabric/notebooks/` and optional Databricks notebooks.
- Data Agent instructions, selected-table metadata, datasource descriptions, and few-shot examples.
- Power BI report labels, semantic field bindings, and smoke checks.
- Fabric deployment parameterization and safe azd/postprovision activation.

## Step 1: Read Existing Data Patterns

Read these files before designing the industry pack:

- `infra/data/samples_fabric/shared/*.csv`, `finance/*.csv`, and `sales/*.csv`.
- `infra/data/samples_databricks/sales/*.csv` and `infra/data/samples_snowflake/sales/*.csv` if cross-source adaptation is requested.
- `src/fabric/notebooks/schema/model_shared_silver.ipynb`, `model_finance_gold.ipynb`, `model_salesfabric_gold.ipynb`, and related bronze/silver/gold notebooks.
- `src/databricks/notebooks/` when the target industry needs Databricks examples.
- `fabric_workspace/parameter.yml` for lakehouse, semantic model, and Data Agent reference replacement.
- `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json`, `datasource.json`, and `fewshots.json`.
- `fabric_workspace/reports/sales_dashboard.Report/report.json` and `reports/theme.json`.
- `.github/sa-analysis/architecture-survey.md` and `.github/sa-analysis/fy27-evaluation.md`.

Study required/optional columns, foreign-key relationships, schema names, report queryRefs, Data Agent SQL examples, and where user-facing terminology appears.

## Step 2: Identify Target Industry

Ask the user:

1. **Target industry and sub-domain:** Healthcare, Financial Services, Manufacturing, Energy & Utilities, Public Sector, Legal, Education, or another vertical.
2. **Core business entities:** Which source entities replace or extend Customer, Product, Order, Invoice, Payment, Location, and Relationship Type?
3. **Source coverage:** Fabric only, or also Databricks/Snowflake sample paths?
4. **Compliance constraints:** HIPAA/HL7/FHIR, SOX/PCI/KYC/AML, ISO/OSHA/FDA/FAA, NERC CIP, FedRAMP/FISMA/508, FERPA, legal privilege, or other requirements.
5. **Synthetic data volume:** Generate 10-20 rows per entity unless the user requests a different demo size.
6. **Report and Data Agent wording:** Which report titles, visual labels, Data Agent instructions, and few-shot questions should reflect the target industry?
7. **Activation scope:** Is this a staging-only pack, or should existing sample/demo lakehouse data be replaced after validation through `deploy-adaptation`?

## Step 3: Design Industry Data Pack

### 3.0 Pre-write check

Do not overwrite native sample files without explicit confirmation. Prefer a sibling staging path first:

```text
infra/data/industry_packs/<industry>/
├── SCHEMA_MAPPING.md
├── DATA_SWAP_GUIDE.md
├── samples_fabric/<domain>/*.csv
├── samples_databricks/<domain>/*.csv        # optional
├── samples_snowflake/<domain>/*.csv         # optional
├── notebooks/CHANGE_PLAN.md
├── data_agent/CHANGE_PLAN.md
└── reports/CHANGE_PLAN.md
```

This staging path is for planning and review. Actual runtime loading still requires intentional integration with the native sample paths, notebooks, or Fabric install hook.

### 3.1 Schema mapping

Create `SCHEMA_MAPPING.md` with a table like:

| Current entity | Industry entity | Required changes | Sensitive fields |
|---|---|---|---|
| Customer | Patient / Account / Student / Supplier | Add industry identifiers and demographics as needed | PHI/PII/financial/education/legal privilege flags |
| Product | Procedure / Policy / Course / Part | Add industry taxonomy and status fields | Regulated code sets or proprietary catalog values |
| Order / Invoice / Payment | Encounter / Claim / Transaction / Work Order | Preserve fact/dimension relationships and date/currency semantics | Payment, diagnosis, account, or operational risk data |

Every current core entity must map to an industry equivalent, be explicitly retired, or be replaced by a validated new contract.

### 3.2 Synthetic datasets

Generate 10-20 fully synthetic rows per entity with realistic relationships and edge cases. Keep IDs fake, dates logical, foreign keys consistent, and compliance-sensitive fields clearly synthetic. Use native CSV naming conventions when staging replacements for `infra/data/samples_fabric`, `samples_databricks`, or `samples_snowflake`.

### 3.3 Fabric artifact changes

Plan notebook/report/Data Agent changes that make the industry pack usable:

- Schema notebooks for new or renamed tables.
- Bronze-to-silver and silver-to-gold transformations for each source in scope.
- Data management and row-count checks for safe validation.
- Data Agent datasource metadata, instructions, few-shot questions, and selected-table descriptions.
- Power BI report titles, visual labels, semantic-model field references, and optional theme/branding updates.
- `fabric_workspace/parameter.yml` replacements for any new workspace item references.

### 3.4 UI surface updates

Use the surveyed Fabric UI surfaces in this order:

- [ ] Update report labels/copy and Data Agent prompt/example wording for target-industry terminology.
- [ ] Update visual titles, page titles, field labels, and example questions while preserving stable Fabric schema/table/column keys unless a contract migration is intentional.
- [ ] Review `datasource.json`, semantic model bindings, and report queryRefs as contract-supporting surfaces.
- [ ] Update report theme/branding only when requested.
- [ ] Record smoke checks: report opens with target-industry labels, a representative visual renders, Data Agent answers a target-industry few-shot, and stable contract keys remain available.

## Step 4: Create Data Swap Guide

Write `DATA_SWAP_GUIDE.md` in the industry pack with:

1. Prerequisites and source coverage.
2. Data format specification by entity/file.
3. Mapping instructions from current entities to target-industry entities.
4. UI/report/Data Agent terminology checklist.
5. Validation instructions pointing to Step C and `.github/skills/adapt-for-industry/validate.py`.
6. Activation handoff identifying any sample/demo reset, native sample path replacement, postprovision hook rerun, lakehouse table reload, or report redeployment needed.

`DATA_SWAP_GUIDE.md` is planning and data-format guidance only. Do not include destructive commands, cloud-mutating commands, table drops/truncates, data reload commands, postprovision hook reruns, Search/index/cache resets, or workspace teardown. Route those through `deploy-adaptation`.

## Compliance Quick Sheet

| Industry | Key requirements to acknowledge | Data handling notes |
|---|---|---|
| Healthcare | HIPAA, HITECH, HL7/FHIR | No real PHI; use synthetic patient/provider/encounter data. |
| Financial Services | SOX, PCI-DSS, KYC/AML | Use fake account/card identifiers; preserve audit and transaction lineage. |
| Manufacturing | ISO 9001, OSHA, FDA/FAA where relevant | Preserve traceability, work-order, BOM, and quality-event relationships. |
| Energy & Utilities | NERC CIP, EPA, FERC | Separate operational and customer data; avoid critical infrastructure details. |
| Public Sector | FedRAMP, FISMA, Section 508 | Respect data sovereignty, accessibility, and audit expectations. |
| Legal | eDiscovery, privilege, bar rules | Avoid real matters/names; track privilege and chain-of-custody flags. |
| Education | FERPA, LMS integration norms | Use synthetic student/course/enrollment data only. |

## Step C: Validate

From the SA repo root, run the validator generated with this skill:

```bash
python .github/skills/adapt-for-industry/validate.py
```

Run this before any Fabric workspace update, postprovision hook rerun, sample-data reset, or deployment. The validator checks required files, JSON/notebook parseability, Bicep compilation, cross-layer Fabric/Data Agent/report contracts, and UI contract drift. If it fails, stop and use `VALIDATE.md` for remediation.

## Step D: Redeploy / Activate

This accelerator is `azd-native`: there is no production Docker image or app host to deploy. After validation passes, use `REDEPLOYMENT.md` for non-destructive azd/postprovision guidance, and use the sibling `deploy-adaptation` skill before any Fabric sample-data reset, lakehouse truncate/drop, postprovision hook rerun, workspace teardown, or other cloud mutation.


## Quality Checks

Before delivering the industry pack, verify every generated CSV parses, every core entity is mapped, sample data is synthetic, Data Agent examples reference existing datasource keys, Power BI report bindings remain valid, UI wording is changed separately from backend/Fabric schema keys, and no placeholders remain.
