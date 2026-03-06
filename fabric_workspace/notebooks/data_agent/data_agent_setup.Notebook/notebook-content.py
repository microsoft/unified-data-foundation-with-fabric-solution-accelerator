# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "environment": {
# META       "environmentId": "0c58b444-0b92-bbd4-4a73-35e068e88d7b",
# META       "workspaceId": "00000000-0000-0000-0000-000000000000"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Configure Fabric Data Agent
# 
# This notebook configures the Microsoft Fabric Data Agent using the `fabric-data-agent-sdk` library (in preview).
# 
# The notebook performs the following tasks:
# 1. **Install and Import Required Libraries** - Set up the necessary SDK and dependencies
# 2. **Variable Initialization and AI Instructions** - Configure data agent settings and define comprehensive AI instructions for analytics
# 3. **Initialize Data Agent Client** - Create a connection to the Data Agent service
# 4. **Connect to Existing Data Agent** - Establish connection to a pre-existing data agent instance
# 5. **Configure Lakehouse as Data Source** - Add the Lakehouse and select specific tables for AI access
# 6. **Configure Data Agent with AI Instructions and Few-shot Examples** - Apply AI instructions, remove existing few-shot examples, and add new query examples to improve the agent's performance
# 7. **Publish Data Agent Configuration** - Publish all configuration changes to make the data agent available for use

# MARKDOWN ********************

# ## Step 1: Install and Import Required Libraries

# CELL ********************

# Install the fabric data agent SDK for programmatic management
# NOTE: THIS WILL BE CONFIGURED VIA ENVIRONMENT AS SCHEDULED JOBS DO NOT ALLOW pip install COMMANDS
# %pip install fabric-data-agent-sdk==0.1.16a0
# %pip show fabric-data-agent-sdk

# Import required libraries
from uuid import UUID
from fabric.dataagent.client import FabricDataAgentManagement

print("✅ Installation and import complete")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 2: Variable Initialization and AI Instructions
# 
# Configure the variables needed for the data agent setup and define AI instructions:

# CELL ********************

# Configuration variables
data_agent_id = "e7308630-0a27-4dc2-bf68-9b7300364b3f"
lakehouse_id = "86c1a3bb-fee7-4ce5-9f89-8466a3e8aa1e"
lakehouse_workspace_id = "8b4b90aa-74f8-4b72-8fd0-1d254ff4ee59"

# Configure specific tables to be available to the AI
# Note: selected_tables is a list of [schema, table_name] pairs
# Example: [["dbo", "customers"], ["dbo", "orders"], ["sales", "products"]]
selected_tables = [['finance', 'account'], ['finance', 'invoice'], ['finance', 'payment'], ['shared', 'customer'], ['shared', 'productcategory'], ['salesfabric', 'order'], ['salesfabric', 'orderline'], ['salesfabric', 'orderpayment'], ['shared', 'customeraccount'], ['shared', 'customerrelationshiptype'], ['shared', 'customertradename'], ['shared', 'location'], ['shared', 'product']]

print(f"📋 Configuration:")
print(f"   Data Agent ID: {data_agent_id}")
print(f"   Lakehouse ID: {lakehouse_id}")

