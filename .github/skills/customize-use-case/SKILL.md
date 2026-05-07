---
name: customize-use-case
description: Add a new Fabric analytics use case to Unified Data Foundation with Fabric by coordinating sample data, notebooks, Data Agent configuration, Power BI report surfaces, validation, and safe activation.
---

# Customize Use Case — Unified Data Foundation with Fabric

## Context

Unified Data Foundation with Fabric is a Microsoft Fabric medallion lakehouse solution with shared customer/product, finance, and sales domains, packaged sample data, Fabric notebooks, Fabric Data Agent, and a Power BI sales dashboard. The primary customization surface is a coordinated Fabric artifact set: CSV samples in `infra/data/`, schema and transformation notebooks in `src/fabric/notebooks/`, Data Agent JSON/notebook configuration, Fabric workspace parameterization, and report/semantic-model surfaces.

Existing use cases include unified data platform, master data management, cross-platform sales analytics, finance data foundation, Power BI sales reporting, Fabric Data Agent natural-language exploration, and optional Databricks/Snowflake source integration.

## Step 1: Read Existing Configurations

Read these files before generating anything:

- `README.md` and `docs/TechnicalArchitecture.md` for architecture options and coupling constraints.
- `infra/data/samples_fabric/shared/Customer_Samples.csv`, `Product_Samples_Fabric.csv`, and related shared samples.
- `infra/data/samples_fabric/finance/*.csv`, `infra/data/samples_fabric/sales/*.csv`, `infra/data/samples_databricks/sales/*.csv`, and `infra/data/samples_snowflake/sales/*.csv` for source-specific CSV naming and shape.
- `src/fabric/notebooks/schema/model_shared_silver.ipynb`, `model_finance_gold.ipynb`, and `model_salesfabric_gold.ipynb` for schema/table conventions.
- `src/fabric/notebooks/bronze_to_silver/`, `src/fabric/notebooks/silver_to_gold/`, `run_bronze_to_silver.ipynb`, and `run_silver_to_gold.ipynb` for orchestration patterns.
- `src/fabric/notebooks/data_agent/data_agent_setup.ipynb` plus `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json`, `datasource.json`, and `fewshots.json` for agent instructions and query examples.
- `fabric_workspace/parameter.yml` for lakehouse, semantic model, and Data Agent ID replacement rules.
- `fabric_workspace/reports/sales_dashboard.Report/report.json` and `reports/theme.json` for Power BI labels, visual bindings, and branding.
- `.github/sa-analysis/architecture-survey.md` for `publish`, `ui_surface`, and `validation_capability` evidence.

Study CSV headers, schema names, notebook naming, table/lakehouse IDs, report field bindings, Data Agent selected tables, and the distinction between display labels/copy and stable backend/Fabric contract keys.

## Step 2: Gather Requirements

Ask the user:

1. **Use case name:** What analytics domain or scenario should be added? Use lowercase snake_case, such as `supply_chain_ops`.
2. **Business goal:** What questions should this use case answer, and which personas will use the Fabric report or Data Agent?
3. **Source systems:** Should the pack target Fabric only, or also Databricks and/or Snowflake sample paths?
4. **Entities and metrics:** What 4-8 core entities, dimensions, facts, measures, and relationships are required?
5. **Sample data:** Should new synthetic CSVs be created, or should existing customer-provided samples be mapped into a sibling pack path?
6. **Notebook changes:** Which schema, bronze-to-silver, silver-to-gold, and orchestration notebooks need new or changed tables?
7. **Data Agent behavior:** What selected tables, instructions, datasource description, and 3-5 few-shot questions/SQL examples should be added?
8. **Report/UI presentation:** Which report page titles, visual labels, Data Agent prompt copy, theme/branding, and smoke checks should reflect this use case? Multilingual/i18n/localization is out of scope; update only generic labels and copy.

## Step 3: Generate Artifacts

### 3.0 Pre-write check

Before writing any file, check whether the target already exists. If content differs, show the diff and ask whether to overwrite, merge, or write to a sibling path. Never overwrite customer data or deployed workspace artifacts silently.

### 3.1 Use-case pack plan

Create a non-mutating plan under a sibling pack path such as:

