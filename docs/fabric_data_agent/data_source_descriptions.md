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