# AI instructions
agent_instructions = """
# Microsoft Fabric Data Agent - Master Prompt Instructions

## Overview

You are a specialized Microsoft Fabric Data Agent for the Unified Data Foundation with Fabric Solution Accelerator. Your expertise lies in helping users interact with, understand, and query the medallion architecture lakehouse data built on Microsoft Fabric. This solution implements a comprehensive data foundation with integrated domains covering shared entities (customer, product), finance, and sales data.

Your goal is to empower business users with data-driven insights that improve sales operations, and financial performance while maintaining the highest standards of data accuracy and query performance.

## Background and Special Guide

The data is synthetically generated. It is part of a solution accelerator as a public GitHub Repository. The purpose is to let users clone and deploy to jumpstart their real-time intelligence projects. The data is far from being comprehensive like those collected from a real-world sales and finance. There are limitations on what you can get out of the small sample datasets. Please follow below guidelines when interacting with users: 

- Do not offer root cause analysis or other complex statistical analysis.  
- Do not offer charts or visual reports. If users ask for them, explain that you cannot produce them at present. 
- When users ask about data in particular tables, exclude fields that are GUIDs when you display the fields of a table. 
- When users ask general questions such as "How tall is the Empire State Building?" or "What is the population of USA?", please refrain from answering them and decline politely as you are not a general chatbot. 

## Solution Architecture Context

This solution accelerator provides a unified data foundation with integrated data architecture leveraging Microsoft Fabric and OneLake. It's built with principles of medallion lakehouse architecture and supports data mesh concepts with domain-specific schemas and sample data frameworks.

### Architecture Focus

This data agent is designed specifically for the **Core Medallion Architecture in Microsoft Fabric**:

- 48 data engineering PySpark notebooks and 4 utility scripts
- Two runner notebooks for automated execution (Bronze → Silver → Gold)
- All data consolidated in the Gold tier data lake for unified access
- Prebuilt Power BI semantic models and dashboards with business insights:
  - Total sales for a period
  - Year-over-year sales comparison
  - Revenue by customer segment
  - Top-selling products by revenue/quantity
  - Sales distribution by gender

### Key Architecture Components:

- **Bronze Layer**: Raw data ingestion from source files
- **Silver Layer**: Validated and cleaned data with proper schemas
- **Gold Layer**: Enriched data ready for analytics and reporting
- **Power BI Integration**: Semantic models and dashboards for business insights
- **Automated Data Pipelines**: Runner notebooks for end-to-end data processing

### Data Domains (All Available in Gold Tier Data Lake):

1. **Shared Domain**: Customer and Product master data
2. **Finance Domain**: Accounts, invoices, and payments
3. **Sales Domain**: Orders, order lines, and payments

## Data Schema Knowledge

### Shared Domain Tables:

- **Customer**: Customer master data with demographics, contact information, and relationship types
  - Fields: CustomerId, CustomerTypeId (Individual/Business/Government), CustomerRelationshipTypeId (Standard/Premium/VIP/SMB/Local), FirstName, LastName, Gender, DateOfBirth, PrimaryPhone, PrimaryEmail, IsActive, etc.
- **Product**: Product catalog with pricing and categorization
  - Fields: ProductID, Name, Color, StandardCost, ListPrice, Size, Weight, CategoryID, CategoryName
- **CustomerAccount**: Customer account relationships
- **Location**: Geographic location data
- **ProductCategory**: Product categorization hierarchy

### Sales Domain Tables:

- **Order**: Sales orders from Fabric channel
  - Fields: OrderId, SalesChannelId (Fabric), OrderNumber, CustomerId, CustomerAccountId, OrderDate, OrderStatus, SubTotal, TaxAmount, OrderTotal, PaymentMethod, IsoCurrencyCode
- **OrderLine**: Individual line items per order
- **OrderPayment**: Payment details for orders

### Finance Domain Tables:

- **Account**: Financial accounts (Receivable/Payable)
  - Fields: AccountId, AccountNumber, CustomerId, AccountType, AccountStatus, Balance, Currency, CreatedDate
- **Invoice**: Invoice records
- **Payment**: Payment transactions

## Core Capabilities

### 1. Data Query Assistance

- Help users construct PySpark or SQL queries across bronze, silver, and gold layers
- Provide guidance on joining tables across domains
- Suggest optimal query patterns for analytics use cases
- Support both PySpark and SQL endpoint queries

### 2. Business Intelligence Support

- Explain available metrics and KPIs in the gold layer
- Guide users in creating meaningful aggregations and calculations
- Support Power BI semantic model understanding
- Reference prebuilt dashboard capabilities and insights

### 3. Data Model Navigation

- Explain relationships between tables across domains
- Clarify data lineage from bronze → silver → gold
- Help understand the medallion architecture benefits
- Guide users through the automated runner notebook workflows

### 4. Data Lake Navigation

- Help users understand the Gold tier data lake structure
- Guide users to the most relevant tables for their analytics needs
- Explain how all domain data is consolidated and accessible
- Guide on extending queries across multiple domains

### 4. Analytics Use Cases

Support common business scenarios:

- Customer segmentation analysis (by relationship type, demographics)
- Sales performance tracking (total sales, YoY comparison)
- Revenue analysis by customer segment
- Product performance metrics (top-selling products by revenue/quantity)
- Finance reporting (account balances, payment patterns)
- Cross-domain analytics (customer-product-sales relationships)

## Sample Data Context

The solution includes synthetic sample data for testing and demonstration:

- ~515 customer records across different types and relationship levels
- ~317 product records with multiple categories
- ~1,800+ order records with detailed line items
- ~515 financial account records with various statuses
- Invoice and payment history

### Key Business Entities:

- **Customer Types**: Individual, Business, Government
- **Relationship Types**: Standard, Premium, VIP, SMB (Small-Medium Business), Local
- **Sales Channels**: Fabric (primary channel for this architecture)
- **Payment Methods**: VISA, MC (MasterCard), PayPal, Discover
- **Account Types**: Receivable, Payable
- **Account Statuses**: Active, Overdue, Closed

## Query Guidance Principles

### 1. Performance Optimization

- Always prefer querying gold layer for analytics
- Use silver layer for validation and data quality checks
- Query bronze layer only for raw data investigation
- Suggest appropriate filtering and partitioning strategies

### 2. Data Quality Awareness

- Alert users to potential data quality considerations
- Recommend validation checks when querying across domains
- Suggest appropriate NULL handling for optional fields

### 3. Business Context

- Always provide business context for technical recommendations
- Explain the business meaning of metrics and calculations
- Relate technical queries to real-world business scenarios

## Common Query Patterns

### Customer Analysis:

```sql
-- Customer segmentation by relationship type
SELECT CustomerRelationshipTypeId, COUNT(*) as CustomerCount
FROM shared.Customer 
WHERE IsActive = true
GROUP BY CustomerRelationshipTypeId
```

### Sales Performance:

```sql
-- Monthly sales trends
SELECT 
    YEAR(OrderDate) as Year,
    MONTH(OrderDate) as Month,
    COUNT(*) as OrderCount,
    SUM(OrderTotal) as TotalRevenue
FROM salesfabric.Order 
WHERE OrderStatus = 'Completed'
GROUP BY YEAR(OrderDate), MONTH(OrderDate)
ORDER BY Year, Month
```

### Cross-Domain Analytics:

```sql
-- Customer value analysis
SELECT 
    c.CustomerRelationshipTypeId,
    c.Gender,
    COUNT(o.OrderId) as OrderCount,
    AVG(o.OrderTotal) as AvgOrderValue,
    SUM(o.OrderTotal) as TotalRevenue
FROM shared.Customer c
JOIN salesfabric.Order o ON c.CustomerId = o.CustomerId
WHERE c.IsActive = true AND o.OrderStatus = 'Completed'
GROUP BY c.CustomerRelationshipTypeId, c.Gender
```

## Response Guidelines

### 1. Always Be Contextual

- Reference the specific domain and layer when discussing data
- Explain business implications of technical queries
- Provide complete working examples when possible

### 2. Promote Best Practices

- Suggest proper SQL formatting and commenting
- Recommend appropriate aggregation levels
- Guide users toward scalable query patterns

### 3. Educational Approach

- Explain the "why" behind recommendations
- Share relevant medallion architecture concepts
- Help users understand data relationships

## Integration Points

### Power BI Capabilities:

- Sales analysis dashboards
- Customer segmentation reports
- Product performance metrics
- Financial reporting views

### Fabric Features:

- OneLake integration for unified data access
- Spark-based data processing notebooks
- Automated data pipeline execution
- Cross-workspace data sharing capabilities

## Limitations and Scope

### Current Scope:

- **Data Access**: Gold tier data lake in Microsoft Fabric (all domains consolidated)
- **Data Type**: Synthetic sample data (not production data patterns)
- **Language**: English language schema and data
- **Processing Pipeline**: 48 data engineering PySpark notebooks + 4 utility scripts
- **Automation**: 2 runner notebooks for automated Bronze→Silver→Gold processing

### Not Included:

- Real-time streaming data scenarios
- Advanced ML/AI model integration
- External data source integration beyond provided samples
- Data from Bronze or Silver layers (focus on Gold tier analytics-ready data)

## Error Handling and Troubleshooting

### Common Issues:

- **Schema not found**: Ensure proper database context (shared, finance, salesfabric)
- **Table not accessible**: Verify lakehouse connections and permissions
- **Performance issues**: Recommend gold layer queries over bronze/silver
- **Data inconsistencies**: Guide toward validation queries in silver layer

### Best Practices for Troubleshooting:

1. Start with schema validation queries
2. Use sample data for testing before production queries
3. Validate joins with small result sets first
4. Check data types and NULL handling in complex queries

## Ethical Guidelines & Safety

- **Data Accuracy:** Only rely on the data provided from the data sources and never make up any new data.
- **Manufacturing safety:** Never provide recommendations that could compromise worker safety
- **Data privacy:** Respect any confidentiality requirements for production data
- **Accurate reporting:** Ensure quality and safety metrics are precisely calculated
- **Responsible insights:** Consider business impact of recommendations and analysis
"""

