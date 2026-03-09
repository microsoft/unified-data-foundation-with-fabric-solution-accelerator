# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
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

# # Load Bronze Data to Silver Table - OrderLine (ADB)
# 
# ## Overview
# Load OrderLine sample data from Bronze lakehouse files into Silver lakehouse table.
# 
# ## Data Flow
# - **Source**: Bronze Lakehouse /Files/samples_databricks/sales/OrderLine_Samples_ADB.csv
# - **Target**: Silver Lakehouse salesadb.OrderLine table (Delta table)
# - **Process**: Read CSV, validate schema, load to Delta table
# 
# ---

# CELL ********************

import pandas as pd
from pyspark.sql.types import *
from pyspark.sql.functions import col, sum as spark_sum
import os
import sempy.fabric as fabric

# Configuration - Using correct Fabric cross-lakehouse path from Fabric portal
# Get workspace ID dynamically at runtime (avoids issues with spaces in workspace names)
WORKSPACE_ID = fabric.get_notebook_workspace_id()

# Get lakehouse ID dynamically (avoids issues with lakehouse names)
lakehouse_properties = mssparkutils.lakehouse.get("maag_bronze")
SOURCE_LAKEHOUSE_ID = lakehouse_properties.id

SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_databricks/sales/OrderLine_Samples_ADB.csv"

TARGET_SCHEMA = "salesadb"
TARGET_TABLE = "OrderLine"
TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"

print(f"🔄 Loading OrderLine data")
print(f"📂 Source: {SOURCE_PATH}")
print(f"🎯 Target: {TARGET_FULL_PATH}")

# Read CSV from Bronze lakehouse
df = spark.read.option("header", "true").option("inferSchema", "true").csv(SOURCE_PATH)

print(f"✅ Data loaded successfully")
print(f"📊 Records: {df.count()}")
print(f"📋 Columns: {df.columns}")

# Display sample data
print(f"\n📖 Sample data:")
df.show(10, truncate=False)

# Validate and conform to target schema
print(f"🔍 Validating data quality...")

# Required columns from Model_Sales_Domain.ipynb OrderLine table
required_columns = [
    "OrderId", "OrderLineNumber", "ProductId", "ProductName", "Quantity",
    "UnitPrice", "LineTotal", "DiscountAmount", "TaxAmount"
]

# Check for missing columns
missing_columns = [c for c in required_columns if c not in df.columns]
if missing_columns:
    print(f"⚠️ Warning: Missing columns in source data: {missing_columns}")
else:
    print(f"✅ All required columns present in source data.")

# Add missing columns with default values if needed
from pyspark.sql import functions as F
for col_name in missing_columns:
    if col_name in ["Quantity", "UnitPrice", "LineTotal", "DiscountAmount", "TaxAmount"]:
        df = df.withColumn(col_name, F.lit(0.0))
    else:
        df = df.withColumn(col_name, F.lit(""))

# Align DataFrame columns and types to match the target table
from pyspark.sql.types import StringType, IntegerType, DoubleType

df = df.withColumn("OrderId", col("OrderId").cast(StringType()))
df = df.withColumn("OrderLineNumber", col("OrderLineNumber").cast(IntegerType()))
df = df.withColumn("ProductId", col("ProductId").cast(StringType()))
df = df.withColumn("ProductName", col("ProductName").cast(StringType()))
df = df.withColumn("Quantity", col("Quantity").cast(IntegerType()))
df = df.withColumn("UnitPrice", col("UnitPrice").cast(DoubleType()))
df = df.withColumn("LineTotal", col("LineTotal").cast(DoubleType()))
df = df.withColumn("DiscountAmount", col("DiscountAmount").cast(DoubleType()))
df = df.withColumn("TaxAmount", col("TaxAmount").cast(DoubleType()))
df = df.select(required_columns)

# Data quality checks
print(f"\n📊 Data Quality Check:")
null_counts = df.select([F.sum(col(c).isNull().cast("int")).alias(c) for c in required_columns]).collect()[0]
for col_name in required_columns:
    null_count = null_counts[col_name]
    if null_count > 0:
        print(f"  {col_name}: {null_count} null values")
    else:
        print(f"  {col_name}: ✅ No nulls")

# Load data to Silver table
print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")

try:
    df.write \
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
    spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY OrderId, OrderLineNumber").show(10, truncate=False)

    print(f"🎉 OrderLine data load complete!")

except Exception as e:
    print(f"❌ Error loading data to table: {str(e)}")
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
