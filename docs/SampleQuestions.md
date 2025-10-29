# Sample Questions

To help you get started, here are some **Sample Prompts** you can ask in the app:

## **Sections**
Select the team option from the top left section and click **continue** button.

![GenerateDraft](images/maag-sample.png)

### **Fabric Testing**
_Sample Steps:_ <br>
- Validate 4 folders are created successully in the Fabric Workspace <br>
  - databricks
  - lakehouses
  - notebooks
  - reports 
- Browse the resources in each folder and subfolders.
- Open notebooks folder and verify below resourcses:
  - **bronze_to_silver:** Contains 16 notebooks to process data in bronze lakehouse and populate data models in the silver lakehouse
  - **data_management:** Contains 5 notebooks to truncate and delete tables if a process needs to be rerun
  - **schema:** Contains  8 notebooks to create data models
  - **silver_to_gold:** Contains 19 notebooks to take data from silver tier with necessary processing and  insert data to tables in gold lakehouse
- You will also see two runner notebooks:
  - **run_bronze_to_silver:** This notebook runs all the notebooks related to data processing from bronze to silver
  - **run_silver_to_gold:** This notebook runs all the notebooks related to data processing from silver to gold
- 1. Navigate to the notebooks/schema folder in the Fabric workspace.
  2. Verify that notebooks are available to create data models for the following domains:
	 - Customer
	 - Product
	 - Sales
	 - Finance
  
- 1. Open the targeted notebook **'model_shared_gold'** in the Fabric workspace.
  2. Confirm that the notebook interface loads successfully without errors.
  3. Review the notebook content to verify the database schema and table structures referenced or defined within it.
     
### **Lakehouse Testing**  
- 1. Navigate to the lakehouses folder and verify that three lakehouses are displayed.
  2. Open the maag_gold lakehouse and confirm the schema and list of tables are visible.
  3. Access the SQL endpoint associated with maag_gold.
  4. Run T-SQL queries (e.g., **SELECT COUNT(*) FROM [maag_gold].[salesadb].[order]**) and verify that valid row counts are returned.

### **Notebook Testing**  
- 1. Navigate to the notebooks folder.
  2. Opens the bronze_to_silver subfolder.
  3. Observes the list of related notebooks.
  4. pen any notebook  verify that the notebook details are loaded correctly.
- 1. Navigate to the notebooks folder.
  2. Opens the silver_to_gold subfolder.
  3. Observes the list of related notebooks.
  4. Open any notebook  verify that the notebook details are loaded correctly.
- 1. Navigate to the notebooks folder.
  2. Opens the  data_management subfolder.
  3. Observes the list of related notebooks.
  4. Open any notebook  verify that the notebook details are loaded correctly. e.g. truncate_all_tables_gold
- 1. Navigate to the notebooks folder.
  2. Verify that two runner notebooks is displayed.
  3. Open any notebook  verify that the notebook details are loaded correctly.         

### **Power BI Testing** 
- Open the Fabric  workspace and Open reports folder and navigate to sales_dashboard, 
- 1. Observe YOY Net sales Comparison chart.
  2. Observe the trend line and identify any downward trend in the data.
  3. Hover over a specific year on the trend line(e.g. 2022)
  4. Verify that the exact Net Sales value for that year is displayed in the tooltip.
- 1. Next, Observe the Revenue Distribution by Customer Segment visual.
  2. Review the distribution across customer segments:
      - Individual
      - Business
      - Government
  3. Compare the thresholds and contribution of each segment to overall revenue.   

### **Azure Databricks and Fabric integration**    
- 1. Open fabric workspace and navigate to databricks folder
  2. Navigate to **maagcatalog** mirrored Azure Databricks and validate the list of tables under sales schema - order, orderline and orderpayment

### **Purview Testing**   
- Open Purview and select Data Map
- Navigate Data Sources and validate Fabric Data source is Available in Collection created 
  1. Verify Fabric is successfully connected to Microsoft Purview, and Purview collections appear in Fabric.
- **Scan and Report**
  1. Navigate to Data Map -> Monitoring
  2. Observe the Scan details. See information on Cards and Graph  
- Data Lineage  and metdata review
  1. Navigate to Unified Catalog -> Catalog management -> Data Products
  2. Select Data Product Sales Resources.
  3. Open maag_gold. Observe Data asset lineage   
       
