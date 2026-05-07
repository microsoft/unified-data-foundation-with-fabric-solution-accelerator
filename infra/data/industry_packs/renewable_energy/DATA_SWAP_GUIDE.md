# Renewable Energy Industry Pack - Data Swap Guide

## 1. Prerequisites and source coverage

This pack stages a renewable energy adaptation under:

`infra/data/industry_packs/renewable_energy/`

It does not modify native sample paths. The staged files are intended for review, validation, and a later controlled activation handoff. The requested activation goal is to replace demo sample data after validation, but replacement must be gated through `deploy-adaptation` before any runtime or workspace mutation.

Compliance assumptions:

- Acknowledge NERC CIP, EPA, and FERC obligations.
- Use only fully synthetic offtaker, product, delivery, invoice, payment, account, and location data.
- Avoid critical infrastructure details such as real facility names, precise generation-site coordinates, substation identifiers, grid topology, protection systems, and operational control data.

## 2. Data format specification

All staged CSVs preserve native Fabric sample headers and are generated with 50 synthetic rows per staged entity.

| Domain | Staged file | Renewable entity | Key contract fields preserved |
|---|---|---|---|
| shared | `samples_fabric/shared/Customer_Samples.csv` | Offtaker or utility buyer | `CustomerId`, `CustomerTypeId`, `CustomerRelationshipTypeId`, `IsActive` |
| shared | `samples_fabric/shared/CustomerAccount_Samples.csv` | Offtaker settlement account | `CustomerAccountId`, `CustomerId`, `IsoCurrencyCode` |
| shared | `samples_fabric/shared/CustomerTradeName_Samples.csv` | Registered buyer operating name | `CustomerId`, `TradeNameId`, `TradeName` |
| shared | `samples_fabric/shared/CustomerRelationshipType_Samples.csv` | PPA/REC/interconnection relationship | `CustomerRelationshipTypeId`, `CustomerRelationshipTypeName` |
| shared | `samples_fabric/shared/Location_Samples.csv` | Renewable site or grid-node region | `LocationId`, `CustomerId`, regional address fields |
| shared | `samples_fabric/shared/ProductCategory_Samples.csv` | Renewable product taxonomy | `CategoryID`, `CategoryName`, `IsActive` |
| shared | `samples_fabric/shared/ProductCategory_Samples_Combined.csv` | Renewable product taxonomy used by shared product-category notebooks | `CategoryID`, `CategoryName`, `IsActive` |
| shared | `samples_fabric/shared/Product_Samples_Fabric.csv` | Renewable product or PPA product | `ProductID`, `Name`, `CategoryID`, `CategoryName`, price/cost fields |
| shared | `samples_fabric/shared/Product_Samples_Combined.csv` | Renewable product or PPA product used by shared product notebooks | `ProductID`, `ProductName`, `ProductCategoryID`, `CategoryName`, price/cost fields |
| sales | `samples_fabric/sales/Order_Samples_Fabric.csv` | Energy delivery or generation commitment | `OrderId`, `CustomerId`, `CustomerAccountId`, `OrderDate`, `OrderTotal` |
| sales | `samples_fabric/sales/OrderLine_Samples_Fabric.csv` | Delivered MWh, REC, storage, or capacity line | `OrderId`, `ProductId`, `ProductName`, `Quantity`, `UnitPrice` |
| sales | `samples_fabric/sales/OrderPayment_Fabric.csv` | Order settlement transaction | `OrderId`, `PaymentMethod`, `TransactionId` |
| finance | `samples_fabric/finance/Account_Samples_Fabric.csv` | Receivable/payable settlement account | `AccountId`, `CustomerId`, `Balance`, `Currency` |
| finance | `samples_fabric/finance/Invoice_Samples_Fabric.csv` | Energy settlement invoice | `InvoiceId`, `CustomerId`, `OrderId`, `TotalAmount` |
| finance | `samples_fabric/finance/Payment_Samples_Fabric.csv` | Energy settlement payment | `PaymentId`, `InvoiceId`, `CustomerId`, `PaymentAmount` |

The primary requested coverage is Fabric. For deployment compatibility with the accelerator's default runner notebooks and uploaded demo data folder, this pack also includes renewable compatibility files for the existing ADB/Snowflake sales sample names and the ADB finance/product sample names. This prevents activated demo deployments from mixing renewable Fabric data with legacy Contoso sample rows while preserving the existing table and file contracts.

## 3. Mapping instructions

Use the mapping in `SCHEMA_MAPPING.md` as the authoritative entity crosswalk.

Recommended activation mapping when a controlled replacement is approved:

