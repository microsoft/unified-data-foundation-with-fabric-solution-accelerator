# Renewable Energy Industry Pack - Schema Mapping

## Target scope

Industry: Energy & Utilities - renewable power generation, asset operations, and energy sales.

Source coverage: Fabric sample paths are the primary target. Deployment compatibility files are also staged for the default ADB/Snowflake sample filenames that the accelerator uploads or processes so activated demos do not mix industry terminology.

Compliance posture: NERC CIP, EPA, and FERC are acknowledged. The pack uses fully synthetic commercial and operational demo data and intentionally avoids critical infrastructure details, real grid assets, real customers, precise facility identifiers, and production operational telemetry.

## Stable contract strategy

This pack preserves the existing Fabric schemas, table names, and column keys so current notebooks, Data Agent datasource metadata, semantic model bindings, and report queryRefs can continue to resolve. Renewable-energy meaning is expressed through staged synthetic values, labels, descriptions, and planned display-copy changes.

| Current entity | Industry entity | Required changes | Sensitive fields |
|---|---|---|---|
| Customer | Offtaker, utility buyer, corporate PPA buyer, municipal buyer, or community solar sponsor | Keep `CustomerId`, `CustomerTypeId`, `CustomerRelationshipTypeId`, contact, active-status, and date fields. Populate business/government-style synthetic buyer contacts and relationship tiers such as `PPA-Utility-Offtake` and `Corporate-24x7-CFE`. | Business contact PII in production; buyer contract status; customer energy demand profile. |
| CustomerAccount | Offtaker settlement account | Keep `CustomerAccountId`, `ParentAccountId`, `CustomerAccountName`, `CustomerId`, and `IsoCurrencyCode`. Use one synthetic settlement account per offtaker. | Billing account numbers, credit exposure, settlement balances. |
| CustomerTradeName | Offtaker registered operating name | Keep trade-name fields and use synthetic utility, corporate, campus, and municipal buyer names. | Legal names, regulated counterparty identifiers. |
| CustomerRelationshipType | PPA, REC, interconnection, community solar, or asset ownership relationship type | Keep `CustomerRelationshipTypeId`, name, and description. Use renewable contract/relationship categories and document commercial meaning. | Contract tier, preferential pricing, regulated counterparty classification. |
| Location | Renewable site, balancing area, or grid node region | Keep location fields. Use synthetic regional coordinates and notes that coordinates are not asset coordinates. | Critical infrastructure location, substation/site coordinates, grid topology details. |
| ProductCategory | Renewable product category | Keep category hierarchy fields. Use categories such as solar PPA, wind PPA, storage services, renewable energy credits, capacity attributes, and curtailment settlement. | Proprietary product taxonomy or market pricing strategy. |
| Product | Renewable energy product, PPA product, REC bundle, storage service, or capacity product | Keep product/product-category, price, cost, status, date, and currency fields. Use synthetic price/cost per MWh, REC, or MW-month. | Proprietary tariff terms, hedge strategy, dispatch constraints. |
| Order | Energy delivery, generation commitment, PPA settlement, or REC delivery commitment | Keep `OrderId`, `SalesChannelId`, `OrderNumber`, `CustomerId`, `CustomerAccountId`, order date/status, totals, payment method, and currency. Use order totals as settlement value. | Contract volume, delivery period, grid delivery terms, pricing exposure. |
| OrderLine | Delivery line item for MWh, REC, storage, capacity, or curtailment service | Keep product linkage, `ProductName`, `Quantity`, `UnitPrice`, `LineTotal`, discount, and tax fields. Interpret `Quantity` as MWh, REC count, or MW-month based on staged product naming. | Operational generation volumes, settlement exceptions, curtailment details. |
| OrderPayment | Order settlement transaction reference | Keep `OrderId`, `PaymentMethod`, and `TransactionId`. Use synthetic ACH, wire, and registry settlement labels. | Bank references, registry transaction IDs, settlement audit details. |
| Account | Receivable/payable settlement account | Keep account, customer, status, balance, currency, and description fields. Use receivable balances for unpaid PPA/REC settlements. | Credit exposure, counterparty balance, regulated accounting details. |
| Invoice | Energy settlement invoice | Keep invoice, customer, order, date, due date, subtotal, tax, total, and status fields. Use invoice numbers and dates aligned to delivery orders. | Invoice amounts, billing terms, customer contract references. |
| Payment | Energy settlement payment | Keep payment, invoice, customer, date, amount, method, and status fields. Use synthetic settlement payments aligned to invoices. | Payment method, payment status, financial audit lineage. |

## Contract-preserving notes

- Do not rename lakehouse schemas, tables, or columns for this staged pack.
- Keep `shared.customer`, `shared.product`, `salesfabric.order`, `salesfabric.orderline`, `salesfabric.orderpayment`, `finance.invoice`, `finance.payment`, and `finance.account` available to Data Agent and report consumers.
- Keep report/Data Agent query keys such as `CustomerId`, `CustomerRelationshipTypeId`, `ProductName`, `Quantity`, `OrderTotal`, `OrderDate`, and `ProductID`/`ProductId`.
- Treat asset availability, curtailment, and REC settlement as display and sample-value concepts unless a later contract migration adds explicit fields and updates every producer and consumer.
