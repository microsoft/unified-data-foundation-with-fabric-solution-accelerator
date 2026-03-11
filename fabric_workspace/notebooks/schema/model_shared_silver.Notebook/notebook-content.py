# Fabric notebook source

# METADATA ********************

# META {
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f6efaae4-adf6-463c-84d7-9a959877a8a5",
# META       "default_lakehouse_name": "maag_silver",
# META       "default_lakehouse_workspace_id": "8b4b90aa-74f8-4b72-8fd0-1d254ff4ee59",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6efaae4-adf6-463c-84d7-9a959877a8a5"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Data Model for Customer and Product Dimentions. 
# 
# ## Schema Structure
# - **Customer Management (5 tables)**: 
# - Customer, Samples Ready: Customer_Samples.csv 
# - CustomerRelationshipType, Samples Ready: CustomerRelationshipType_samples.csv
# - CustomerTradeName, Samples Ready: CustomerTradeNames_Samples.csv
# - Location, Samples Ready: Location_Samples.csv
# - CustomerAccount, Samples Ready: CustomerAccount_Samples.csv
# - **Product Catalog (2 tables)**: 
# - Product, Samples Ready: Product_Samples.csv
# - ProductCategory, Samples Ready: ProductCategory_Samples.csv

# MARKDOWN ********************


# CELL ********************

################################################################################################
# Schema Configuration - You can define different value here
################################################################################################

# Schema Configuration
SCHEMA_NAME = "shared"
spark.sql(f"CREATE DATABASE IF NOT EXISTS {SCHEMA_NAME}")
print(f"✅ {SCHEMA_NAME} schema ready!")

# CELL ********************


################################################################################################
# Customer Domain - Customer with Contact Info, Customer Accounts, Locations, etc. 5 Tables
################################################################################################

# 1. Create Customer table
TABLE_NAME = "Customer"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    CustomerId STRING,
    CustomerTypeId STRING, --Individual, Business, Government
    IsActive BOOLEAN,
    CustomerNamePrefix STRING,
    FirstName STRING,
    LastName STRING,
    MiddleName STRING,
    Gender STRING,
    DateOfBirth DATE,
    PrimaryPhone STRING,
    SecondaryPhone STRING,
    PrimaryEmail STRING,
    SecondaryEmail STRING,
    CustomerEstablishedDate DATE,
    CustomerRelationshipTypeId STRING,
    CustomerNote STRING,
    CreatedBy STRING,
    UpdatedBy STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")


# 2. Create CustomerTradeName table
TABLE_NAME = "CustomerTradeName"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    CustomerId STRING,
    CustomerTypeId STRING, --Individual, Business, Government
    TradeNameId STRING,   
    TradeName STRING,
    PeriodStartDate DATE,
    PeriodEndDate DATE,
    CustomerTradeNameNote STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")


# 3. Create CustomerRelationshipType table
TABLE_NAME = "CustomerRelationshipType"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    CustomerRelationshipTypeId STRING,  -- Individual: Standard, Premium, VIP. Business: SMB, Premier, Partner. Government: Federal, State, Local.
    CustomerRelationshipTypeName STRING,
    CustomerRelationshipTypeDescription STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")


# 4. Create Location table
TABLE_NAME = "Location"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    LocationId STRING,
    CustomerId STRING,
    LocationName STRING,
    IsActive BOOLEAN,
    AddressLine1 STRING,  -- "1000 Main St" 
    AddressLine2 STRING,  -- "Apt 5" or "Suite 200"
    City STRING,
    StateId STRING,
    ZipCode STRING,
    CountryId STRING,
    SubdivisionName STRING,
    Region STRING,        -- "Northeast", "West Coast", "Midwest"
    Latitude DECIMAL(10,7),
    Longitude DECIMAL(10,7),
    Note STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")

# 5. Create CustomerAccount table
TABLE_NAME = "CustomerAccount"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    CustomerAccountId STRING,
    ParentAccountId STRING,
    CustomerAccountName STRING,
    CustomerId STRING,
    IsoCurrencyCode STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")

# CELL ********************


################################################################################################
# Products - Product and ProductCategory, 2 Tables
################################################################################################

# 1. Create Product table
TABLE_NAME = "Product"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    ProductID STRING,
    ProductName STRING,
    ProductDescription STRING,
    BrandName STRING,
    ProductNumber STRING,
    Color STRING,
    ProductModel STRING,
    ProductCategoryID STRING,
    CategoryName STRING,
    ListPrice DECIMAL(18,2),
    StandardCost DECIMAL(18,2),
    Weight DECIMAL(18,3),
    WeightUom STRING,     -- kg, lb, oz
    ProductStatus STRING, -- active, inactive, discontinued
    CreatedDate DATE,
    SellStartDate DATE,
    SellEndDate DATE,
    IsoCurrencyCode STRING,
    UpdatedDate DATE,
    CreatedBy STRING,
    UpdatedBy STRING
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")

# 2. Create ProductCategory table
TABLE_NAME = "ProductCategory"
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    CategoryID STRING,
    ParentCategoryId STRING,
    CategoryName STRING,
    CategoryDescription STRING,
    BrandName STRING,
    BrandLogoUrl STRING,
    IsActive BOOLEAN
)
USING DELTA
"""
spark.sql(create_table_sql)
print(f"✅ {SCHEMA_NAME}.{TABLE_NAME} table created!")

print(f"\n🎉 SCHEMA and TABLES CREATION COMPLETE!")