| Current demo concept | Renewable demo concept |
|---|---|
| Customers | Offtakers, utility buyers, municipal buyers, and corporate PPA buyers |
| Customer relationship levels | PPA, REC, community solar, interconnection, and ownership relationship categories |
| Products | PPA products, REC bundles, storage services, capacity attributes, and curtailment services |
| Product categories | Renewable product taxonomy |
| Orders | Energy deliveries, generation commitments, and PPA settlements |
| Order lines | Delivered MWh, REC count, storage MWh, capacity MW-month, or curtailment settlement quantity |
| Invoices | Energy settlement invoices |
| Payments | Energy settlement payments |
| Locations | Regional renewable site or grid-node areas |

Keep the current schema/table/column names unless a later migration updates all notebooks, Data Agent datasource metadata, semantic-model bindings, report queryRefs, and validation checks together.

Default deployment compatibility replacement list:

- `infra/data/samples_fabric/shared/Customer_Samples.csv`
- `infra/data/samples_fabric/shared/CustomerAccount_Samples.csv`
- `infra/data/samples_fabric/shared/CustomerRelationshipType_Samples.csv`
- `infra/data/samples_fabric/shared/CustomerTradeName_Samples.csv`
- `infra/data/samples_fabric/shared/Location_Samples.csv`
- `infra/data/samples_fabric/shared/ProductCategory_Samples.csv`
- `infra/data/samples_fabric/shared/ProductCategory_Samples_Combined.csv`
- `infra/data/samples_fabric/shared/ProductCategory_Samples_ADB.csv`
- `infra/data/samples_fabric/shared/Product_Samples_Fabric.csv`
- `infra/data/samples_fabric/shared/Product_Samples_Combined.csv`
- `infra/data/samples_fabric/shared/Product_Samples_ADB.csv`
- `infra/data/samples_fabric/sales/Order_Samples_Fabric.csv`
- `infra/data/samples_fabric/sales/OrderLine_Samples_Fabric.csv`
- `infra/data/samples_fabric/sales/OrderPayment_Fabric.csv`
- `infra/data/samples_fabric/finance/Account_Samples_Fabric.csv`
- `infra/data/samples_fabric/finance/Invoice_Samples_Fabric.csv`
- `infra/data/samples_fabric/finance/Payment_Samples_Fabric.csv`
- `infra/data/samples_fabric/finance/Account_Samples_ADB.csv`
- `infra/data/samples_fabric/finance/Invoice_Samples_ADB.csv`
- `infra/data/samples_fabric/finance/Payment_Samples_ADB.csv`
- `infra/data/samples_databricks/sales/Order_Samples_ADB.csv`
- `infra/data/samples_databricks/sales/OrderLine_Samples_ADB.csv`
- `infra/data/samples_databricks/sales/OrderPayment_ADB.csv`
- `infra/data/samples_snowflake/sales/Order_Samples_Snow.csv`
- `infra/data/samples_snowflake/sales/OrderLine_Samples_Snow.csv`
- `infra/data/samples_snowflake/sales/OrderPayment_Snow.csv`

## 4. UI, report, and Data Agent terminology checklist

- Update visible report copy from sales language to renewable energy portfolio language.
- Rename display labels such as `Sales Analysis`, `Sales Overview`, `Net Sales`, `Top 5 Selling Products by Quantity`, and `Revenue Distribution by Customer Segment`.
- Keep backend report queryRefs and semantic fields stable, including `ProductName`, `Quantity`, `OrderDate`, and revenue measures, unless an intentional contract migration is validated.
- Update Data Agent instructions to describe renewable portfolio, generation performance, PPA revenue, asset availability, curtailment, REC settlement, and offtaker performance.
- Keep Data Agent SQL examples on existing datasource keys such as `shared.customer`, `shared.product`, `salesfabric.[order]`, `salesfabric.orderline`, `finance.invoice`, and `finance.payment`.
- Mention that all values are synthetic and not suitable for real operational, compliance, trading, dispatch, or grid-reliability decisions.

## 5. Validation instructions

From the repository root, validate before activation:

```bash
python3 .github/skills/adapt-for-industry/validate.py
```

If your local environment maps `python` to Python 3.10 or newer, the validator can also be run with `python`.

Also confirm every staged CSV parses and that foreign keys align:

- Every order `CustomerId` exists in the staged customer file.
- Every order `CustomerAccountId` exists in the staged customer account file.
- Every order line `OrderId` exists in the staged order file.
- Every order line `ProductId` exists in the staged product file.
- Every invoice `OrderId` and `CustomerId` exists in staged sales/shared data.
- Every payment `InvoiceId` exists in the staged invoice file.

## 6. Activation handoff

This guide is planning and data-format guidance only. It does not authorize native sample replacement, lakehouse reset, postprovision hook rerun, workspace teardown, or any Fabric data mutation.

Before replacing demo data after validation, use the sibling `deploy-adaptation` skill to confirm:

- Target workspace/environment ownership.
- Demo/sample-only scope.
- Snapshot or rollback plan.
- Exact native sample files to replace with staged renewable files.
- Immediate-before-reset confirmation.
- Smoke checks for report labels, representative visuals, Data Agent examples, row counts, and stable contract keys.