data_source_instructions="""
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
```
"""

data_source_description="""
# Data Source Descriptions - Microsoft Fabric Gold Tier Data Lake

## Overview

This document provides comprehensive descriptions of all data sources available in the Microsoft Fabric Gold tier data lake. All data has been processed through the medallion architecture (Bronze → Silver → Gold) and is analytics-ready for business intelligence and reporting purposes.

## Domain Structure

### Shared Domain (`shared` schema)
Master data entities that serve as foundational reference data across the organization.

#### Customer (`shared.Customer`)
**Purpose**: Central customer master data with demographics and relationship management
**Source**: Customer management systems and CRM platforms
**Update Frequency**: Daily batch processing
**Record Count**: ~515 customers

| Field Name | Data Type | Description | Sample Values |
|------------|-----------|-------------|---------------|
| CustomerId | STRING | Primary key, unique customer identifier | CID-001, CID-002 |
| CustomerTypeId | STRING | Classification of customer organization type | Individual, Business, Government |
| CustomerRelationshipTypeId | STRING | Customer tier/relationship level | Standard, Premium, VIP, SMB, Local |
| IsActive | BOOLEAN | Current status of customer account | true, false |
| FirstName | STRING | Customer's first name | Tsehayetu, Antra |
| LastName | STRING | Customer's last name | Abera, Abola |
| Gender | STRING | Customer gender | Male, Female |
| DateOfBirth | DATE | Customer's birth date | 1960-03-18, 1964-12-28 |
| PrimaryPhone | STRING | Primary contact phone | (985) 555-0158 |
| SecondaryPhone | STRING | Alternative contact phone | (470) 555-0206 |
| PrimaryEmail | STRING | Primary email address | tsehayetu@contoso.com |
| SecondaryEmail | STRING | Alternative email address | backup@contoso.com |
| CreatedBy | STRING | System/user who created record | Sales, Services |

**Business Rules**:
- Each customer has a unique CustomerId
- CustomerRelationshipTypeId determines pricing tiers and service levels
- IsActive flag controls customer accessibility for new transactions

#### Product (`shared.Product`)
**Purpose**: Product catalog with pricing, categorization, and specifications
**Source**: Product information management (PIM) systems
**Update Frequency**: Weekly batch processing
**Record Count**: ~317 products

| Field Name | Data Type | Description | Sample Values |
|------------|-----------|-------------|---------------|
| ProductID | INTEGER | Primary key, unique product identifier | 1, 2, 3 |
| Name | STRING | Product name and specifications | "HL Road Frame - Black, 58" |
| Color | STRING | Product color variant | Black, Red, Blue, Multi |
| StandardCost | DECIMAL | Manufacturing/procurement cost | 1059.31, 13.0863 |
| ListPrice | DECIMAL | Suggested retail price | 1431.50, 34.99 |
| Size | STRING | Product size specification | 58, M, L, S |
| Weight | DECIMAL | Product weight in standard units | 1016.04 |
| CategoryID | INTEGER | Product category identifier | 18, 35, 27 |
| CategoryName | STRING | Product category description | Road Frames, Helmets, Socks |

**Business Rules**:
- ListPrice must be greater than StandardCost
- Products can have multiple color variants with same base specifications
- CategoryID links to product hierarchy for reporting and analysis

#### CustomerAccount (`shared.CustomerAccount`)
**Purpose**: Links customers to their financial accounts for transaction processing
**Source**: Financial systems and account management platforms
**Update Frequency**: Real-time during account creation/modification

#### Location (`shared.Location`)
**Purpose**: Geographic location data for customers and business operations
**Source**: Address validation services and geographic databases
**Update Frequency**: Monthly batch processing

#### ProductCategory (`shared.ProductCategory`)
**Purpose**: Hierarchical categorization of products for reporting and analysis
**Source**: Product management systems
**Update Frequency**: Quarterly during catalog reviews

---

### Finance Domain (`finance` schema)
Financial data supporting accounts receivable, accounts payable, and transaction processing.

#### Account (`finance.Account`)
**Purpose**: Financial accounts for tracking customer receivables and business payables
**Source**: ERP financial modules and accounting systems
**Update Frequency**: Daily batch processing with real-time balance updates
**Record Count**: ~515 accounts

| Field Name | Data Type | Description | Sample Values |
|------------|-----------|-------------|---------------|
| AccountId | STRING | Primary key, unique account identifier | UUID format |
| AccountNumber | STRING | Business-readable account number | ACC-Fabric-1000, ACC-Fabric-1001 |
| CustomerId | STRING | Foreign key to Customer table | CID-001, CID-002 |
| AccountType | STRING | Type of financial account | Receivable, Payable |
| AccountStatus | STRING | Current account status | Active, Overdue, Closed |
| CreatedDate | DATE | Account creation date | 2022-12-21, 2025-05-29 |
| ClosedDate | DATE | Account closure date (if applicable) | NULL for active accounts |
| Balance | DECIMAL | Current account balance | 0.0, 20642.95, -1500.00 |
| Currency | STRING | Account currency code | USD, EUR, GBP |
| Description | STRING | Account purpose description | "Customer receivable account (Fabric)" |

**Business Rules**:
- AccountType 'Receivable' represents money owed to the company
- AccountType 'Payable' represents money owed by the company
- AccountStatus 'Overdue' indicates payment past due date
- Balance can be positive (owed to company) or negative (credit balance)

#### Invoice (`finance.Invoice`)
**Purpose**: Invoice records for billing customers and tracking payments due
**Source**: Billing systems and invoice generation platforms
**Update Frequency**: Real-time during invoice creation and updates

#### Payment (`finance.Payment`)
**Purpose**: Payment transaction records for tracking money received and disbursed
**Source**: Payment processing systems and bank reconciliation
**Update Frequency**: Real-time during payment processing

---

### Sales Domain (`salesfabric` schema)
Sales transaction data from the Microsoft Fabric sales channel, including orders and payment details.

#### Order (`salesfabric.Order`)
**Purpose**: Sales order headers with customer, pricing, and status information
**Source**: E-commerce platform and sales order management systems
**Update Frequency**: Real-time during order processing
**Record Count**: ~1,800+ orders

| Field Name | Data Type | Description | Sample Values |
|------------|-----------|-------------|---------------|
| OrderId | STRING | Primary key, unique order identifier | UUID format |
| SalesChannelId | STRING | Sales channel identifier | Fabric |
| OrderNumber | STRING | Business-readable order number | F100000, F100001 |
| CustomerId | STRING | Foreign key to Customer table | CID-001, CID-002 |
| CustomerAccountId | STRING | Foreign key to CustomerAccount | CA-0001, CA-0003 |
| OrderDate | DATE | Date order was placed | 2024-03-05, 2021-12-22 |
| OrderStatus | STRING | Current order processing status | Completed, Pending, Cancelled |
| SubTotal | DECIMAL | Order total before tax | 15901.30, 9262.79 |
| TaxAmount | DECIMAL | Tax amount calculated | 795.06, 463.14 |
| OrderTotal | DECIMAL | Final order total including tax | 16696.36, 9725.93 |
| PaymentMethod | STRING | Payment method used | MC, VISA, PayPal, Discover |
| IsoCurrencyCode | STRING | Currency code for order | USD |
| CreatedBy | STRING | System/user who created order | SampleGen |

**Business Rules**:
- OrderTotal = SubTotal + TaxAmount
- SalesChannelId is always 'Fabric' for this data source
- OrderStatus 'Completed' indicates successful fulfillment and payment
- PaymentMethod abbreviations: MC (MasterCard), VISA, PayPal, Discover

#### OrderLine (`salesfabric.OrderLine`)
**Purpose**: Individual line items within sales orders, linking products to orders
**Source**: Order management systems and product catalogs
**Update Frequency**: Real-time during order processing

#### OrderPayment (`salesfabric.OrderPayment`)
**Purpose**: Payment details and transaction information for order payments
**Source**: Payment processing gateways and financial systems
**Update Frequency**: Real-time during payment processing

---

## Data Quality and Governance

### Data Quality Standards
- **Completeness**: All required fields populated (nullable fields clearly documented)
- **Accuracy**: Data validated against business rules during Silver layer processing
- **Consistency**: Standardized formats and reference data across domains
- **Timeliness**: Data freshness maintained according to specified update frequencies

### Data Lineage
All Gold tier data has been processed through:
1. **Bronze Layer**: Raw data ingestion with minimal transformation
2. **Silver Layer**: Data validation, cleansing, and business rule application
3. **Gold Layer**: Data enrichment, aggregation, and analytics optimization

### Reference Data Relationships
- **Customer ↔ Account**: One-to-many relationship via CustomerId
- **Customer ↔ Order**: One-to-many relationship via CustomerId
- **Order ↔ OrderLine**: One-to-many relationship via OrderId
- **Product ↔ OrderLine**: Many-to-many relationship via ProductId
- **Product ↔ ProductCategory**: Many-to-one relationship via CategoryId

### Synthetic Data Notice
All data in this environment is synthetic and generated for demonstration purposes. The data patterns, relationships, and business rules reflect realistic scenarios but do not represent actual customer, product, or financial information.
"""

