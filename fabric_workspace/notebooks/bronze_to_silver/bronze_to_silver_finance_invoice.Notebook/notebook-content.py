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

# # Load Bronze Data to Silver Table - Invoice
# 
# ## Overview
# Load Invoice sample data from Bronze lakehouse files into Silver lakehouse table.
# 
# ## Data Flow
# - **Source-Fabric**: Bronze Lakehouse/Files/samples_fabric/finance/Invoice_Samples_Fabric.csv
# - **Source-ADB**: Bronze Lakehouse/Files/samples_databricks/finance/Invoice_Samples_ADB.csv
# - **Target**: Silver Lakehouse.finance.Invoice table 
# - **Process**: Read CSV, validate schema, load to Delta table
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

FABRIC_SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_fabric/finance/Invoice_Samples_Fabric.csv"


TARGET_SCHEMA = "finance"
TARGET_TABLE = "invoice"
TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"

print(f"🔄 Loading Fabric Invoice data")
print(f"📂 Source: {FABRIC_SOURCE_PATH}")
print(f"🎯 Target: {TARGET_FULL_PATH}")

# Read CSV from Bronze lakehouse
invoice_df = spark.read.option("header", "true").option("inferSchema", "true").csv(FABRIC_SOURCE_PATH)

print(f"✅ Data loaded successfully")
print(f"📊 Records: {invoice_df.count()}")
print(f"📋 Columns: {invoice_df.columns}")

# Display sample data
print(f"\n📖 Sample data:")
invoice_df.show(10, truncate=False)

required_columns = [
    "InvoiceId", "InvoiceNumber", "CustomerId", "OrderId", "InvoiceDate", "DueDate",
    "SubTotal", "TaxAmount", "TotalAmount", "InvoiceStatus", "CreatedBy"
]

missing_columns = [c for c in required_columns if c not in invoice_df.columns]
if missing_columns:
    print(f"⚠️ Warning: Missing columns in source data: {missing_columns}")
else:
    print(f"✅ All required columns present in source data.")

for col_name in missing_columns:
    if col_name in ["SubTotal", "TaxAmount", "TotalAmount"]:
        invoice_df = invoice_df.withColumn(col_name, F.lit(0.0))
    else:
        invoice_df = invoice_df.withColumn(col_name, F.lit(""))

invoice_df = invoice_df.withColumn("InvoiceId", col("InvoiceId").cast(StringType()))
invoice_df = invoice_df.withColumn("InvoiceNumber", col("InvoiceNumber").cast(StringType()))
invoice_df = invoice_df.withColumn("CustomerId", col("CustomerId").cast(StringType()))
invoice_df = invoice_df.withColumn("OrderId", col("OrderId").cast(StringType()))
invoice_df = invoice_df.withColumn("InvoiceDate", col("InvoiceDate").cast(DateType()))
invoice_df = invoice_df.withColumn("DueDate", col("DueDate").cast(DateType()))
invoice_df = invoice_df.withColumn("SubTotal", col("SubTotal").cast(DoubleType()))
invoice_df = invoice_df.withColumn("TaxAmount", col("TaxAmount").cast(DoubleType()))
invoice_df = invoice_df.withColumn("TotalAmount", col("TotalAmount").cast(DoubleType()))
invoice_df = invoice_df.withColumn("InvoiceStatus", col("InvoiceStatus").cast(StringType()))
invoice_df = invoice_df.withColumn("CreatedBy", col("CreatedBy").cast(StringType()))
invoice_df = invoice_df.select(required_columns)

# Data quality checks
print(f"\n📊 Data Quality Check:")
null_counts = invoice_df.select([F.sum(col(c).isNull().cast("int")).alias(c) for c in required_columns]).collect()[0]
for col_name in required_columns:
    null_count = null_counts[col_name]
    if null_count > 0:
        print(f"  {col_name}: {null_count} null values")
    else:
        print(f"  {col_name}: ✅ No nulls")

# Show value distributions for InvoiceStatus
print(f"\n🎯 InvoiceStatus Distribution:")
invoice_df.groupBy("InvoiceStatus").count().orderBy("InvoiceStatus").show()

# Load data to Silver table
print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")
try:
    invoice_df.write \
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
    spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY InvoiceId").show(10, truncate=False)
    
    print(f"🎉 Invoice data load complete!")

