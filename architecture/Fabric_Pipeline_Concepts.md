# Fabric Pipeline Concepts (Quick Start)

## What is a Fabric Pipeline?
A pipeline in Microsoft Fabric lets you automate and orchestrate data workflows, such as running notebooks, moving data, and creating tables.

## How to Use Pipelines

1. **Create a Pipeline**
   - Go to your Fabric workspace and select "Pipelines".
   - Click "New pipeline".

2. **Add Activities**
   - Add a "Notebook Activity" for each notebook you want to run.
   - Select the notebook file (e.g., `Model_Shared_Data.ipynb`, `Model_Sales_Domain.ipynb`).

3. **Set Parameters**
   - For each notebook activity, you can pass parameters (e.g., `SCHEMA_NAME`).
   - In your notebook, access parameters using:
     ```python
     SCHEMA_NAME = notebook_param.get("SCHEMA_NAME", "default_schema")
     ```

4. **Connect Activities (Dependencies)**
   - You can control the flow between activities using hooks:
     - **on success:** triggers next activity only if previous activity succeeds (recommended for sequential execution).
     - **on fail:** triggers next activity only if previous activity fails (useful for error handling).
     - **on skip:** triggers if previous activity is skipped.
     - **on completion:** triggers regardless of success or failure.

5. **Run and Monitor**
   - Save and run the pipeline.
   - Monitor execution and check logs for results.

## Best Practices

- Use parameters to make notebooks reusable.
- Run schema/table creation notebooks first, then data loading notebooks.
- Keep pipelines simple and modular.

## References

- [Fabric Pipeline Documentation](https://learn.microsoft.com/en-us/fabric/data-engineering/pipelines/)
- [Notebook Activity Parameters](https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity#parameters)

---
- Create a new pipeline.
- Add activities (e.g., "Run Notebook", "Copy Data").
- Configure triggers and parameters.
- Test and monitor pipeline runs.

## 6. References

- [Microsoft Fabric documentation - Microsoft Fabric | Microsoft Learn](https://learn.microsoft.com/en-us/fabric/)
- [Data Engineering in Microsoft Fabric documentation - Microsoft Fabric | Microsoft Learn](https://learn.microsoft.com/en-us/fabric/data-engineering/)
- [Lakehouse Architecture](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview)
- [Notebook activity - Microsoft Fabric | Microsoft Learn](https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity)

## 7. Passing Parameters to Notebooks in Fabric Pipelines

- When you add a notebook activity to a pipeline, you can pass parameters to the notebook.
- Parameters allow you to make your notebook dynamic (e.g., pass file paths, table names, dates).

**How to use parameters:**
1. **Define parameters in your notebook code:**
   ```python
   # In the first cell of your notebook
   dbutils.widgets.text("input_path", "")
   input_path = dbutils.widgets.get("input_path")
   print(f"Input path: {input_path}")
   ```

2. **Set parameters in the pipeline activity:**
   - In the pipeline UI, select the notebook activity.
   - Add parameters (name and value) in the settings pane.
   - The names must match those defined in your notebook (e.g., `input_path`).

**Supported parameter types:**
- Text (string)
- Numeric (int, float)
- Boolean

**Best practices:**
- Always define default values for parameters in your notebook.
- Document expected parameters at the top of your notebook.
- Use parameters for file paths, table names, dates, and other runtime values.

**References:**
- [Notebook activity parameters in Fabric](https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity#parameters)

## 8. Example: Executing Model_Sales_Domain.ipynb in a Pipeline

- Add a **Notebook Activity** to your pipeline.
- Select `Model_Sales_Domain.ipynb` as the notebook to run.
- If your notebook does not require parameters, you can leave the parameters section empty.
- If you want to pass parameters (e.g., schema name, table names), define them in the notebook using `dbutils.widgets` and set them in the pipeline activity.

**Example parameter usage in notebook:**
```python
# At the top of Model_Sales_Domain.ipynb
dbutils.widgets.text("SCHEMA_NAME", "sales")
SCHEMA_NAME = dbutils.widgets.get("SCHEMA_NAME")
print(f"Using schema: {SCHEMA_NAME}")
```

**Pipeline setup steps:**
1. Create a pipeline in Fabric.
2. Add a notebook activity and select `Model_Sales_Domain.ipynb`.
3. (Optional) Add parameters if needed.
4. Save and run the pipeline.

**Best Practice:**  
Start with schema/table creation notebooks first, then add data loading and transformation notebooks as additional activities in your pipeline.

---

**Tip:**  
Start with a simple pipeline that creates schemas and loads data, then expand with more steps and automation as needed.

## How to Manually Run a Pipeline in Fabric

1. Open your pipeline in the Fabric workspace.
2. Click the **Run** button (usually at the top right).
3. If prompted, select or confirm any required parameters.
4. Monitor the pipeline run in the UI:
   - You will see the status of each activity (e.g., running, succeeded, failed).
   - Click on activities to view logs and outputs.
5. Review results and logs to confirm successful execution.

**Tip:**  
You can re-run the pipeline as needed, and check the history of previous runs for troubleshooting.
