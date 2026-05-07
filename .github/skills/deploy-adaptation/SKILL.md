---
name: deploy-adaptation
description: Safely validate, activate, deploy, smoke test, and roll back Unified Data Foundation with Fabric use-case or industry adaptations in its azd-native Fabric topology.
---

# Deploy Adaptation — Unified Data Foundation with Fabric

## Context

Unified Data Foundation with Fabric is deployed through azd/Bicep plus a Fabric postprovision hook. The surveyed publish surface is `azd-native`: there is no production Dockerfile, no app service host, and no custom frontend build. Infrastructure evidence is `azure.yaml`, `infra/main.bicep`, `infra/main.parameters.json`, and the Fabric install/remove scripts under `infra/scripts/fabric/`.

Use this skill after `customize-use-case` or `adapt-for-industry` has created or modified artifacts. It does not replace those skills' `REDEPLOYMENT.md` runbooks; it orchestrates the safe path for validation, Fabric sample/demo reset, `azd up` or hook rerun, report/Data Agent smoke checks, and rollback.

## Step 1: Read Deployment Evidence

Read before recommending any command:

- `.github/sa-analysis/architecture-survey.md` and `.github/sa-analysis/fy27-evaluation.md`.
- `.github/skills/customize-use-case/` and `.github/skills/adapt-for-industry/`, especially `validate.py`, `VALIDATE.md`, and `REDEPLOYMENT.md`.
- `azure.yaml` for `requiredVersions.azd`, postprovision, and predown hooks.
- `infra/main.bicep` and `infra/main.parameters.json` for Fabric capacity, AVM, and azd outputs.
- `infra/scripts/fabric/install_udf_solution.py`, `remove_udf_solution.py`, `fabric_api.py`, and `infra/deploy/udf_solution_installer.ipynb`.
- `infra/data/` native and staged sample data paths.
- `src/fabric/notebooks/` and `src/databricks/notebooks/` schema, transform, and data-management notebooks.
- `fabric_workspace/parameter.yml`, Data Agent JSON configs, report JSON, lakehouse artifacts, and `reports/theme.json`.

If evidence is missing or stale, pause. Do not invent `azd`, Fabric, Bicep, table-reset, or deletion commands.

## Step 2: Gather Request and Inspect Changes

Ask the user to confirm target azd environment, subscription/resource group, adaptation skill used, files or branch to activate, source coverage (Fabric/Databricks/Snowflake), desired window, and whether destructive sample/demo reset is in scope.

Inspect changed paths and map them to the surfaces below. Never print secrets or overwrite cloud/customer data while inspecting.

## Step 3: Classify Impact

Classify exactly one impact:

| Impact | Unified Data Foundation examples |
|---|---|
| `data-only` | Staged CSV packs, sample data plans, Data Agent few-shot/config changes that do not require infra or notebook schema changes. |
| `fabric-artifact-only` | Fabric workspace JSON/notebook/report/Data Agent artifacts with no Bicep changes and no native sample replacement yet. |
| `infrastructure-only` | `azure.yaml`, `infra/main.bicep`, parameter files, Fabric capacity SKU/admin/location settings. |
| `frontend-only` | Power BI/Fabric display-only labels/copy/theme changes in report/Data Agent artifacts without schema/data changes. |
| `mixed` | Any combination of data, notebooks, report/Data Agent, semantic model, parameter mappings, infra, or uncertain ordering. |

If changed paths touch report JSON, Data Agent prompt/copy, theme, or Fabric UI artifacts only, require UI smoke checks but no web frontend build. If UI changes are paired with schema/table/column, Data Agent datasource, semantic model, or notebook changes, classify as `mixed`.

## Step 4: Preflight

Before activation or deployment:

- Confirm `az account show`, `azd env list/select`, and `azd env get-values` point to the intended environment.
- Confirm azd satisfies `>1.17.1` and is not `1.23.9`.
- Confirm required Fabric values: `AZURE_FABRIC_CAPACITY_NAME`, `SOLUTION_SUFFIX`, `AZURE_FABRIC_CAPACITY_ADMINISTRATORS`, optional `FABRIC_WORKSPACE_NAME`, and optional `FABRIC_WORKSPACE_ADMINISTRATORS`.
- Confirm no secrets are committed, printed, or written into generated files.
- Confirm any reset target is sample/demo-only and separated from real customer or production data.
- Treat `azd down` and `azure.yaml` `predown`/`remove_udf_solution.py` as destructive teardown, not a normal data-swap path.

## Step 5: Validate Before Deploy

Run the relevant validators and checks from the SA repo root:

```bash
python .github/skills/customize-use-case/validate.py
python .github/skills/adapt-for-industry/validate.py
az bicep build --file infra/main.bicep --stdout > /dev/null
```

For changed JSON, CSV, notebooks, Bicep, or YAML, parse or compile the exact files before any mutation. For UI/Fabric display changes, run the validator's `ui_contract` check and plan smoke checks. Stop on failure.

## Step 6: Plan and Confirm Sample/Demo Reset

For new use-case or industry data packs, inventory:

- Native and staged sample data under `infra/data/`.
- Fabric lakehouse tables in bronze/silver/gold that will receive replacement data.
- Data management notebooks that can drop/truncate tables.
- Data Agent datasource/few-shot configs and report artifacts that reference the data.
- Any postprovision hook behavior that deploys, appends, replaces, or removes workspace content.

Only after validation succeeds, ask for explicit confirmation with the exact target list, sample/demo ownership evidence, rollback/snapshot plan, and load order. If data ownership is ambiguous, require a sibling demo workspace/lakehouse/table path instead of resetting shared stores.

For Fabric lakehouses, prefer scoped sample-row/table replacement over broad workspace teardown. Preserve schema/report definitions unless an intentional contract migration was validated and confirmed.

## Step 7: Activate / Deploy

Choose the narrowest evidence-backed path:

1. **No cloud mutation needed:** record that validation and local/staged artifacts are complete.
2. **Infrastructure only:** run `azd provision` after validation.
3. **Full Fabric refresh:** run `azd up` after validation and reset confirmation.
4. **Postprovision hook only:** run `pwsh ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/install_udf_solution.py" -SkipPythonVirtualEnvironment` only when the plan proves Bicep does not need to change and hook inputs are safe.
5. **Destructive teardown:** avoid by default. `azd down`/predown requires separate explicit approval, proof no customer data is affected, and a rollback plan.

Reset old confirmed sample/demo data immediately before loading the new pack, not during planning or preflight.

## Step 8: Smoke Test and Rollback

Smoke checks:

- Fabric workspace and expected lakehouses exist.
- Row counts or notebook output prove expected sample data is present.
- Old sample/demo entities are absent when replacement was confirmed.
- `sales_dashboard` renders adapted page/visual labels and key visuals.
- Data Agent loads adapted instructions/few-shot examples and answers a representative question.
- Stable contract keys such as `CustomerId`, `OrderId`, `ProductName`, and `Quantity` remain present unless intentionally migrated.

Rollback by reverting file changes, rerunning validators, and using the previous known-good activation path. If data was replaced, restore from the confirmed snapshot/sibling demo pack; do not use broad workspace teardown as a shortcut.
