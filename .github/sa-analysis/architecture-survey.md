# Architecture Survey — Unified Data Foundation with Fabric

## 1. Directory Structure

The accelerator is a Microsoft Fabric-centered medallion lakehouse solution with supporting Azure Developer CLI infrastructure and workspace artifacts.

| Path | Purpose |
|---|---|
| `azure.yaml` | azd orchestration for Bicep provisioning and Fabric install/remove hooks. |
| `infra/main.bicep` | Resource-group scoped Bicep that provisions or references Fabric capacity through AVM. |
| `infra/main.parameters.json` | azd-backed deployment parameters for solution name and existing Fabric capacity. |
| `infra/scripts/fabric/` | Fabric REST/API deployment, install, and removal scripts. |
| `infra/deploy/udf_solution_installer.ipynb` | Notebook-driven Fabric workspace deployment and sample data load. |
| `infra/data/` | Packaged sample data for Fabric, Databricks, and Snowflake sources. |
| `src/fabric/notebooks/` | Source notebooks for schema creation, bronze-to-silver, silver-to-gold, data management, Data Agent, and report setup. |
| `src/databricks/notebooks/` | Databricks schema, load, and data-management notebooks for the optional Databricks path. |
| `fabric_workspace/` | Fabric-cicd workspace artifacts for lakehouses, notebooks, Data Agent, and Power BI report. |
| `reports/` | Power BI/Fabric theme assets. |
| `docs/` | Deployment, architecture, Data Agent, Copilot for Power BI, and customization documentation. |

## 2. Configuration Surfaces

- `azure.yaml:10-39` declares Bicep infra and hooks. `hooks.postprovision` runs `./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/install_udf_solution.py"` and the POSIX variant adds `-SkipPythonVirtualEnvironment`; `hooks.predown` runs `remove_udf_solution.py`.
- `infra/main.parameters.json:4-11` maps azd environment values into `solutionName` and `existingFabricCapacityName`.
- `infra/main.bicep:5-42` defines deploy-time parameters for solution naming, region, telemetry, Fabric capacity admins, SKU, and existing capacity reuse.
- `infra/scripts/fabric/install_udf_solution.py:20-40` reads Fabric deployment environment variables: `AZURE_FABRIC_CAPACITY_NAME`, `SOLUTION_SUFFIX`, `AZURE_FABRIC_CAPACITY_ADMINISTRATORS`, optional `FABRIC_WORKSPACE_NAME`, and `FABRIC_WORKSPACE_ADMINISTRATORS`.
- `fabric_workspace/parameter.yml:20-78` maps notebook/lakehouse GUIDs, semantic model SQL endpoints, and Data Agent lakehouse references to target workspace items.
- `src/fabric/notebooks/data_agent/data_agent_setup.ipynb` contains Data Agent setup placeholders for agent ID, lakehouse IDs, selected tables, instructions, datasource description, and query examples.
- `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json`, `draft/stage_config.json`, `draft/lakehouse-tables-maag_gold/datasource.json`, and `draft/lakehouse-tables-maag_gold/fewshots.json` define the packaged Data Agent configuration.

## 3. Data Layer

The default domain covers shared customer/product master data, finance, and sales across Fabric, Databricks, and Snowflake sample sources.

- Sample data is stored under `infra/data/samples_fabric/{shared,finance,sales}`, `infra/data/samples_databricks/sales`, and `infra/data/samples_snowflake/sales`.
- Fabric schema notebooks under `src/fabric/notebooks/schema/` create `shared`, `finance`, `salesfabric`, and `salesadb` schemas and Delta tables.
- Bronze-to-silver and silver-to-gold transformations live in `src/fabric/notebooks/bronze_to_silver/` and `src/fabric/notebooks/silver_to_gold/`; orchestration notebooks are `run_bronze_to_silver.ipynb` and `run_silver_to_gold.ipynb`.
- Data management notebooks `drop_all_tables_*.ipynb`, `truncate_all_tables_*.ipynb`, and `table_counts.sql` are the reset/verification surfaces and must be gated before use.
- Workspace lakehouse artifacts in `fabric_workspace/lakehouses/maag_bronze.Lakehouse`, `maag_silver.Lakehouse`, and `maag_gold.Lakehouse` define the deployable Fabric items.