# Initialize few-shot examples for queries based on your data
fewshots_examples = {'I need to understand our customer base better. Can you show me a breakdown of customers by relationship type and gender, including their average age and activity status? I want to see which customer segments we should focus on for our upcoming marketing campaign.': "-- Customer Segmentation Analysis - Detailed View by Relationship Type and Gender\r\nWITH customer_segmentation AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        Gender,\r\n        DATEDIFF(YEAR, DateOfBirth, GETDATE()) AS Age,\r\n        IsActive\r\n    FROM shared.customer\r\n    WHERE DateOfBirth IS NOT NULL \r\n      AND Gender IS NOT NULL\r\n),\r\n\r\nsegmentation_metrics AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        Gender,\r\n        COUNT(*) AS CustomerCount,\r\n        ROUND(AVG(CAST(Age AS FLOAT)), 1) AS AvgAge,\r\n        SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) AS ActiveCustomers,\r\n        SUM(CASE WHEN IsActive = 'False' THEN 1 ELSE 0 END) AS InactiveCustomers,\r\n        ROUND(\r\n            (SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), \r\n            1\r\n        ) AS ActivePercentage\r\n    FROM customer_segmentation\r\n    GROUP BY CustomerRelationshipTypeId, Gender\r\n),\r\n\r\ntotal_customers AS (\r\n    SELECT COUNT(*) AS TotalCount\r\n    FROM customer_segmentation\r\n)\r\n\r\nSELECT \r\n    sm.CustomerRelationshipTypeId AS [Relationship Type],\r\n    sm.Gender,\r\n    sm.CustomerCount AS [Total Customers],\r\n    CONCAT(sm.AvgAge, ' years') AS [Average Age],\r\n    CONCAT(sm.ActiveCustomers, ' / ', sm.InactiveCustomers) AS [Active / Inactive],\r\n    CONCAT(CAST(sm.ActivePercentage AS DECIMAL(5,1)), '%') AS [Activity Rate],\r\n    CONCAT(CAST(ROUND((sm.CustomerCount * 100.0 / tc.TotalCount), 1) AS DECIMAL(5,1)), '%') AS [% of Total Base]\r\nFROM segmentation_metrics sm\r\nCROSS JOIN total_customers tc\r\nORDER BY \r\n    sm.CustomerCount DESC, \r\n    sm.CustomerRelationshipTypeId, \r\n    CASE WHEN sm.Gender = 'Male' THEN 1 ELSE 2 END;\r\n\r\n-- Executive Summary by Relationship Type Only\r\nWITH customer_segmentation AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        Gender,\r\n        DATEDIFF(YEAR, DateOfBirth, GETDATE()) AS Age,\r\n        IsActive\r\n    FROM shared.customer\r\n    WHERE DateOfBirth IS NOT NULL \r\n      AND Gender IS NOT NULL\r\n),\r\n\r\nsegmentation_metrics AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        Gender,\r\n        COUNT(*) AS CustomerCount,\r\n        ROUND(AVG(CAST(Age AS FLOAT)), 1) AS AvgAge,\r\n        SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) AS ActiveCustomers,\r\n        ROUND(\r\n            (SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), \r\n            1\r\n        ) AS ActivePercentage\r\n    FROM customer_segmentation\r\n    GROUP BY CustomerRelationshipTypeId, Gender\r\n),\r\n\r\ntotal_customers AS (\r\n    SELECT COUNT(*) AS TotalCount\r\n    FROM customer_segmentation\r\n)\r\n\r\nSELECT \r\n    CustomerRelationshipTypeId AS [Relationship Type],\r\n    SUM(CustomerCount) AS [Total Customers],\r\n    CONCAT(ROUND(AVG(AvgAge), 1), ' years') AS [Average Age],\r\n    SUM(ActiveCustomers) AS [Active Customers],\r\n    CONCAT(CAST(ROUND(AVG(ActivePercentage), 1) AS DECIMAL(5,1)), '%') AS [Average Activity Rate],\r\n    CONCAT(CAST(ROUND((SUM(CustomerCount) * 100.0 / MAX(tc.TotalCount)), 1) AS DECIMAL(5,1)), '%') AS [% of Customer Base]\r\nFROM segmentation_metrics sm\r\nCROSS JOIN total_customers tc\r\nGROUP BY CustomerRelationshipTypeId, tc.TotalCount\r\nORDER BY SUM(CustomerCount) DESC;", 'I need to analyze our sales performance and identify our most valuable customers. Can you show me the top-performing customers by total revenue, their order patterns, and how different customer segments contribute to our overall sales? I also want to understand seasonal trends in our sales data.': "-- Sales Performance and Customer Value Analysis\r\n\r\n-- Top 20 Customers by Total Revenue\r\nWITH customer_value AS (\r\n    SELECT \r\n        c.CustomerId,\r\n        c.FirstName,\r\n        c.LastName,\r\n        c.CustomerRelationshipTypeId,\r\n        COUNT(o.OrderId) AS TotalOrders,\r\n        SUM(o.OrderTotal) AS TotalRevenue,\r\n        ROUND(AVG(o.OrderTotal), 2) AS AvgOrderValue,\r\n        MIN(o.OrderDate) AS FirstOrderDate,\r\n        MAX(o.OrderDate) AS LastOrderDate,\r\n        DATEDIFF(DAY, MIN(o.OrderDate), MAX(o.OrderDate)) AS CustomerLifespan_Days\r\n    FROM shared.customer c\r\n    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId\r\n    WHERE o.OrderStatus = 'Completed'\r\n    GROUP BY c.CustomerId, c.FirstName, c.LastName, c.CustomerRelationshipTypeId\r\n)\r\n\r\nSELECT TOP 20\r\n    CustomerId,\r\n    FirstName,\r\n    LastName,\r\n    CustomerRelationshipTypeId,\r\n    ROUND(TotalRevenue, 2) AS TotalRevenue,\r\n    TotalOrders,\r\n    AvgOrderValue\r\nFROM customer_value\r\nORDER BY TotalRevenue DESC;\r\n\r\n-- Customer Segment Performance Analysis\r\nWITH customer_value AS (\r\n    SELECT \r\n        c.CustomerId,\r\n        c.CustomerRelationshipTypeId,\r\n        COUNT(o.OrderId) AS TotalOrders,\r\n        SUM(o.OrderTotal) AS TotalRevenue,\r\n        AVG(o.OrderTotal) AS AvgOrderValue\r\n    FROM shared.customer c\r\n    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId\r\n    WHERE o.OrderStatus = 'Completed'\r\n    GROUP BY c.CustomerId, c.CustomerRelationshipTypeId\r\n),\r\n\r\ntotal_revenue AS (\r\n    SELECT SUM(OrderTotal) AS TotalRevenue\r\n    FROM salesfabric.[order]\r\n    WHERE OrderStatus = 'Completed'\r\n)\r\n\r\nSELECT \r\n    cv.CustomerRelationshipTypeId,\r\n    COUNT(cv.CustomerId) AS CustomerCount,\r\n    ROUND(SUM(cv.TotalRevenue), 2) AS SegmentRevenue,\r\n    ROUND(AVG(cv.TotalRevenue), 2) AS AvgRevenuePerCustomer,\r\n    SUM(cv.TotalOrders) AS SegmentOrders,\r\n    ROUND(AVG(CAST(cv.TotalOrders AS FLOAT)), 1) AS AvgOrdersPerCustomer,\r\n    ROUND(AVG(cv.AvgOrderValue), 2) AS SegmentAvgOrderValue,\r\n    ROUND((SUM(cv.TotalRevenue) * 100.0 / tr.TotalRevenue), 2) AS RevenuePercentage\r\nFROM customer_value cv\r\nCROSS JOIN total_revenue tr\r\nGROUP BY cv.CustomerRelationshipTypeId, tr.TotalRevenue\r\nORDER BY SegmentRevenue DESC;\r\n\r\n-- Monthly Sales Trends\r\nSELECT \r\n    YEAR(OrderDate) AS OrderYear,\r\n    MONTH(OrderDate) AS OrderMonth,\r\n    FORMAT(OrderDate, 'yyyy-MM') AS YearMonth,\r\n    COUNT(OrderId) AS MonthlyOrders,\r\n    ROUND(SUM(OrderTotal), 2) AS MonthlyRevenue,\r\n    ROUND(AVG(OrderTotal), 2) AS MonthlyAvgOrderValue,\r\n    COUNT(DISTINCT CustomerId) AS UniqueCustomers\r\nFROM salesfabric.[order]\r\nWHERE OrderStatus = 'Completed'\r\nGROUP BY YEAR(OrderDate), MONTH(OrderDate), FORMAT(OrderDate, 'yyyy-MM')\r\nORDER BY OrderYear, OrderMonth;\r\n\r\n-- Seasonal Sales Analysis\r\nWITH seasonal_sales AS (\r\n    SELECT \r\n        CASE \r\n            WHEN MONTH(OrderDate) IN (12, 1, 2) THEN 'Winter'\r\n            WHEN MONTH(OrderDate) IN (3, 4, 5) THEN 'Spring'\r\n            WHEN MONTH(OrderDate) IN (6, 7, 8) THEN 'Summer'\r\n            ELSE 'Fall'\r\n        END AS Season,\r\n        OrderId,\r\n        OrderTotal,\r\n        CustomerId\r\n    FROM salesfabric.[order]\r\n    WHERE OrderStatus = 'Completed'\r\n),\r\n\r\ntotal_revenue AS (\r\n    SELECT SUM(OrderTotal) AS TotalRevenue\r\n    FROM salesfabric.[order]\r\n    WHERE OrderStatus = 'Completed'\r\n)\r\n\r\nSELECT \r\n    ss.Season,\r\n    COUNT(ss.OrderId) AS SeasonalOrders,\r\n    ROUND(SUM(ss.OrderTotal), 2) AS SeasonalRevenue,\r\n    ROUND(AVG(ss.OrderTotal), 2) AS SeasonalAvgOrderValue,\r\n    COUNT(DISTINCT ss.CustomerId) AS UniqueSeasonalCustomers,\r\n    ROUND((SUM(ss.OrderTotal) * 100.0 / tr.TotalRevenue), 2) AS RevenuePercentage\r\nFROM seasonal_sales ss\r\nCROSS JOIN total_revenue tr\r\nGROUP BY ss.Season, tr.TotalRevenue\r\nORDER BY SeasonalRevenue DESC;\r\n\r\n-- High-Value Customer Analysis (Top 10%)\r\nWITH customer_value AS (\r\n    SELECT \r\n        c.CustomerId,\r\n        c.FirstName,\r\n        c.LastName,\r\n        c.CustomerRelationshipTypeId,\r\n        SUM(o.OrderTotal) AS TotalRevenue,\r\n        COUNT(o.OrderId) AS TotalOrders\r\n    FROM shared.customer c\r\n    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId\r\n    WHERE o.OrderStatus = 'Completed'\r\n    GROUP BY c.CustomerId, c.FirstName, c.LastName, c.CustomerRelationshipTypeId\r\n),\r\n\r\ncustomer_percentile AS (\r\n    SELECT \r\n        *,\r\n        NTILE(10) OVER (ORDER BY TotalRevenue DESC) AS RevenueDecile\r\n    FROM customer_value\r\n)\r\n\r\nSELECT \r\n    COUNT(*) AS HighValueCustomerCount,\r\n    ROUND(SUM(TotalRevenue), 2) AS HighValueRevenue,\r\n    ROUND(AVG(TotalRevenue), 2) AS AvgHighValueRevenue,\r\n    SUM(TotalOrders) AS HighValueOrders\r\nFROM customer_percentile\r\nWHERE RevenueDecile = 1;", 'I need to analyze our product performance to understand which products are driving revenue. Can you show me the top-selling products by revenue and quantity, product performance by category, and identify which products have the best profit margins? I also want to see how product preferences vary across different customer segments.': "-- Product Performance Analysis\r\n\r\n-- Top 15 Products by Revenue\r\nWITH product_sales AS (\r\n    SELECT \r\n        p.ProductID,\r\n        p.ProductName,\r\n        p.CategoryName,\r\n        p.StandardCost,\r\n        p.ListPrice,\r\n        ol.Quantity,\r\n        ol.UnitPrice,\r\n        (ol.Quantity * ol.UnitPrice) AS LineRevenue,\r\n        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit,\r\n        o.CustomerId\r\n    FROM salesfabric.orderline ol\r\n    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId\r\n    INNER JOIN shared.product p ON ol.ProductId = p.ProductID\r\n    WHERE o.OrderStatus = 'Completed'\r\n)\r\n\r\nSELECT TOP 15\r\n    ProductID,\r\n    ProductName,\r\n    CategoryName,\r\n    ROUND(SUM(LineRevenue), 2) AS TotalRevenue,\r\n    SUM(Quantity) AS TotalUnitsSold,\r\n    COUNT(DISTINCT CustomerId) AS UniqueCustomers,\r\n    COUNT(*) AS OrderLines,\r\n    ROUND(SUM(LineRevenue) / COUNT(DISTINCT CustomerId), 2) AS AvgRevenuePerCustomer\r\nFROM product_sales\r\nGROUP BY ProductID, ProductName, CategoryName\r\nORDER BY TotalRevenue DESC;\r\n\r\n-- Product Category Performance\r\nWITH product_sales AS (\r\n    SELECT \r\n        p.ProductID,\r\n        p.CategoryName,\r\n        ol.Quantity,\r\n        ol.UnitPrice,\r\n        (ol.Quantity * ol.UnitPrice) AS LineRevenue,\r\n        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit,\r\n        o.CustomerId\r\n    FROM salesfabric.orderline ol\r\n    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId\r\n    INNER JOIN shared.product p ON ol.ProductId = p.ProductID\r\n    WHERE o.OrderStatus = 'Completed'\r\n)\r\n\r\nSELECT \r\n    CategoryName,\r\n    COUNT(DISTINCT ProductID) AS ProductsInCategory,\r\n    ROUND(SUM(LineRevenue), 2) AS CategoryRevenue,\r\n    SUM(Quantity) AS CategoryUnitsSold,\r\n    COUNT(DISTINCT CustomerId) AS CategoryCustomers,\r\n    ROUND(AVG((LineProfit * 100.0) / LineRevenue), 2) AS AvgProfitMargin,\r\n    ROUND(SUM(LineRevenue) / COUNT(DISTINCT ProductID), 2) AS RevenuePerProduct\r\nFROM product_sales\r\nGROUP BY CategoryName\r\nORDER BY CategoryRevenue DESC;\r\n\r\n-- Top 12 Most Profitable Products (Revenue > $1,000)\r\nWITH product_sales AS (\r\n    SELECT \r\n        p.ProductID,\r\n        p.ProductName,\r\n        p.CategoryName,\r\n        p.StandardCost,\r\n        p.ListPrice,\r\n        ol.Quantity,\r\n        ol.UnitPrice,\r\n        (ol.Quantity * ol.UnitPrice) AS LineRevenue,\r\n        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit\r\n    FROM salesfabric.orderline ol\r\n    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId\r\n    INNER JOIN shared.product p ON ol.ProductId = p.ProductID\r\n    WHERE o.OrderStatus = 'Completed'\r\n),\r\n\r\nproduct_profitability AS (\r\n    SELECT \r\n        ProductID,\r\n        ProductName,\r\n        CategoryName,\r\n        StandardCost,\r\n        ListPrice,\r\n        SUM(LineProfit) AS TotalProfit,\r\n        SUM(LineRevenue) AS TotalRevenue,\r\n        SUM(Quantity) AS TotalQuantity,\r\n        AVG((LineProfit * 100.0) / LineRevenue) AS AvgMargin\r\n    FROM product_sales\r\n    GROUP BY ProductID, ProductName, CategoryName, StandardCost, ListPrice\r\n    HAVING SUM(LineRevenue) > 1000\r\n)\r\n\r\nSELECT TOP 12\r\n    ProductID,\r\n    ProductName,\r\n    CategoryName,\r\n    ROUND(TotalProfit, 2) AS TotalProfit,\r\n    ROUND(TotalRevenue, 2) AS TotalRevenue,\r\n    TotalQuantity,\r\n    ROUND(AvgMargin, 2) AS AvgMargin,\r\n    ROUND(TotalProfit / TotalQuantity, 2) AS ProfitPerUnit\r\nFROM product_profitability\r\nORDER BY TotalProfit DESC;\r\n\r\n-- Product Category Preferences by Customer Segment\r\nWITH product_sales AS (\r\n    SELECT \r\n        p.CategoryName,\r\n        c.CustomerRelationshipTypeId,\r\n        ol.Quantity,\r\n        (ol.Quantity * ol.UnitPrice) AS LineRevenue,\r\n        p.ProductID,\r\n        o.CustomerId\r\n    FROM salesfabric.orderline ol\r\n    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId\r\n    INNER JOIN shared.product p ON ol.ProductId = p.ProductID\r\n    INNER JOIN shared.customer c ON o.CustomerId = c.CustomerId\r\n    WHERE o.OrderStatus = 'Completed'\r\n),\r\n\r\nsegment_category AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        CategoryName,\r\n        SUM(LineRevenue) AS SegmentCategoryRevenue,\r\n        SUM(Quantity) AS SegmentCategoryQuantity,\r\n        COUNT(DISTINCT ProductID) AS ProductVariety,\r\n        COUNT(DISTINCT CustomerId) AS CustomersInSegment\r\n    FROM product_sales\r\n    GROUP BY CustomerRelationshipTypeId, CategoryName\r\n),\r\n\r\nsegment_totals AS (\r\n    SELECT \r\n        CustomerRelationshipTypeId,\r\n        SUM(SegmentCategoryRevenue) AS SegmentTotal\r\n    FROM segment_category\r\n    GROUP BY CustomerRelationshipTypeId\r\n)\r\n\r\nSELECT \r\n    sc.CustomerRelationshipTypeId,\r\n    sc.CategoryName,\r\n    ROUND(sc.SegmentCategoryRevenue, 2) AS SegmentCategoryRevenue,\r\n    ROUND((sc.SegmentCategoryRevenue * 100.0 / st.SegmentTotal), 1) AS CategoryShare,\r\n    sc.ProductVariety,\r\n    sc.CustomersInSegment\r\nFROM segment_category sc\r\nINNER JOIN segment_totals st ON sc.CustomerRelationshipTypeId = st.CustomerRelationshipTypeId\r"}

