# Renewable Energy Notebook Change Plan

## Scope

No native notebooks are changed by this pack. The activated deployment branch keeps notebook schemas and transformations stable while replacing native demo sample data with renewable energy CSVs.

## Contract-preserving notebook approach

Keep the existing schemas and table names:

- `shared.Customer`, `shared.CustomerAccount`, `shared.CustomerTradeName`, `shared.CustomerRelationshipType`, `shared.Location`, `shared.Product`, `shared.ProductCategory`
- `salesfabric.Order`, `salesfabric.OrderLine`, `salesfabric.OrderPayment`
- `finance.account`, `finance.invoice`, `finance.payment`

The staged CSVs preserve current headers, so the schema notebooks can remain structurally unchanged for the initial activation. Renewable terminology is carried in row values and in UI/Data Agent copy rather than through table or column renames.

## Review points before activation

| Notebook area | Required review |
|---|---|
| Schema notebooks | Confirm `model_shared_silver.ipynb`, `model_shared_gold.ipynb`, `model_salesfabric_silver.ipynb`, `model_salesfabric_gold.ipynb`, `model_finance_silver.ipynb`, and `model_finance_gold.ipynb` still match staged CSV headers and expected data types. |
| Bronze-to-silver notebooks | Confirm file names and required columns match the staged Fabric files. Treat `Quantity` as MWh, REC count, MW-month, or curtailment settlement quantity based on product naming. |
| Silver-to-gold notebooks | Confirm gold load timestamp enrichment and table writes do not require old sales/product vocabulary in code comments or notebook outputs. |
| Runner notebooks | Confirm orchestration still covers shared, salesfabric, and finance domains in the same order. |
| Data management notebooks | Use only through the deployment safety process; they remain reset surfaces and are not part of this staging pack. |

## Optional future contract migration

If future users require explicit renewable metrics such as `AssetAvailabilityPct`, `CurtailmentMWh`, `RECQuantity`, `BalancingAuthority`, or `TechnologyType`, add them through a validated migration that updates:

- Staged CSV headers and native sample files.
- Silver and gold schema notebooks.
- Bronze-to-silver and silver-to-gold transformations.
- Data Agent datasource metadata and few-shot SQL.
- Semantic model fields and report queryRefs.
- Validation checks and activation rollback plan.

Do not introduce these fields as silent defaults in this pack; the current pack is intentionally contract-preserving.
