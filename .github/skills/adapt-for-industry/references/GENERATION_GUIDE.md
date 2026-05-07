# Generation Guide — adapt-for-industry for Unified Data Foundation with Fabric

This skill was generated for a Fabric/Power BI/Data Agent accelerator with shared, finance, and sales sample domains.

## Industry-pack pattern

Create a reviewed industry pack under `infra/data/industry_packs/<industry>/` first. Include `SCHEMA_MAPPING.md`, `DATA_SWAP_GUIDE.md`, staged sample CSVs, and change plans for notebooks, Data Agent, and reports. Native sample paths are consumed by the deployment/install flow, so moving staged data into `infra/data/samples_fabric`, `samples_databricks`, or `samples_snowflake` requires explicit confirmation and validation.

## Entity mapping rules

Map Customer, Product, Order, OrderLine, OrderPayment, Account, Invoice, Payment, Location, and CustomerRelationshipType to industry equivalents. Preserve relationships and field types unless a contract migration is intentionally documented.

## UI and contract guidance

Power BI report labels and Data Agent prompt/examples are display surfaces. `datasource.json`, report queryRefs, semantic model fields, and lakehouse table/column names are contract surfaces. Keep contracts stable unless both producer and consumer are updated and validated.

## Activation guidance

Industry data replacement often reuses sample/demo stores. `deploy-adaptation` must verify environment ownership, snapshot/rollback, reset targets, and immediate-before-reset confirmation before any destructive mutation.
