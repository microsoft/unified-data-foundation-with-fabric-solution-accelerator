# Guide to Deployed Fabric Jupyter Notebooks 

There are total 48 Fabric notebooks and 2 scripts provided. All the notebooks and scripts will be deployed to Fabric with automated deployment process. 

#### 2 Runner Notebooks 

- In `src/fabric/notebooks` folder, there are two runner notebooks, each executing automated tasks programmed in a group of notebooks, and to be run in below sequence: 
  1. `run_bronze_to_silver.ipynb`: This notebook runs a group of notebooks with each copying raw data in specified folder/file into specified schema/table in bronze lakehouse. When successfully executed, all the raw .csv files stored in bronze lakehouse `Files/samples_fabric/finance,` `Files/samples_fabric/sales`, `Files/samples_fabric/shared` folders will be loaded into tables in schemas `finance`, `sales`, and `shared` in silver lakehouse, respectively. 
  2. `run_silver_to_gold.ipynb`: This notebook runs a group of notebooks with each copying data in specified schema/table from silver lakehouse into specified schema/table in gold lakehouse. 

#### 8 Notebooks to create schemas and tables 

- In `src/fabric/notebooks/schema` folder, there are 8 notebooks. Each notebook defines the structure of a group of tables under a specific schema. For example, `model_salesfabric_gold.ipynb` specifies the schema `salesfabric` and tables to be created in gold lakehouse. After successful execution of this notebook, three tables `order`, `orderline`, and `orderpayment` will be created under schema `salesfabric`. 

#### 5 Notebooks and 1 SQL Script for Data Management 

- In `src/fabric/data_management` folder, there are 5 notebooks and 1 SQL script. The notebooks perform data management functions, such as truncate table, drop table, and sample scripts such as `table_counts.sql` that you can use in lakehouse SQL end points to check the counts of records in tables. 

#### 16 Notebooks for loading data from .CSV files in Bronze Lakehouse to Silver Lakehouse Tables 

- In `src/fabric/notebooks/bronze_to_silver` folder, there are 16 notebooks. Each notebook defines the code to load raw .csv file in a specified Files folder in bronze lakehouse to a specified schema/table in silver lakehouse.

#### 16 Notebooks for Copying Tables in Silver Lakehouse to Gold Lakehouse Tables 

- In `src/fabric/notebooks/silver_to_gold` folder, there are 16 notebooks. Each notebook defines the code to copy data from a specified schema/table in silver lakehouse to the corresponding schema/table in gold lakehouse. 

#### 1 Sample Notebook for data analysis 

- In `src/fabric/notebooks/test_report` folder, there is a sample notebook for user to provide simple graphical report for specified data. This one does not need to be executed. It is for experiment. 

  

