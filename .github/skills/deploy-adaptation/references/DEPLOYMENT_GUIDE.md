# Deployment Guide — Unified Data Foundation with Fabric deploy-adaptation

## Evidence summary

- Publish surface: `azd-native`.
- azd entrypoint: `azure.yaml` with Bicep infra path `infra` and required azd version `>1.17.1 !=1.23.9`.
- Provisioning hook: `hooks.postprovision` runs `infra/scripts/fabric/install_udf_solution.py` through `infra/scripts/utils/Run-PythonScript.ps1`.
- Destructive teardown hook: `hooks.predown` runs `infra/scripts/fabric/remove_udf_solution.py`.
- IaC: `infra/main.bicep` uses AVM Fabric capacity module `br/public:avm/res/fabric/capacity:0.1.1`; no app host/container/static web/function resources were found.
- Runtime artifacts: Fabric lakehouses, notebooks, Data Agent configs, Power BI report/semantic model artifacts, and sample CSVs.

## Path-to-impact matrix

| Path pattern | Impact | Validation | Activation |
|---|---|---|---|
| `infra/data/**` | `data-only` or `mixed` when native sample paths are replaced | CSV/header checks, adapter validator, sample/demo ownership proof | Scoped sample reload through confirmed Fabric plan; no broad teardown |
| `src/fabric/notebooks/**` | `fabric-artifact-only` or `mixed` | Notebook JSON parse, schema/report/Data Agent cross-layer checks | postprovision hook or `azd up` after confirmation |
| `src/databricks/notebooks/**` | `mixed` when Databricks source is in scope | Notebook JSON parse and source-specific smoke checks | Databricks-specific plan plus Fabric refresh when mirrored/shortcut content changes |
| `fabric_workspace/Data Agent for UDF.DataAgent/**` | `fabric-artifact-only` or `frontend-only` for prompt-only changes | JSON parse and `ui_contract` | postprovision hook after validation |
| `fabric_workspace/reports/**`, `reports/theme.json` | `frontend-only` or `mixed` if field bindings change | JSON parse, `ui_contract`, report smoke check | postprovision hook/report deploy path after validation |
| `fabric_workspace/parameter.yml` | `mixed` | YAML review plus cross-layer ID/endpoint checks | postprovision hook or `azd up` |
| `infra/main.bicep`, `infra/main.parameters.json`, `azure.yaml` | `infrastructure-only` or `mixed` | `az bicep build --file infra/main.bicep --stdout > /dev/null`, azd env review | `azd provision` or `azd up` |

## Sample/demo reset safety

Reset is allowed only when all are true:

1. The target is confirmed sample/demo data, not customer or production data.
2. The exact workspace, lakehouse, schema/table, report, Data Agent, or file path is listed.
3. Validation has passed.
4. A rollback/snapshot plan exists.
5. The user confirms immediately before mutation.

If any target may contain real customer data, use a sibling demo workspace/lakehouse/table/path instead.

## Recommended command shapes

Non-destructive validation:

```bash
python .github/skills/customize-use-case/validate.py
python .github/skills/adapt-for-industry/validate.py
az bicep build --file infra/main.bicep --stdout > /dev/null
```

Infrastructure refresh:

```bash
azd provision
```

Full azd-native refresh:

```bash
azd up
```

Postprovision hook only, after validation and confirmation:

```bash
pwsh ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/install_udf_solution.py" -SkipPythonVirtualEnvironment
```

Avoid `azd down` except for explicitly approved teardown. It invokes the predown remove hook and can remove deployed Fabric artifacts.

## Smoke-test checklist

- Fabric workspace opens and expected lakehouses are present.
- Target tables contain expected synthetic/demo rows.
- Old sample/demo rows are absent when replacement was confirmed.
- Power BI `sales_dashboard` opens with adapted labels and working visuals.
- Fabric Data Agent loads adapted instructions/examples and answers a representative prompt.
- Contract keys and report bindings remain stable or were intentionally migrated and validated.