## 4. Agent/AI Components

- The AI surface is Fabric Data Agent plus Copilot for Power BI rather than custom LangChain/Semantic Kernel code.
- `src/fabric/notebooks/data_agent/data_agent_setup.ipynb` configures the Data Agent, selected tables, instructions, datasource description, and examples.
- `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json:3-4` contains the master prompt instructions, including the synthetic-data disclaimer and guidance not to offer charts or root-cause analysis.
- `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json:3-20` packages natural-language few-shot questions and SQL queries over `shared`, `salesfabric`, and related schemas.

## 5. Integration Points

- Azure Developer CLI drives provisioning through `azure.yaml` and `infra/main.bicep`.
- `infra/main.bicep:89-98` uses AVM module `br/public:avm/res/fabric/capacity:0.1.1` for Fabric capacity.
- `infra/scripts/fabric/fabric_api.py` and related scripts call the Microsoft Fabric REST API using Azure CLI credentials and Fabric bearer tokens.
- Optional Databricks and Snowflake sample paths are represented by source data directories and Databricks notebooks; the Fabric workspace uses shortcuts/mirroring concepts documented in `README.md` and `docs/`.
- Power BI/Fabric report and semantic model artifacts are deployed from `fabric_workspace/reports/` and parameterized by `fabric_workspace/parameter.yml`.

## 6. Business Rules

- Schema and table rules are encoded in notebooks under `src/fabric/notebooks/schema/` and mirrored in `fabric_workspace/notebooks/schema/` deployable artifacts.
- Transformation rules are notebook code under `bronze_to_silver` and `silver_to_gold` directories for each domain/source.
- Data Agent behavior is controlled by `stage_config.json`, selected table datasource metadata, and few-shot SQL examples.
- Power BI report visuals encode business presentation rules in `fabric_workspace/reports/sales_dashboard.Report/report.json`.
- The README explicitly warns that data model, notebooks, semantic models, dashboards, and sample data are cohesive and must be changed together (`README.md:52-65`).

## 7. Extension Points

High-value extension points for adapter skills:

1. Add a new analytics domain/use case by adding sample data under `infra/data/`, matching Fabric schema and transformation notebooks under `src/fabric/notebooks/`, Data Agent table/query examples, and report/semantic model surfaces.
2. Adapt the default shared/finance/sales model to a target industry by mapping entities, replacing or adding synthetic samples, updating schema/transformation notebooks, and updating Data Agent/report terminology.
3. Use `fabric_workspace/parameter.yml` to keep deployed workspace IDs and lakehouse/Data Agent/semantic model references environment-safe.
4. Route any sample/demo reset, install-hook rerun, lakehouse truncate/drop, workspace teardown, or Fabric data mutation through `deploy-adaptation` safety gates.

## 8. Deployment and UI/Frontend Surfaces

- There is no custom web frontend package, no React/Vue/Next build, and no production Dockerfile. The only Dockerfile is `.devcontainer/Dockerfile`, which is excluded from production classification.
- UI/frontend surfaces are Fabric and Power BI workspace artifacts:
  - `fabric_workspace/reports/sales_dashboard.Report/report.json:36,43,61,69` contains page/report labels such as `Sales Analysis`, `Sales Overview`, `Filter Pane`, `Product Name`, `Quantity`, and `Top 5 Selling Products by Quantity`.
  - `reports/theme.json:1` contains the `maag-theme` report theme name.
  - `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json:3-4` contains Data Agent instructions visible to generated answers.
  - `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json:3-20` contains natural-language prompt examples and SQL examples.
  - `fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json` contains stable schema/table/column contract keys such as `CustomerId`, `OrderId`, `ProductName`, and `Quantity`.
- UI smoke checks must be Fabric artifact checks: open the `sales_dashboard` report, verify adapted page/visual labels, confirm the Data Agent loads with adapted instructions/examples, and verify the selected tables still expose stable lakehouse schema keys.

### 9. Publish & Validation Surface