print(f"📋 AI Instructions and Configuration Defined:")
print(f"   Agent Instructions: {len(agent_instructions)} characters")
print(f"   Data Source Description: {len(data_source_description)} characters")
print(f"   Data Source Instructions: {len(data_source_instructions)} characters")
print(f"   Fewshots Examples: {len(fewshots_examples)} examples prepared")
print(f"   Selected Tables: {len(selected_tables)} tables configured")
print(f"   ✅ Configuration ready")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 3: Initialize Data Agent Client
# 
# Create a connection to the Data Agent service:

# CELL ********************

# Initialize the Data Agent management client for existing data agent
mgmt_client = FabricDataAgentManagement(UUID(data_agent_id))
print(f"✅ Successfully initialized Data Agent management client for: {data_agent_id}")
print(f"✅ Client ready for data agent operations")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 4: Connect to Existing Data Agent
# 
# Connect to an existing data agent using the configured ID:

# CELL ********************

# Connect to existing data agent and verify configuration
print(f"🤖 Connecting to existing data agent: {data_agent_id}")

config = mgmt_client.get_configuration()
print(f"✅ Successfully connected to data agent")

print(f"\n📊 Data Agent Details:")
print(f"   Name: Data Agent")
print(f"   ID: {data_agent_id}")
print(f"   Status: Ready for configuration")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 5: Configure Lakehouse as Data Source
# 
# Add the Lakehouse as a data source and select specific tables for the data agent:

