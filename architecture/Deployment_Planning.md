

# **Deployment Plan and Tasks**

#### 1. Environment Setup: Guide End Users on how to set up Fabric, Databricks, and Purview 

- Fabric Setup (Fabric_Setup.md): Fabric Workspace creation and Adding Users (**Alvaro**)
- Databricks Setup (Databricks_Setup.md): Databricks workspace creation and Adding Users (**Anish/PSL**)
- Power BI Semantic Model and Data Sources set up (PBI_Setup.md) to use the data loaded to Gold Lakehouse ((**Anish/PSL**))
- Purview Set up (Purview_Setup.md): Purview setup and integration with Fabric (**James**)

#### 2. Automated Resource Deployment (Fabric) - Alvaro 

- Fabric: After workspace is created. scripts / python programs that automated below tasks 

  - Creation of Bronze, Silver, and Gold Lakehouses with a set of names such as **maag_bronze**, **maag_silver**, and **maag_gold**. Current fabric notebooks are using these names. 
  - **Workspace and Lakehouse Name Update**:  (1) The code is expecting workspace name "Fabric_MAAG". When the deployed workspace name is different from this, will need to replace the value in all fabric PySpark Notebooks. (2) If the lakehouse names are other than above three names, we need to run scripts to replace the coded names in fabric PySpark Notebooks.
  - If workspace name is different than current 
  - Create Top level folders in Fabric Workspace to organize resources 
    - lakehouses 
    - notebooks 
    - reports 
  - move three lakehouses into folder '**lakehouses**'
    - maag_bronze
    - maag_silver
    - maag_gold
  - subfolder under '**notebooks**'
    - bronze_to_silver
    - data_management
    - schema
    - silver_to_gold 
  - no subfolder under '**reports**'  (we will only have files)
  - scripts to import from ado/github repo folder src/fabric/notebooks into Fabric workspace into above folders 

#### 3. Automated Resource Deployment (Fabric) - Lakehouse Attachment and detachment if needed - Alvaro 

There are two sets of PySpark notebooks. One set is attached to silver lakehouse (maag_silver), another set needs to be attached to gold lakehouse (maag_gold).

- Silver: fabric/notebooks/run_bronze_to_silver.ipynb and all notebooks in abric/notebooks/bronze_to_silver 
- Gold: fabric/notebooks/run_silver_to_gold.ipynb and all notebooks in abric/notebooks/silver_to_gold 

#### 4. Automated Sample Data uploading to Bronze Lakehouse (**Alvaro**)

On GitHub repo, the sample data is stored in file structure like this 

- infra/data/samples_databricks/sales 
- infra/data/samples_fabric/finance 
- infra/data/samples_fabric/sales
- infra/data/samples_fabric/shared 

Files in above subfolders will be uploaded to Bronze Lakehouse into corresponding folders (will need to create this folder structure first before able to upload files to each folder)

- Files/samples_databricks/sales 
- Files/samples_fabric/finance 
- Files/samples_fabric/sales
- Files/samples_fabric/shared 

#### 5. Automated Resource Deployment (Databricks) - Anish/PSL 

- Create folder structure in azure databricks for notebooks, follow the structure set up in src/databricks/notebooks (please work with Yamini on details)
- Upload source files from infra/data/samples_databrics to appropriate folder in databricks (use what Yamini has set up)

The details has been documented in architecture/**DatabricksWork.pptx**

#### 6. Automated Resource Deployment (Purview) - James 

There are discussions on either automate this or keep it manual with markdown readme file. Currently thinking of manual steps. 

Possible rescuable Code (or portion of it) from **Mike Swantek**. James and Mike to work on any automation scripts to be used. 

[GitHub - mswantek68/fabric-purview-domain-integration](https://github.com/mswantek68/fabric-purview-domain-integration).



