# Renewable Energy Data Agent Change Plan

## Scope

The activated deployment branch updates Data Agent display-copy, datasource descriptions, and few-shot examples while preserving datasource contract keys.

## Instruction updates

The Data Agent instructions should describe:

- Renewable energy portfolio analytics across shared, finance, and salesfabric gold tables.
- Synthetic offtaker, PPA product, energy delivery, REC settlement, invoice, payment, and account data.
- Data limitations: demo-only, no real customer information, no real grid assets, no production telemetry, no dispatch or reliability recommendations, and no critical infrastructure details.
- Supported analytics: offtaker performance, PPA revenue, generation delivery volume, renewable product mix, REC settlement, settlement status, and high-level curtailment/service revenue where represented by product names.

Keep the existing safety boundaries:

- Do not offer root-cause analysis or complex statistical analysis.
- Do not offer charts or visual reports.
- Decline unrelated general-knowledge questions.
- Do not use the synthetic data for operational, trading, dispatch, reliability, compliance-certification, or financial-control decisions.

## Datasource metadata updates

Datasource schemas, tables, and columns remain stable. Only user-facing descriptions are updated:

| Current datasource surface | Renewable wording |
|---|---|
| Shared customer master data | Offtaker and utility buyer master data |
| Product catalog | Renewable product, PPA product, REC bundle, storage service, and capacity product catalog |
| Sales orders | Energy delivery and generation commitment settlements |
| Order lines | Delivered MWh, REC count, storage MWh, capacity MW-month, or curtailment settlement line items |
| Finance invoices/payments/accounts | Energy settlement invoices, payments, and receivable/payable accounts |

## Few-shot examples using existing keys

Use questions like these while keeping SQL on current datasource keys.

### Offtaker performance by relationship type

Question: "Which renewable offtaker relationship types have the highest completed PPA settlement value?"

```sql
SELECT
    c.CustomerRelationshipTypeId,
    COUNT(DISTINCT c.CustomerId) AS OfftakerCount,
    COUNT(o.OrderId) AS CompletedSettlements,
    ROUND(SUM(o.OrderTotal), 2) AS PpaRevenue
FROM shared.customer c
JOIN salesfabric.[order] o
    ON c.CustomerId = o.CustomerId
WHERE o.OrderStatus = 'Completed'
GROUP BY c.CustomerRelationshipTypeId
ORDER BY PpaRevenue DESC;
```

### Renewable product mix by delivered quantity

Question: "What renewable products contributed the most delivered MWh or REC quantity?"

```sql
SELECT TOP 10
    ol.ProductName,
    ROUND(SUM(ol.Quantity), 2) AS DeliveredQuantity,
    ROUND(SUM(ol.LineTotal), 2) AS SettlementValue
FROM salesfabric.orderline ol
JOIN salesfabric.[order] o
    ON ol.OrderId = o.OrderId
WHERE o.OrderStatus = 'Completed'
GROUP BY ol.ProductName
ORDER BY DeliveredQuantity DESC;
```

### Settlement status by invoice month

Question: "How are renewable settlement invoices trending by month and status?"

```sql
SELECT
    YEAR(i.InvoiceDate) AS InvoiceYear,
    MONTH(i.InvoiceDate) AS InvoiceMonth,
    i.InvoiceStatus,
    COUNT(i.InvoiceId) AS InvoiceCount,
    ROUND(SUM(i.TotalAmount), 2) AS InvoiceAmount
FROM finance.invoice i
GROUP BY YEAR(i.InvoiceDate), MONTH(i.InvoiceDate), i.InvoiceStatus
ORDER BY InvoiceYear, InvoiceMonth, i.InvoiceStatus;
```

## Smoke checks

- Data Agent loads renewable instructions without changing datasource artifact IDs.
- Example questions reference renewable terminology and existing SQL keys.
- Queries resolve against `shared`, `salesfabric`, and `finance` gold tables.
- The answer includes the synthetic-data disclaimer and avoids operational recommendations.