# CELL ********************

# Add Lakehouse as data source to the data agent
print(f"🔗 Adding Lakehouse as data source...")
print(f"   Data Agent ID: {data_agent_id}")
print(f"   Lakehouse ID: {lakehouse_id}")

# Add the Lakehouse as a data source
datasource = mgmt_client.add_datasource(
    workspace_id_or_name=UUID(lakehouse_workspace_id),
    artifact_name_or_id=UUID(lakehouse_id),
    type="lakehouse"
)

print(f"✅ Successfully added Lakehouse data source")
print(f"   Datasource ID: {datasource._id}")

# Configure table selection from config variables
# Note: selected_tables is a list of [schema, table_name] pairs
print(f"\n📋 Configuring table selection...")
print(f"   Selected tables: {', '.join([f'{schema}.{table}' for schema, table in selected_tables])}")

# Enable the specified tables for the data agent
for schema, table_name in selected_tables:
    datasource.select(schema, table_name)
    print(f"   ✓ Enabled table: {schema}.{table_name}")

print(f"✅ Table configuration completed")
print(f"   Tables available to AI: {', '.join([f'{schema}.{table}' for schema, table in selected_tables])}")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 6: Configure Data Agent with AI Instructions and Few-shot Examples
# 
# Apply the AI instructions and add few-shot examples to configure the data agent's behavior:

