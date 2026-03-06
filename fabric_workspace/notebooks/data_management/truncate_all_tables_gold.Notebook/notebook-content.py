# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "86c1a3bb-fee7-4ce5-9f89-8466a3e8aa1e",
# META       "default_lakehouse_name": "maag_gold",
# META       "default_lakehouse_workspace_id": "8b4b90aa-74f8-4b72-8fd0-1d254ff4ee59",
# META       "known_lakehouses": [
# META         {
# META           "id": "86c1a3bb-fee7-4ce5-9f89-8466a3e8aa1e"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Truncate All Tables in all Schemes 
# 
# This notebook truncates (removes all rows from) tables in the schemas `shared`, `salesfabric`, `salesadb`, and `finance` if they exist.

# CELL ********************

# Truncate tables in multiple schemas if they exist
def truncate_tables(schema_name, tables):
    try:
        existing_tables = set(spark.sql(f"SHOW TABLES IN {schema_name}").select('tableName').rdd.flatMap(lambda x: x).collect())
    except Exception as e:
        print(f"⚠️ Schema {schema_name} not found. Skipping all tables in this schema.")
        return
    for table in tables:
        full_table = f"{schema_name}.{table}"
        if table in existing_tables:
            print(f"🔨 Truncating {full_table} ...")
            try:
                spark.sql(f"TRUNCATE TABLE {full_table}")
                print(f"✅ {full_table} truncated!")
            except Exception as e:
                print(f"⚠️ Could not truncate {full_table}: {e}")
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

# Truncate all tables
for schema, tables in schemas_tables.items():
    print(f"\n--- Truncating tables in schema: {schema} ---")
    truncate_tables(schema, tables)

print(f"\n🎉 ALL SELECTED TABLES TRUNCATED!")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
