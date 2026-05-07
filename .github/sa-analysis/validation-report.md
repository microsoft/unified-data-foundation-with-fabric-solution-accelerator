# Adapter Skill Validation Report — Unified Data Foundation with Fabric

## Overall Assessment

**PASS.** All three adapter skills are ready for use in the cloned accelerator at `/tmp/unified-data-foundation-with-fabric-solution-accelerator`.

## Skill Contract Status

| Skill | Status | Required artifacts |
|---|---|---|
| `customize-use-case` | PASS | `SKILL.md`, `validate.py`, `VALIDATE.md`, `REDEPLOYMENT.md`, `references/GENERATION_GUIDE.md` |
| `adapt-for-industry` | PASS | `SKILL.md`, `validate.py`, `VALIDATE.md`, `REDEPLOYMENT.md`, `references/GENERATION_GUIDE.md` |
| `deploy-adaptation` | PASS | `SKILL.md`, `references/DEPLOYMENT_GUIDE.md` only |

`deploy-adaptation` intentionally has no `validate.py`, `VALIDATE.md`, or `REDEPLOYMENT.md`; it references the first two skills' validators and runbooks where relevant.

## Companion Artifact Status

- `customize-use-case/validate.py`: PASS, 11 checks passed or skipped as designed; `lint` and `tests` skipped because no repo lint/test framework config was detected.
- `adapt-for-industry/validate.py`: PASS, 11 checks passed or skipped as designed; `lint` and `tests` skipped for the same reason.
- Both `VALIDATE.md` files document `environment`, `lint`, `compile`, `schema_integrity`, `cross_layer`, `ui_contract`, `iac_build`, and `tests`.
- Both `REDEPLOYMENT.md` files match surveyed `publish.surface = azd-native` and route Fabric postprovision/sample-data mutation through `deploy-adaptation`.

## Deploy-Adaptation Safety Case

PASS. The deployment skill:

- Reads `azure.yaml`, Bicep/AVM files, Fabric install/remove hooks, sample data, notebooks, Data Agent configs, report artifacts, and generated sibling skills before recommending commands.
- Classifies impact across `data-only`, `fabric-artifact-only`, `infrastructure-only`, `frontend-only`, and `mixed`.
- Requires validation before `azd up`, `azd provision`, Fabric postprovision hook reruns, sample/demo data resets, or teardown.
- Treats `azd down` and the `predown` remove hook as destructive, confirmation-gated teardown.
- Requires sample/demo ownership evidence, rollback/snapshot planning, and immediate-before-reset confirmation before replacing lakehouse/sample data.

## UI Surface Coverage

PASS. The survey and generated skills cover Fabric UI surfaces rather than a non-existent web frontend:

- Power BI report display labels and visual bindings in `fabric_workspace/reports/sales_dashboard.Report/report.json`.
- Data Agent display/instruction surfaces in `stage_config.json` and `fewshots.json`.
- Stable datasource contract keys in `datasource.json`.
- Branding/theme signal in `reports/theme.json`.
- UI smoke checks for `sales_dashboard` and Fabric Data Agent.

The generated validators include `ui_contract` checks for report copy/fields, Data Agent copy/datasource keys, and theme branding.

## Issues Found

None.

## Warnings

- The FY27 score is Tier 3 because schemas, notebooks, sample data, semantic/report artifacts, and Data Agent configs are tightly coupled and must be adapted together.
- There is no custom frontend build command; UI validation is based on Fabric/Power BI/Data Agent artifact checks and smoke-test guidance.
