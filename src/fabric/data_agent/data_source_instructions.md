# Data Source Instructions - Microsoft Fabric Gold Tier Data Lake

## Overview

This document provides specific instructions for querying and working with data sources in the Microsoft Fabric Gold tier data lake. These instructions ensure optimal performance, data accuracy, and adherence to best practices when accessing the unified data foundation.

## General Query Guidelines

### 1. Schema and Table Naming Conventions
Always use fully qualified table names when writing queries:
```sql
-- Correct format
SELECT * FROM shared.Customer
SELECT * FROM finance.Account  
SELECT * FROM salesfabric.Order

-- Avoid unqualified names
SELECT * FROM Customer  -- May cause ambiguity
```

### 2. Performance Optimization Principles
- **Always query Gold tier first**: This data is optimized for analytics
- **Use specific column selection**: Avoid `SELECT *` for large result sets
- **Apply filters early**: Use WHERE clauses to limit data processing
- **Leverage partitioning**: Filter by date columns when available

### 3. Data Type Handling
- **STRING fields**: Use single quotes for literal values
- **DATE fields**: Use standard date formats (YYYY-MM-DD)
- **DECIMAL fields**: Handle NULL values appropriately in calculations
- **BOOLEAN fields**: Use `true`/`false` (lowercase) for comparisons

## Domain-Specific Query Instructions

### Shared Domain Queries

#### Customer Analysis Patterns
```sql
-- Customer segmentation by relationship type
SELECT 
    CustomerRelationshipTypeId,
    CustomerTypeId,
    COUNT(*) as CustomerCount,
    COUNT(CASE WHEN IsActive = true THEN 1 END) as ActiveCount
FROM shared.Customer
GROUP BY CustomerRelationshipTypeId, CustomerTypeId
ORDER BY CustomerCount DESC;

-- Customer demographics analysis
SELECT 
    Gender,
    CustomerRelationshipTypeId,
    AVG(DATEDIFF(CURRENT_DATE(), DateOfBirth) / 365) as AvgAge,
    COUNT(*) as CustomerCount
FROM shared.Customer
WHERE IsActive = true 
  AND DateOfBirth IS NOT NULL
GROUP BY Gender, CustomerRelationshipTypeId;
```

#### Product Catalog Queries
```sql
-- Product pricing analysis by category
SELECT 
    CategoryName,
    COUNT(*) as ProductCount,
    AVG(ListPrice) as AvgListPrice,
    AVG(StandardCost) as AvgStandardCost,
    AVG(ListPrice - StandardCost) as AvgMargin
FROM shared.Product
WHERE ListPrice > 0 AND StandardCost > 0
GROUP BY CategoryName
ORDER BY AvgMargin DESC;

-- Product variants analysis
SELECT 
    CategoryName,
    Color,
    COUNT(*) as ProductCount,
    AVG(ListPrice) as AvgPrice
FROM shared.Product
GROUP BY CategoryName, Color
HAVING COUNT(*) >= 2
ORDER BY CategoryName, Color;
```

### Finance Domain Queries

#### Account Balance Analysis
```sql
-- Account status summary
SELECT 
    AccountType,
    AccountStatus,
    COUNT(*) as AccountCount,
    SUM(Balance) as TotalBalance,
    AVG(Balance) as AvgBalance
FROM finance.Account
GROUP BY AccountType, AccountStatus
ORDER BY AccountType, AccountStatus;

-- Overdue accounts analysis
SELECT 
    a.AccountNumber,
    a.Balance,
    a.CreatedDate,
    c.CustomerRelationshipTypeId,
    DATEDIFF(CURRENT_DATE(), a.CreatedDate) as DaysOutstanding
FROM finance.Account a
JOIN shared.Customer c ON a.CustomerId = c.CustomerId
WHERE a.AccountStatus = 'Overdue' 
  AND a.Balance > 0
ORDER BY a.Balance DESC;
```

### Sales Domain Queries

