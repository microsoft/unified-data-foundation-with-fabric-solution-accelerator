# Generation Guide — customize-use-case for Unified Data Foundation with Fabric

This skill was generated for a Fabric/Power BI/Data Agent accelerator with `publish.surface = azd-native`.

## Architecture-specific pattern

Use-case customization is not a single JSON toggle. A useful new scenario must coordinate:

1. Native sample data under `infra/data/samples_fabric`, and optionally `samples_databricks` or `samples_snowflake`.
2. Fabric schema, bronze-to-silver, silver-to-gold, and orchestration notebooks under `src/fabric/notebooks/`.
3. Data Agent setup and packaged workspace configs under `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/`.
4. Power BI/Fabric report and semantic model artifacts under `fabric_workspace/reports/`.
5. `fabric_workspace/parameter.yml` when workspace item IDs or semantic model endpoints change.

## Output guidance

Prefer staging new packs under `infra/data/use_case_packs/<use_case>/` with clear integration notes. Only write to native `infra/data/samples_*` paths after the user confirms replacement or merge behavior.

## UI and contract guidance

There is no custom web frontend. Treat Fabric report JSON and Data Agent config as the UI surface. Update display labels/copy in report/Data Agent artifacts separately from stable schema/table/column keys in datasource metadata and semantic model bindings.

## Activation guidance

This skill records the plan. `deploy-adaptation` owns any `azd up`, postprovision hook rerun, Fabric sample/demo reset, lakehouse truncate/drop, table reload, or workspace teardown.
