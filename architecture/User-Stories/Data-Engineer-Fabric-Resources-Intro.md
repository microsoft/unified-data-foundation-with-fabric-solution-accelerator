**Title: Fabric Resources Organized into Folders** 

Fabric resources are organized into below folders (some has sub folders): 

1. databricks: mirrored azure databricks calalog 
2. lakehouses: medallion lakehoueses in Fabric: bronze, silver, and gold
3. notebooks: PySpark notebooks for data models, data processing, and data management
4. reports: PowerBI sementic models and dashboards   



**Talk track** 

The data engineer can browse the resources in each folder and examines the code. For example, the data engineer Claudette Mukarukundo opens folder named notebooks, she will see below subfolders



1. bronze_to_silver: contains notebooks to process data in bronze lakehouse and populate data models in the silver lakehouse
2. data_management: contains notebooks to truncate and delete tables if a process needs to be rerun 
3. trouble_shooting: a folder contains troubleshooting notebooks and user can add notebooks to this folder as needed 
4. schema: contains notebooks to create data models
5. silver_to_gold: contains notebooks to take data from silver tier with necessary processing and then insert data to tables in gold lakehouse 
6. 

You will also see two runner notebooks:

1. run_bronze_to_silver: this notebok will run all the notebooks related to data processing from bronze to silver 
2. run_silver_to_gold: this notebook runs all the notebooks related to data processing from silver to gold 



**Core tech** 

One Lake 

Lakehouse 

Fabric data mirroring

Fabric data engineering 

Fabric PowerBI 



**CELA disclaimer**  
Terms displayed or discussed are for explanation/education only. Such terms may differ from your agreement. ​