#### Sales Performance Analysis
```sql
-- Monthly sales trends
SELECT 
    YEAR(OrderDate) as SalesYear,
    MONTH(OrderDate) as SalesMonth,
    COUNT(*) as OrderCount,
    SUM(OrderTotal) as TotalRevenue,
    AVG(OrderTotal) as AvgOrderValue
FROM salesfabric.Order
WHERE OrderStatus = 'Completed'
GROUP BY YEAR(OrderDate), MONTH(OrderDate)
ORDER BY SalesYear DESC, SalesMonth DESC;

-- Payment method preferences
SELECT 
    PaymentMethod,
    COUNT(*) as OrderCount,
    SUM(OrderTotal) as TotalRevenue,
    AVG(OrderTotal) as AvgOrderValue
FROM salesfabric.Order
WHERE OrderStatus = 'Completed'
GROUP BY PaymentMethod
ORDER BY TotalRevenue DESC;
```

## Cross-Domain Analytics Patterns

### Customer Value Analysis
```sql
-- Customer lifetime value by segment
SELECT 
    c.CustomerRelationshipTypeId,
    c.Gender,
    COUNT(DISTINCT o.OrderId) as OrderCount,
    SUM(o.OrderTotal) as TotalRevenue,
    AVG(o.OrderTotal) as AvgOrderValue,
    SUM(o.OrderTotal) / COUNT(DISTINCT o.OrderId) as RevenuePerOrder
FROM shared.Customer c
JOIN salesfabric.Order o ON c.CustomerId = o.CustomerId
WHERE c.IsActive = true 
  AND o.OrderStatus = 'Completed'
GROUP BY c.CustomerRelationshipTypeId, c.Gender
ORDER BY TotalRevenue DESC;
```

### Product Performance with Customer Insights
```sql
-- Top products by customer segment
SELECT 
    p.CategoryName,
    p.Name,
    c.CustomerRelationshipTypeId,
    COUNT(*) as OrderFrequency,
    SUM(ol.Quantity * ol.UnitPrice) as TotalRevenue
FROM shared.Product p
JOIN salesfabric.OrderLine ol ON p.ProductID = ol.ProductId
JOIN salesfabric.Order o ON ol.OrderId = o.OrderId
JOIN shared.Customer c ON o.CustomerId = c.CustomerId
WHERE o.OrderStatus = 'Completed'
GROUP BY p.CategoryName, p.Name, c.CustomerRelationshipTypeId
HAVING TotalRevenue > 1000
ORDER BY TotalRevenue DESC;
```

## Data Access Best Practices

### 1. NULL Value Handling
Always consider NULL values in your queries:
```sql
-- Safe date calculations
SELECT CustomerId,
       CASE 
           WHEN DateOfBirth IS NOT NULL 
           THEN DATEDIFF(CURRENT_DATE(), DateOfBirth) / 365 
           ELSE NULL 
       END as Age
FROM shared.Customer;

-- Safe aggregations
SELECT COUNT(*) as TotalCustomers,
       COUNT(SecondaryPhone) as CustomersWithSecondaryPhone,
       COUNT(SecondaryEmail) as CustomersWithSecondaryEmail
FROM shared.Customer;
```

### 2. Join Optimization
Use appropriate join types and conditions:
```sql
-- Inner join for required relationships
SELECT c.CustomerId, c.FirstName, a.Balance
FROM shared.Customer c
INNER JOIN finance.Account a ON c.CustomerId = a.CustomerId
WHERE c.IsActive = true;

-- Left join to include all records
SELECT c.CustomerId, c.FirstName, COUNT(o.OrderId) as OrderCount
FROM shared.Customer c
LEFT JOIN salesfabric.Order o ON c.CustomerId = o.CustomerId 
    AND o.OrderStatus = 'Completed'
GROUP BY c.CustomerId, c.FirstName;
```

### 3. Date Range Filtering
Use efficient date filtering for performance:
```sql
-- Efficient date range queries
SELECT *
FROM salesfabric.Order
WHERE OrderDate >= '2024-01-01' 
  AND OrderDate < '2025-01-01'
  AND OrderStatus = 'Completed';

-- Year-over-year comparisons
SELECT 
    YEAR(OrderDate) as Year,
    SUM(OrderTotal) as YearlyRevenue,
    LAG(SUM(OrderTotal)) OVER (ORDER BY YEAR(OrderDate)) as PreviousYearRevenue
FROM salesfabric.Order
WHERE OrderStatus = 'Completed'
GROUP BY YEAR(OrderDate)
ORDER BY Year;
```