except Exception as e:
    print(f"❌ Error loading data to table: {str(e)}")
    raise
# --- End Fabric Channel ---

# CELL ********************

# --- ADB Channel ---
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

ADB_SOURCE_PATH = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/Files/samples_fabric/finance/Invoice_Samples_ADB.csv"

TARGET_SCHEMA = "finance"
TARGET_TABLE = "invoice"
TARGET_FULL_PATH = f"{TARGET_SCHEMA}.{TARGET_TABLE}"

print(f"🔄 Loading ADB Invoice data")
print(f"📂 Source: {ADB_SOURCE_PATH}")
print(f"🎯 Target: {TARGET_FULL_PATH}")

# Read CSV from Bronze lakehouse
invoice_df = spark.read.option("header", "true").option("inferSchema", "true").csv(ADB_SOURCE_PATH)

print(f"✅ Data loaded successfully")
print(f"📊 Records: {invoice_df.count()}")
print(f"📋 Columns: {invoice_df.columns}")

# Display sample data
print(f"\n📖 Sample data:")
invoice_df.show(10, truncate=False)

required_columns = [
    "InvoiceId", "InvoiceNumber", "CustomerId", "OrderId", "InvoiceDate", "DueDate",
    "SubTotal", "TaxAmount", "TotalAmount", "InvoiceStatus", "CreatedBy"
]

missing_columns = [c for c in required_columns if c not in invoice_df.columns]
if missing_columns:
    print(f"⚠️ Warning: Missing columns in source data: {missing_columns}")
else:
    print(f"✅ All required columns present in source data.")

for col_name in missing_columns:
    if col_name in ["SubTotal", "TaxAmount", "TotalAmount"]:
        invoice_df = invoice_df.withColumn(col_name, F.lit(0.0))
    else:
        invoice_df = invoice_df.withColumn(col_name, F.lit(""))

invoice_df = invoice_df.withColumn("InvoiceId", col("InvoiceId").cast(StringType()))
invoice_df = invoice_df.withColumn("InvoiceNumber", col("InvoiceNumber").cast(StringType()))
invoice_df = invoice_df.withColumn("CustomerId", col("CustomerId").cast(StringType()))
invoice_df = invoice_df.withColumn("OrderId", col("OrderId").cast(StringType()))
invoice_df = invoice_df.withColumn("InvoiceDate", col("InvoiceDate").cast(DateType()))
invoice_df = invoice_df.withColumn("DueDate", col("DueDate").cast(DateType()))
invoice_df = invoice_df.withColumn("SubTotal", col("SubTotal").cast(DoubleType()))
invoice_df = invoice_df.withColumn("TaxAmount", col("TaxAmount").cast(DoubleType()))
invoice_df = invoice_df.withColumn("TotalAmount", col("TotalAmount").cast(DoubleType()))
invoice_df = invoice_df.withColumn("InvoiceStatus", col("InvoiceStatus").cast(StringType()))
invoice_df = invoice_df.withColumn("CreatedBy", col("CreatedBy").cast(StringType()))
invoice_df = invoice_df.select(required_columns)

# Data quality checks
print(f"\n📊 Data Quality Check:")
null_counts = invoice_df.select([F.sum(col(c).isNull().cast("int")).alias(c) for c in required_columns]).collect()[0]
for col_name in required_columns:
    null_count = null_counts[col_name]
    if null_count > 0:
        print(f"  {col_name}: {null_count} null values")
    else:
        print(f"  {col_name}: ✅ No nulls")

# Show value distributions for InvoiceStatus
print(f"\n🎯 InvoiceStatus Distribution:")
invoice_df.groupBy("InvoiceStatus").count().orderBy("InvoiceStatus").show()

# Load data to Silver table
print(f"💾 Loading data to Silver table: {TARGET_FULL_PATH}")
try:
    invoice_df.write \
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
    spark.sql(f"SELECT * FROM {TARGET_FULL_PATH} ORDER BY InvoiceId").show(10, truncate=False)
    
    print(f"🎉 Invoice data load complete!")

except Exception as e:
    print(f"❌ Error loading data to table: {str(e)}")
    raise
# --- End ADB Channel ---
