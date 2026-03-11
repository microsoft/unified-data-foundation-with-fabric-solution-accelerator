# Fabric notebook source

# METADATA ********************

# META {
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "be663c06-2418-4eb2-b853-0fa5e76955b7",
# META       "default_lakehouse_name": "maag_silver",
# META       "default_lakehouse_workspace_id": "8b4b90aa-74f8-4b72-8fd0-1d254ff4ee59",
# META       "known_lakehouses": [
# META         {
# META           "id": "be663c06-2418-4eb2-b853-0fa5e76955b7"
# META         },
# META         {
# META           "id": "f6efaae4-adf6-463c-84d7-9a959877a8a5"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Load Bronze Data to Silver Table - Account (Fabric)
# 
# ## Overview
# Load Account sample data from Bronze lakehouse files into Silver lakehouse table for Fabric channel
# 
# ## Data Flow
# - **Source (Fabric)**: Bronze Lakehouse/Files/samples_fabric/finance/Account_Samples_Fabric.csv
# - **Target**: Silver Lakehouse finance.account table
# - **Process**: Read CSV, validate schema, check data quality, show value distributions, load to Delta table, verify load
# 
# ---

# CELL ********************

# --- Fabric Channel ---
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, sum as spark_sum
from pyspark.sql import functions as F
import sempy.fabric as fabric

# Configuration - Using correct Fabric cross-lakehouse path from Fabric portal
# Get workspace ID dynamically at runtime (avoids issues with spaces in workspace names)
WORKSPACE_ID = fabric.get_notebook_workspace_id()

# Get lakehouse ID dynamically (avoids issues with lakehouse names)
lakehouse_properties = mssparkutils.lakehouse.get("maag_bronze")
SOURCE_LAKEHOUSE_ID = lakehouse_properties.id

FABRIC_SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_fabric/finance/Account_Samples_Fabric.csv"

TARGET_SCHEMA = "finance"
TARGET_TABLE = "account"
TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"

print(f"🔄 Loading Fabric Account data")
print(f"📂 Source: {FABRIC_SOURCE_PATH}")
print(f"🎯 Target: {TARGET_FULL_PATH}")

# Read CSV from Bronze lakehouse
account_df = spark.read.option("header", "true").option("inferSchema", "true").csv(FABRIC_SOURCE_PATH)

print(f"✅ Data loaded successfully")
print(f"📊 Records: {account_df.count()}")
print(f"📋 Columns: {account_df.columns}")

# Display sample data
print(f"\n📖 Sample data:")
account_df.show(10, truncate=False)

required_columns = [
    'AccountId', 'AccountNumber', 'CustomerId', 'AccountType', 
    'AccountStatus', 'CreatedDate', 'CreatedBy'
 ]

# Add missing columns with default values if needed
missing_columns = [c for c in required_columns if c not in account_df.columns]
if missing_columns:
    print(f"⚠️ Warning: Missing columns in source data: {missing_columns}")
else:
    print(f"✅ All required columns present in source data.")

for col_name in missing_columns:
    account_df = account_df.withColumn(col_name, F.lit(""))


# Align DataFrame columns and types to match the target table
account_df = account_df.withColumn('AccountId', col('AccountId').cast(StringType()))
account_df = account_df.withColumn('AccountNumber', col('AccountNumber').cast(StringType()))
account_df = account_df.withColumn('CustomerId', col('CustomerId').cast(StringType()))
account_df = account_df.withColumn('AccountType', col('AccountType').cast(StringType()))
account_df = account_df.withColumn('AccountStatus', col('AccountStatus').cast(StringType()))
account_df = account_df.withColumn('CreatedDate', col('CreatedDate').cast(DateType()))
account_df = account_df.withColumn('CreatedBy', col('CreatedBy').cast(StringType()))
account_df = account_df.select(required_columns)

# Data quality checks
print(f"\n📊 Data Quality Check:")
null_counts = account_df.select([F.sum(col(c).isNull().cast("int")).alias(c) for c in required_columns]).collect()[0]
for col_name in required_columns:
    null_count = null_counts[col_name]
    if null_count > 0:
        print(f"  {col_name}: {null_count} null values")
    else:
        print(f"  {col_name}: ✅ No nulls")

# Show value distributions for AccountStatus
print(f"\n🎯 AccountStatus Distribution:")
account_df.groupBy('AccountStatus').count().orderBy('AccountStatus').show()

# Ensure the target schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}")

# Load data to Silver table
print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")
try:
    account_df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(TARGET_FULL_PATH)
    
    print(f"✅ Data loaded successfully to {TARGET_FULL_PATH}")

    # Verify the load
    result_count = spark.sql(f"SELECT COUNT(*) as count FROM {TARGET_FULL_PATH}").collect()[0]['count']
    print(f"📊 Records in target table: {result_count}")

    # Show sample of loaded data
    print(f"\n📖 Sample from Silver table:")
    spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY AccountId").show(10, truncate=False)
    
    print(f"🎉 Account data load complete!")