## Common Query Patterns and Templates

### 1. Customer Segmentation Template
```sql
SELECT 
    {segmentation_field},
    COUNT(*) as CustomerCount,
    COUNT(CASE WHEN IsActive = true THEN 1 END) as ActiveCount,
    ROUND(COUNT(CASE WHEN IsActive = true THEN 1 END) * 100.0 / COUNT(*), 2) as ActivePercentage
FROM shared.Customer
GROUP BY {segmentation_field}
ORDER BY CustomerCount DESC;
```

### 2. Time Series Analysis Template
```sql
SELECT 
    DATE_TRUNC('month', {date_field}) as Period,
    COUNT(*) as RecordCount,
    SUM({amount_field}) as TotalAmount,
    AVG({amount_field}) as AvgAmount
FROM {table_name}
WHERE {date_field} >= '{start_date}'
  AND {optional_filters}
GROUP BY DATE_TRUNC('month', {date_field})
ORDER BY Period;
```

### 3. Top N Analysis Template
```sql
SELECT 
    {dimension_field},
    COUNT(*) as Frequency,
    SUM({metric_field}) as Total,
    ROUND(AVG({metric_field}), 2) as Average
FROM {table_name}
WHERE {filter_conditions}
GROUP BY {dimension_field}
ORDER BY {ranking_metric} DESC
LIMIT {n};
```

## Error Prevention Guidelines

### 1. Common Pitfalls to Avoid
- **Division by zero**: Always check denominators before division
- **String case sensitivity**: Use UPPER() or LOWER() for consistent comparisons
- **Date format assumptions**: Use explicit date formatting
- **Aggregation without GROUP BY**: Ensure all non-aggregated columns are grouped

### 2. Data Validation Checks
Before running complex analyses, validate data quality:
```sql
-- Check for data completeness
SELECT 
    COUNT(*) as TotalRecords,
    COUNT(CustomerId) as NonNullCustomerIds,
    COUNT(DISTINCT CustomerId) as UniqueCustomerIds
FROM shared.Customer;

-- Verify referential integrity
SELECT 
    o.CustomerId,
    COUNT(*) as OrderCount
FROM salesfabric.Order o
LEFT JOIN shared.Customer c ON o.CustomerId = c.CustomerId
WHERE c.CustomerId IS NULL
GROUP BY o.CustomerId;
```

### 3. Performance Monitoring
Monitor query performance and adjust as needed:
- Use EXPLAIN PLAN to understand query execution
- Monitor query execution time for optimization opportunities
- Consider adding filters or limiting result sets for exploratory queries
- Use appropriate sampling for large dataset analysis

## Business Context Guidelines

### 1. Always Provide Business Meaning
When writing queries, include comments explaining the business purpose:
```sql
-- Business Question: Which customer segments generate the highest revenue?
-- This analysis helps prioritize marketing efforts and customer service resources
SELECT 
    c.CustomerRelationshipTypeId,
    COUNT(DISTINCT c.CustomerId) as CustomerCount,
    SUM(o.OrderTotal) as TotalRevenue,
    SUM(o.OrderTotal) / COUNT(DISTINCT c.CustomerId) as RevenuePerCustomer
FROM shared.Customer c
JOIN salesfabric.Order o ON c.CustomerId = o.CustomerId
WHERE c.IsActive = true 
  AND o.OrderStatus = 'Completed'
GROUP BY c.CustomerRelationshipTypeId
ORDER BY TotalRevenue DESC;
```

### 2. Consider Data Currency and Accuracy
Always document the data freshness and any limitations:
- Gold tier data is processed through automated pipelines
- Order data is near real-time (within minutes of transaction)
- Customer data is batch updated daily
- Product catalog is updated weekly
- Account balances are updated daily with end-of-day processing