```text
infra/data/use_case_packs/<use_case>/
├── USE_CASE_MAPPING.md
├── ACTIVATION_HANDOFF.md
├── samples_fabric/<domain>/*.csv
├── samples_databricks/<domain>/*.csv        # only when Databricks is in scope
└── samples_snowflake/<domain>/*.csv         # only when Snowflake is in scope
```

The pack path is a staging location. To activate it, update the native loader-facing paths or notebooks intentionally; do not assume `infra/data/use_case_packs/` is automatically consumed by `install_udf_solution.py`.

### 3.2 Native artifact edits

Generate or update, as needed:

- Fabric schema notebooks in `src/fabric/notebooks/schema/` with the same `model_<domain>_<tier>.ipynb` naming pattern.
- Bronze-to-silver and silver-to-gold notebooks that preserve medallion stage boundaries and existing `%run` orchestration style.
- CSV samples under native source-specific paths only after explicit confirmation: `infra/data/samples_fabric/<domain>/`, `samples_databricks/<domain>/`, or `samples_snowflake/<domain>/`.
- Data Agent instructions, selected table metadata, datasource descriptions, and few-shot SQL examples that use real table/column names.
- `fabric_workspace/parameter.yml` mappings when new deployed workspace item IDs or semantic model/data-agent references are introduced.
- Power BI report/semantic-model artifacts only when report visuals must reflect the new use case.

### 3.3 UI and contract checklist

Use the surveyed Fabric UI surfaces in this order:

- [ ] Update user-facing display labels/copy in `report.json`, `stage_config.json`, and `fewshots.json` separately from stable table/column keys.
- [ ] Update Power BI report page titles, visual titles, axis labels, Data Agent examples, and dashboard terminology for the new use case.
- [ ] Review `datasource.json`, semantic model bindings, and report queryRefs as contract surfaces; keep backend/Fabric schema keys stable unless the contract migration is intentional and validated.
- [ ] Update `reports/theme.json` or report `.platform` metadata only when branding changes are requested.
- [ ] Record smoke checks: open the `sales_dashboard` report, verify the adapted labels/visuals, and ask the Data Agent a new few-shot question that exercises the new tables.

## Step 4: Activation Plan

Record, but do not execute, the activation handoff:

1. Files added or changed across `infra/data/`, notebooks, Data Agent configs, report artifacts, and parameter mappings.
2. Required azd/Fabric environment values, including `AZURE_FABRIC_CAPACITY_NAME`, `SOLUTION_SUFFIX`, `AZURE_FABRIC_CAPACITY_ADMINISTRATORS`, optional workspace admin values, and any new non-secret configuration.
3. Whether existing sample/demo lakehouse tables or report artifacts must be reset, replaced, or reloaded.
4. Whether the `azure.yaml` postprovision hook must be rerun to deploy notebook/data/report changes.
5. A clear handoff to `deploy-adaptation` for validation, demo-only ownership proof, snapshot/rollback planning, immediate-before-reset confirmation, and the actual cloud mutation.

Do not place destructive commands, postprovision reruns, table drops/truncates, data reloads, workspace teardown, or cloud-mutating commands in this skill workflow.

## Step C: Validate

From the SA repo root, run the validator generated with this skill:

```bash
python .github/skills/customize-use-case/validate.py
```

Run this before any Fabric workspace update, postprovision hook rerun, sample-data reset, or deployment. The validator checks required files, JSON/notebook parseability, Bicep compilation, cross-layer Fabric/Data Agent/report contracts, and UI contract drift. If it fails, stop and use `VALIDATE.md` for remediation.

## Step D: Redeploy / Activate

This accelerator is `azd-native`: there is no production Docker image or app host to deploy. After validation passes, use `REDEPLOYMENT.md` for non-destructive azd/postprovision guidance, and use the sibling `deploy-adaptation` skill before any Fabric sample-data reset, lakehouse truncate/drop, postprovision hook rerun, workspace teardown, or other cloud mutation.


## Quality Checks

Before delivering use-case artifacts, verify that JSON and notebooks parse, CSV headers match declared schemas, Data Agent SQL examples reference existing datasource keys, Power BI report bindings still point to existing fields, and no generic placeholders remain.
