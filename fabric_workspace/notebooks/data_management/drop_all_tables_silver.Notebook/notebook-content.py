# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
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

# # Drop All Tables and Schemes
# 
# This notebook drops all tables in the listed schemes (`shared`, `salesfabric`, `salesadb`, `finance`) if they exist, and then drops the schemes themselves.
# 
# - Skips schemes and tables that do not exist.
# - Prints status for each drop operation.

# CELL ********************

# Drop tables in multiple schemas if they exist
def drop_tables(schema_name, tables):
    try:
        existing_tables = set(spark.sql(f"SHOW TABLES IN {schema_name}").select('tableName').rdd.flatMap(lambda x: x).collect())
    except Exception as e:
        print(f"⚠️ Schema {schema_name} not found. Skipping all tables in this schema.")
        return
    for table in tables:
        full_table = f"{schema_name}.{table}"
        if table in existing_tables:
            print(f"🗑️ Dropping {full_table} ...")
            try:
                spark.sql(f"DROP TABLE IF EXISTS {full_table}")
                print(f"✅ {full_table} dropped!")
            except Exception as e:
                print(f"⚠️ Could not drop {full_table}: {e}")
        else:
            print(f"⚠️ Table {full_table} does not exist. Skipping.")

# Define schemas and tables
schemas_tables = {
    "shared": [
        "customer", "customeraccount", "customerrelationshiptype",
        "customertradename", "location", "product", "productcategory"
    ],
    "salesfabric": ["order", "orderline", "orderpayment"],
    "salesadb": ["order", "orderline", "orderpayment"],
    "finance": ["account", "invoice", "payment"]
}

# Drop all tables
for schema, tables in schemas_tables.items():
    print(f"\n--- Dropping tables in schema: {schema} ---")
    drop_tables(schema, tables)

print(f"\n🎉 ALL SELECTED TABLES DROPPED!")

# Drop schemas if they exist
schemas = ["shared", "salesfabric", "salesadb", "finance"]
for schema in schemas:
    print(f"🗑️ Dropping schema {schema} ...")
    try:
        tables_left = spark.sql(f"SHOW TABLES IN {schema}").select('tableName').rdd.flatMap(lambda x: x).collect()
        if tables_left:
            print(f"⚠️ Cannot drop schema {schema}: Tables still exist: {tables_left}")
        else:
            spark.sql(f"DROP DATABASE IF EXISTS {schema} CASCADE")
            print(f"✅ Schema {schema} dropped!")
    except Exception as e:
        print(f"⚠️ Could not drop schema {schema}: {e}")

print(f"\n🎉 ALL Schemas DROPPED!")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
