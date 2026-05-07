# Redeployment Guide — azd-native Fabric activation

## Purpose

After this adapter skill changes files in Unified Data Foundation with Fabric and `validate.py` passes, use this guide to re-apply non-destructive deployment changes. The surveyed publish surface is `azd-native`: there is no production Dockerfile and no long-running app service to redeploy. Provisioning and activation flow through azd plus the Fabric postprovision hook in `azure.yaml`.

## Deployment/reset safety gate

Before running `azd up`, `azd provision`, the Fabric install hook, any lakehouse table truncate/drop notebook, native sample data replacement, or workspace teardown, use the sibling [`deploy-adaptation`](../deploy-adaptation/SKILL.md) skill. It must confirm the target environment, prove sample/demo ownership, plan rollback/snapshot, and get explicit immediate-before-reset confirmation.

`azure.yaml` also has a `predown` hook that runs `infra/scripts/fabric/remove_udf_solution.py`. Treat `azd down` and that hook as destructive teardown, not as a normal reset path.

## Pre-flight

Run from the SA repo root:

```bash
az version
azd version        # requiredVersions.azd is >1.17.1 and !=1.23.9
git status --short
python .github/skills/adapt-for-industry/validate.py
az bicep build --file infra/main.bicep --stdout > /dev/null
```

Confirm the selected azd environment and required Fabric values:

```bash
azd env list
azd env select <env-name>
azd env get-values
```

Required or commonly used values include `AZURE_FABRIC_CAPACITY_NAME`, `SOLUTION_SUFFIX`, `AZURE_FABRIC_CAPACITY_ADMINISTRATORS`, optional `FABRIC_WORKSPACE_NAME`, optional `FABRIC_WORKSPACE_ADMINISTRATORS`, `AZURE_LOCATION`, and `AZURE_RESOURCE_GROUP`.

## Deploy / activate

### Option A — full azd provision plus hook

Use only after validation and `deploy-adaptation` safety gates pass:

```bash
azd up
```

This re-applies Bicep and runs `hooks.postprovision`, which invokes `infra/scripts/fabric/install_udf_solution.py` through `infra/scripts/utils/Run-PythonScript.ps1`.

### Option B — infrastructure only

Use when only `infra/main.bicep` or parameters changed and you intentionally do not want to redeploy Fabric workspace content:

```bash
azd provision
```

### Option C — postprovision hook only

Use only when the deployment plan says Bicep does not need to change and the hook inputs are confirmed safe:

```bash
pwsh ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/install_udf_solution.py" -SkipPythonVirtualEnvironment
```

Run from the SA repo root with the azd environment selected. Do not run this to reset data until `deploy-adaptation` confirms demo-only targets and rollback.

## Smoke checks

After activation, verify the exact artifacts touched by the adaptation:

1. Fabric workspace exists and expected lakehouses `maag_bronze`, `maag_silver`, and `maag_gold` are present.
2. Row counts or notebook output confirm expected sample/demo data is loaded and old sample entities are absent when replacement was confirmed.
3. `sales_dashboard` opens and adapted report title/visual labels render.
4. Data Agent loads adapted instructions/few-shot examples and can answer a representative prompt against selected tables.
5. Stable table/column contract keys such as `CustomerId`, `OrderId`, `ProductName`, and `Quantity` remain available unless an intentional contract migration was validated.

## Rollback

Revert file changes, run `python .github/skills/adapt-for-industry/validate.py`, then rerun the safest activation path selected by `deploy-adaptation`. If a hook appended or replaced data, rollback may also require a planned lakehouse/table restore or a sibling demo workspace; do not use broad workspace teardown unless explicitly approved.