```yaml
publish:
  surface: azd-native
  evidence:
    production_dockerfiles: []
    bicep_acr_refs: []
    bicep_container_apps_refs: []
    bicep_aks_refs: []
    bicep_static_site_refs: []
    bicep_app_service_refs: []
    bicep_function_app_refs: []
    avm_module_count: 2
  services: []
  azure_yaml_hooks:
    postprovision: './infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/install_udf_solution.py"'
    postdeploy: null
    predeploy: null
ui_surface:
  evidence:
    labels_and_copy:
      - "fabric_workspace/reports/sales_dashboard.Report/report.json:36"
      - "fabric_workspace/reports/sales_dashboard.Report/report.json:43"
      - "fabric_workspace/reports/sales_dashboard.Report/report.json:61"
      - "fabric_workspace/reports/sales_dashboard.Report/report.json:69"
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json:3"
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json:5"
    form_fields: []
    review_steps: []
    routes: []
    components:
      - "fabric_workspace/reports/sales_dashboard.Report/report.json:33"
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json:1"
    assets_branding:
      - "reports/theme.json:1"
      - "fabric_workspace/reports/sales_dashboard.Report/.platform:1"
    validation_messages: []
    frontend_constants:
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json:6"
      - "fabric_workspace/parameter.yml:20"
    client_parsers_types:
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json:1"
    api_payload_expectations:
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json:1"
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json:1"
      - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json:1"
  build_commands: []
  smoke_checks:
    - route: "Fabric workspace > sales_dashboard report"
      expected_signal: "adapted report page title, visual title, and axis labels render without breaking ProductName/Quantity field bindings"
    - route: "Fabric Data Agent > lakehouse-tables-maag_gold"
      expected_signal: "adapted Data Agent instructions and few-shot examples load while stable CustomerId, OrderId, ProductName, and Quantity contract keys remain available"
validation_capability:
  lint_tools: []
  test_frameworks: []
  iac_build_commands:
    - tool: bicep
      command: "az bicep build --file infra/main.bicep --stdout > /dev/null"
  schema_files:
    - "infra/main.parameters.json"
    - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json"
    - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json"
    - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
    - "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json"
    - "fabric_workspace/reports/sales_dashboard.Report/report.json"
    - "src/fabric/notebooks/schema/model_shared_silver.ipynb"
    - "src/fabric/notebooks/schema/model_salesfabric_gold.ipynb"
    - "src/fabric/notebooks/data_agent/data_agent_setup.ipynb"
  cross_layer_pairs:
    - kind: 1to1-map
      producer: "infra/main.bicep"
      consumer: "infra/scripts/fabric/install_udf_solution.py"
      example: "Bicep outputs AZURE_FABRIC_CAPACITY_NAME, AZURE_FABRIC_CAPACITY_ADMINISTRATORS, and SOLUTION_SUFFIX are consumed as install-script environment variables."
    - kind: 1to1-map
      producer: "fabric_workspace/parameter.yml"
      consumer: "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
      example: "parameter.yml maps the Data Agent maag_gold lakehouse artifact ID used by datasource.json."
    - kind: column-references
      producer: "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
      consumer: "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json"
      example: "Few-shot SQL references CustomerId, OrderId, ProductName, and Quantity that must remain available in datasource metadata."
    - kind: column-references
      producer: "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
      consumer: "fabric_workspace/reports/sales_dashboard.Report/report.json"
      example: "Power BI report visual bindings reference ProductName and Quantity that must remain available in the lakehouse datasource/semantic model."
```

Evidence summary: `publish.surface` is `azd-native` because the repo has no production Dockerfile, no Container Apps/ACR/AKS/Static Web Apps/App Service/Functions compute modules, and `azure.yaml:17-28` defines a `postprovision` hook that deploys/seeds Fabric workspace artifacts. `infra/main.bicep:89-98` has one active Fabric capacity AVM module, and `infra/main.bicep:74-82` contains one commented AVM managed-identity reference, so raw AVM occurrence count is 2 while active deployable AVM density is 1. `azure.yaml:29-39` also defines a destructive `predown` remove hook; it is intentionally not placed in the required `azure_yaml_hooks` schema because the schema has no `predown` field, but generated deployment guidance treats `azd down`/predown as destructive teardown requiring explicit confirmation.
