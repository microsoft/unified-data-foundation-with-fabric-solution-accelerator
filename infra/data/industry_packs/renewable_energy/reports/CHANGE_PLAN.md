# Renewable Energy Report Change Plan

## Scope

The activated deployment branch updates Power BI report display labels while preserving semantic-model fields and report queryRefs.

## Display label changes

| Current report label | Renewable energy label | Contract note |
|---|---|---|
| `Sales Analysis` | `Renewable Energy Portfolio` | Page display name only. |
| `Sales Overview` | `Renewable Portfolio Overview` | Textbox copy only. |
| `Filter Pane` | `Portfolio Filters` | Visual group display label only. |
| `Net Sales` | `PPA Revenue` | Keep existing measure/queryRef until semantic model migration. |
| `Top 5 Selling Products by Quantity` | `Top Renewable Products by Delivered Quantity` | Keep `ProductName` and `Quantity` bindings. |
| `Top 5 Selling Products by Revenue` | `Top Renewable Products by PPA Revenue` | Keep existing revenue measure binding. |
| `Revenue Distribution by Customer Segment` | `PPA Revenue by Offtaker Segment` | Keep `CustomerTypeId`/segment binding unless semantic model is migrated. |
| `Sales Distribution by Gender` | `Offtaker Contact Mix` | Consider replacing this visual in a later semantic migration because gender is not a renewable-energy business KPI. |
| `YoY Net Sales Comparison` | `YoY PPA Revenue Comparison` | Keep year/order-date bindings. |
| `Product Name` | `Renewable Product` | Display label only; keep `ProductName` queryRef. |
| `Quantity` | `Delivered Quantity` | Display label only; keep `Quantity` queryRef. |

## Binding preservation

Preserve report queryRefs and semantic model fields unless a future contract migration updates every dependent artifact:

- `Sales Orderline (adb+Fabric).ProductName`
- `Sum(Sales Orderline (adb+Fabric).Quantity)`
- `Sales Orderline (adb+Fabric).NetSales(Display)`
- `Sales Orderline (adb+Fabric).Revenue(adb + Fabric)`
- `Sales order (adb +Fabric).OrderDate`
- `Sales order (adb +Fabric).Year`
- `shared customer.CustomerTypeId`

## Smoke checks after activation

- The report opens to `Renewable Energy Portfolio`.
- A representative product/quantity visual renders with renewable product names and delivered quantity values.
- Revenue cards use renewable energy labels while existing measures still resolve.
- Data filters render without renaming backend keys.
- Stable Fabric contract keys remain available to Data Agent and report consumers.

## Future report improvements

If a later semantic migration adds explicit renewable fields, consider replacing retail-sales visuals with:

- Generation by resource type and region.
- PPA revenue by offtaker segment.
- Delivered MWh vs settlement amount by month.
- REC settlement value by product category.
- Curtailment settlement value where explicitly modeled.
