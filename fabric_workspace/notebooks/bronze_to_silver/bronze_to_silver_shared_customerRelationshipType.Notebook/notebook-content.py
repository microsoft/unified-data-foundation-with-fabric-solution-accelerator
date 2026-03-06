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

# CELL ********************


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # Load Bronze Data to Silver Table - CustomerRelationshipType
# 
# ## Overview
# Load CustomerRelationshipType sample data from Bronze lakehouse files into Silver lakehouse table.
# 
# ## Data Flow
# - **Source**: Bronze Lakehouse /Files/samples/fabric/shared/CustomerRelationshipType_Samples.csv
# - **Target**: Silver Lakehouse shared.CustomerRelationshipType table (Delta table)
# - **Process**: Read CSV, validate schema, load to Delta table
# 
# ---

# CELL ********************

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, sum
import os
import sempy.fabric as fabric

# Configuration - Using correct Fabric cross-lakehouse path from Fabric portal
# Get workspace ID dynamically at runtime (avoids issues with spaces in workspace names)
WORKSPACE_ID = fabric.get_notebook_workspace_id()

# Get lakehouse ID dynamically (avoids issues with lakehouse names)
lakehouse_properties = mssparkutils.lakehouse.get("maag_bronze")
SOURCE_LAKEHOUSE_ID = lakehouse_properties.id

SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_fabric/shared/CustomerRelationshipType_Samples.csv"

TARGET_SCHEMA = "shared"
TARGET_TABLE = "customerrelationshiptype"
TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"

print(f"🔄 Loading CustomerRelationshipType data")
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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Validate and conform to target schema
print(f"🔍 Validating data quality...")

# Check for required columns
required_columns = ["CustomerRelationshipTypeId", "CustomerRelationshipTypeName", "CustomerRelationshipTypeDescription"]
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    print(f"❌ Missing required columns: {missing_columns}")
    raise ValueError(f"Required columns missing: {missing_columns}")

print(f"✅ Schema validation passed")

# Check data quality
from pyspark.sql.functions import sum as spark_sum
null_counts = df.select([spark_sum(col(c).isNull().cast("int")).alias(c) for c in df.columns]).collect()[0]
print(f"\n📊 Data Quality Check:")
for col_name in df.columns:
    null_count = null_counts[col_name]
    if null_count > 0:
        print(f"  {col_name}: {null_count} null values")
    else:
        print(f"  {col_name}: ✅ No nulls")

# Show value distributions
print(f"\n🎯 CustomerRelationshipType Distribution:")
df.groupBy("CustomerRelationshipTypeId").count().orderBy("CustomerRelationshipTypeId").show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Load data to Silver table
print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")

try:
    # Write to Delta table in Silver lakehouse
    df.write \
      .format("delta") \
      .mode("overwrite") \
      .option("overwriteSchema", "true") \
      .saveAsTable(TARGET_FULL_PATH)
    
    print(f"✅ Data loaded successfully to {TARGET_FULL_PATH}")
    
    # Verify the load
    result_count = spark.sql(f"SELECT COUNT(*) as count FROM {TARGET_FULL_PATH}").collect()[0]["count"]
    print(f"📊 Records in target table: {result_count}")
    
    # Show sample of loaded data
    print(f"\n📖 Sample from Silver table:")
    spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY CustomerRelationshipTypeId").show(10, truncate=False)
    
    print(f"🎉 CustomerRelationshipType data load complete!")
    
except Exception as e:
    print(f"❌ Error loading data to table: {str(e)}")
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
