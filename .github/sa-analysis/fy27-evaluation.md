# FY27 Evaluation — Unified Data Foundation with Fabric

## Overall Result

**Score: 11 / 20 — Tier 3.** The accelerator is strong as a deployable Fabric reference architecture, but adapters must coordinate multiple tightly coupled artifacts: data samples, schema notebooks, transformation notebooks, Data Agent metadata, semantic/report definitions, and postprovision deployment hooks.

| Principle | Score | Rationale |
|---|---:|---|
| P1: Data-first architecture | 3 | Packaged CSV samples and lakehouse notebooks make data visible and replaceable, but schemas, transformations, semantic model/report bindings, and Data Agent datasource metadata are coupled. A new data pack is feasible when all layers are updated together. |
| P2: Composable integration facades | 3 | Azure/Fabric deployment is automated through azd, Bicep, and Fabric REST helper scripts. Integrations are not abstracted behind swappable facades; Fabric, Power BI, and optional Databricks paths are explicit implementation choices. |
| P3: Configuration over custom code | 2 | Some configuration is externalized in `azure.yaml`, `infra/main.parameters.json`, `fabric_workspace/parameter.yml`, Data Agent JSON, and CSV samples, but business logic and schema evolution primarily live in notebooks and report JSON. |
| P4: Production-mindful, POC-ready standards | 3 | azd deployment, AVM Fabric capacity provisioning, GitHub validation workflow, and docs are present. Production hardening, environment promotion, cost profiles, and safe sample-data reset boundaries still need explicit adapter guidance. |

## Four-Layer Mapping

| Layer | Components |
|---|---|
| Stable Core | `azure.yaml`, `infra/main.bicep`, Fabric capacity provisioning, Fabric REST deployment scripts, workspace item deployment mechanics. |
| Configurable Layer | `infra/main.parameters.json`, azd env values, `fabric_workspace/parameter.yml`, Data Agent JSON configs, sample CSV directories. |
| Use Case Packs | Domain-specific schema/transformation notebooks, sample data, Data Agent prompts/examples, Power BI report/semantic-model changes, data-management checks. |
| Customer-Specific Edge | Customer data mappings, governance/privacy rules, custom Power BI visuals, additional Fabric/Databricks/Snowflake sources, production reset/rollback policy. |

## Customization Strategy Recommendation

1. **Primary `customize-use-case` surface:** add or adapt Fabric analytics domains across `infra/data/`, `src/fabric/notebooks/schema/`, `bronze_to_silver/`, `silver_to_gold/`, Data Agent configs, and report/semantic model surfaces.
2. **Primary `adapt-for-industry` surface:** map current shared/finance/sales entities to industry entities, generate synthetic sample CSVs, update notebooks and Data Agent/report copy, and preserve stable lakehouse/semantic contract keys unless a validated contract migration is intentional.
3. **Deployment activation requirement:** use the `azd-native` deployment path. Validation and planning happen first; actual `azd up`, postprovision hook reruns, Fabric lakehouse resets, table truncates/drops, and workspace teardown go through `deploy-adaptation` safety gates.
4. **Workarounds for low-scoring areas:** keep schema mapping documents beside generated packs, enumerate every artifact touched across data/schema/notebook/report/Data Agent layers, and add UI/cross-layer validation checks before any deployment.