# CELL ********************

# Update data agent with general AI instructions
print(f"🤖 Updating data agent with AI instructions...")
print(f"   Instructions length: {len(agent_instructions)} characters")

mgmt_client.update_configuration(instructions=agent_instructions)
print(f"✅ Successfully updated data agent configuration")

# Configure data source with specific instructions and description
print(f"\n🔗 Configuring data source instructions...")
print(f"   Instructions length: {len(data_source_instructions)} characters")

datasource.update_configuration(
    instructions=data_source_instructions,
    user_description=data_source_description
)
print(f"✅ Successfully updated data source configuration")

# Get existing few-shot examples and remove them
print(f"\n🔍 Checking for existing few-shot examples...")
existing_fewshots = datasource.get_fewshots()
print(f"   Found {len(existing_fewshots)} existing examples")

if len(existing_fewshots) > 0:
    print(f"🗑️ Removing existing few-shot examples...")
    for i, row in existing_fewshots.iterrows():
        fewshot_id = row['Id']
        question = row['Question'][:50] + ('...' if len(row['Question']) > 50 else '')
        print(f"   Removing: {question}")
        datasource.remove_fewshot(fewshot_id)
    print(f"✅ Successfully removed all {len(existing_fewshots)} existing examples")
else:
    print(f"   No existing examples to remove")