except Exception as e:
    print(f"❌ Error loading data to table: {str(e)}")
    raise
# --- End Fabric Channel ---

# CELL ********************

# # --- ADB Channel ---
# import pandas as pd
# from pyspark.sql import SparkSession
# from pyspark.sql.types import *
# from pyspark.sql.functions import col, sum as spark_sum
# from pyspark.sql import functions as F
# import sempy.fabric as fabric
#
# # Configuration - Using correct Fabric cross-lakehouse path from Fabric portal
# # Get workspace ID dynamically at runtime (avoids issues with spaces in workspace names)
# WORKSPACE_ID = fabric.get_notebook_workspace_id()
#
# # Get lakehouse ID dynamically (avoids issues with lakehouse names)
# lakehouse_properties = mssparkutils.lakehouse.get("maag_bronze")
# SOURCE_LAKEHOUSE_ID = lakehouse_properties.id
#
# ADB_SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_databricks/finance/Account_Samples_ADB.csv"
#
# TARGET_SCHEMA = "finance"
# TARGET_TABLE = "Account"
# TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"
#
# print(f"🔄 Loading ADB Account data")
# print(f"📂 Source: {ADB_SOURCE_PATH}")
# print(f"🎯 Target: {TARGET_FULL_PATH}")
#
# # Read CSV from Bronze lakehouse
# account_df = spark.read.option("header", "true").option("inferSchema", "true").csv(ADB_SOURCE_PATH)
#
# print(f"✅ Data loaded successfully")
# print(f"📊 Records: {account_df.count()}")
# print(f"📋 Columns: {account_df.columns}")
#
# # Display sample data
# print(f"\n📖 Sample data:")
# account_df.show(10, truncate=False)
#
# required_columns = [
#     'AccountId', 'AccountNumber', 'CustomerId', 'AccountType', 'AccountStatus', 'CreatedDate', 'CreatedBy'
#  ]
#
# missing_columns = [c for c in required_columns if c not in account_df.columns]
# if missing_columns:
#     print(f"⚠️ Warning: Missing columns in source data: {missing_columns}")
# else:
#     print(f"✅ All required columns present in source data.")
#
# for col_name in missing_columns:
#     account_df = account_df.withColumn(col_name, F.lit(""))
#
# account_df = account_df.withColumn('AccountId', col('AccountId').cast(StringType()))
# account_df = account_df.withColumn('AccountNumber', col('AccountNumber').cast(StringType()))
# account_df = account_df.withColumn('CustomerId', col('CustomerId').cast(StringType()))
# account_df = account_df.withColumn('AccountType', col('AccountType').cast(StringType()))
# account_df = account_df.withColumn('AccountStatus', col('AccountStatus').cast(StringType()))
# account_df = account_df.withColumn('CreatedDate', col('CreatedDate').cast(DateType()))
# account_df = account_df.withColumn('CreatedBy', col('CreatedBy').cast(StringType()))
# account_df = account_df.select(required_columns)
#
# # Data quality checks
# print(f"\n📊 Data Quality Check:")
# null_counts = account_df.select([F.sum(col(c).isNull().cast("int")).alias(c) for c in required_columns]).collect()[0]
# for col_name in required_columns:
#     null_count = null_counts[col_name]
#     if null_count > 0:
#         print(f"  {col_name}: {null_count} null values")
#     else:
#         print(f"  {col_name}: ✅ No nulls")
#
# # Show value distributions for AccountStatus
# print(f"\n🎯 AccountStatus Distribution:")
# account_df.groupBy('AccountStatus').count().orderBy('AccountStatus').show()
#
# # Ensure the target schema exists
# spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}")
#
# # Load data to Silver table
# print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")
# try:
#     account_df.write \
#         .format("delta") \
#         .mode("overwrite") \
#         .option("overwriteSchema", "true") \
#         .saveAsTable(TARGET_FULL_PATH)
#     print(f"✅ Data loaded successfully to {TARGET_FULL_PATH}")
#     # Verify the load
#     result_count = spark.sql(f"SELECT COUNT(*) as count FROM {TARGET_FULL_PATH}").collect()[0]['count']
#     print(f"📊 Records in target table: {result_count}")
#     # Show sample of loaded data
#     print(f"\n📖 Sample from Silver table:")
#     spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY AccountId").show(10, truncate=False)
#     print(f"🎉 Account data load complete!")
# except Exception as e:
#     print(f"❌ Error loading data to table: {str(e)}")
#     raise
# # --- End ADB Channel ---
