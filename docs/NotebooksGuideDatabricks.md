# Guide to Deploy Databricks Notebooks

There are total **8 Databricks notebooks** provided. 
Together, they automate creating schemas, loading sample data, and managing tables in Databricks.  


## Orchestrator Notebook (1 file)

Path: `src/databricks/notebooks/run_bronze_to_adb.ipynb`  

This is the main notebook that controls the workflow. It:  
1. Creates a schema and models in Databricks.    
2. Loads the existing csv data into Delta tables:  
   - `sales.orders`  
   - `sales.orderLines`  
   - `sales.payments`  


## Schema & Model Setup (2 file)

Path: `src/databricks/notebooks/schema/model_salesadb.ipynb`  

   - `model_salesadb.ipynb`: This notebook creates the `sales` schema and defines the models that will hold the data. Once executed successfuly, this notebook creates 3 tables into sales schema naming `order`, `orderline`, `orderpayment`.
   - `manage_unity_catalog_permission.ipynb`: This notebook gives the necessary permissions to the user running the deployment scripts, so they can mirror catalogs and create table shortcuts in Fabric.


## Data Loading Notebooks (3 files)

Path: `src/databricks/notebooks/bronze_to_adb_silver/`  

These three notebooks load sample CSV data into Delta tables:  
- `bronze_to_adb_salesadb_order.ipynb` → loads orders  
- `bronze_to_adb_salesadb_orderLine.ipynb` → loads orderlines  
- `bronze_to_adb_salesadb_orderPayment.ipynb` → loads orderpayments  

After running them, the  tables are filled with sample data.  


## Data Management & Cleanup (2 files)

Path: `src/databricks/notebooks/data_management/`  

These notebooks help reset the environment:  
- `truncate_all_tables.ipynb` → clears all rows from tables (keeps structure).  
- `drop_all_tables.ipynb` → deletes the tables entirely.  

---

With this setup, you can:  
- Deploy notebooks easily into Databricks.  
- Load sample sales data for testing.  
- Create the required catalog and schema in Databricks, and assign the necessary privileges to users for managing and accessing the data.
- Reset or clean up the environment anytime.  