# Add few-shot examples to improve query generation
print(f"\n📚 Adding few-shot examples...")
print(f"   Adding {len(fewshots_examples)} example question-query pairs")

for i, (question, query) in enumerate(fewshots_examples.items(), 1):
    print(f"   {i}. Adding: {question[:60]}{'...' if len(question) > 60 else ''}")
    single_example = {question: query}
    datasource.add_fewshots(single_example)

print(f"✅ Successfully added all {len(fewshots_examples)} few-shot examples")

# Verify final configuration
fewshots_df = datasource.get_fewshots()
config = mgmt_client.get_configuration()
ds_config = datasource.get_configuration()

print(f"\n📊 Final Configuration Summary:")
print(f"   Agent instructions: {'✓' if config.instructions else '✗'}")
print(f"   Data source instructions: {'✓' if ds_config.get('additional_instructions') else '✗'}")
print(f"   Data source description: {'✓' if ds_config.get('user_description') else '✗'}")
print(f"   Few-shot examples: {len(fewshots_df)}")
print(f"   Datasource ID: {datasource._id}")

print(f"\n✅ Data agent configuration completed successfully!")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Step 7: Publish Data Agent Configuration
# 
# Publish the data agent configuration to make it available for use:

# CELL ********************

# Publish the data agent configuration
print(f"📤 Publishing data agent configuration...")
print(f"   Making data agent available for use...")

mgmt_client.publish()
print(f"✅ Successfully published data agent configuration")
print(f"   Data agent is now ready to answer questions!")
print(f"   You can now interact with the agent in Fabric using natural language queries")

print(f"\n🎉 Data Agent Configuration Complete!")
print(f"   Agent ID: {data_agent_id}")
print(f"   Status: Published and Ready")
print(f"   Available Tables: {', '.join([f'{schema}.{table}' for schema, table in selected_tables])}")
print(f"   Few-shot Examples: {len(fewshots_examples)}")
print(f"   Next: Test the agent with analytics queries!")

