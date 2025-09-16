# Fabric Setup for Azure Databricks Lakehouse Integration

## 1. Prerequisites

- You must have access to both Microsoft Fabric and Azure Databricks.
- Your Azure Databricks workspace must have **External Data Access** enabled.
- You need permissions to create shortcuts and mirror tables in Fabric.

## 2. Enable External Data Access in Azure Databricks

- See Databricks ADB_Setup_for_Fabric.md for what to set up in Azure Databricks 
- This is required for Fabric to access Databricks tables via shortcut or mirroring.

## 3. Create a Shortcut in Fabric to Azure Databricks Lakehouse

1. **Open Fabric Workspace**
   - Go to your Fabric workspace in the Fabric portal.

2. **Add a Shortcut**
   - In your Lakehouse, click **New > Shortcut**.
   - Choose **Azure Databricks** as the source.
   - Authenticate and select your Databricks workspace and target table or folder.

3. **Configure Shortcut**
   - Name your shortcut.
   - Confirm the path and permissions.
   - Save the shortcut.

## 4. Access Databricks Data in Fabric

- Use the shortcut in Fabric Notebooks, Dataflows, or Pipelines.
- Example: Read data from the shortcut using Spark or SQL in Fabric.

## 5. Troubleshooting

- If you see:  
  `Unable to access table data in the mirrored catalog as External Data Access is disabled. This is a prerequisite for mirroring.`
  - Go to Azure Databricks and enable External Data Access.
  - Ensure you have the correct permissions in both Fabric and Databricks.

## 6. References

- [Fabric Shortcuts Documentation](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-shortcuts)
- [Azure Databricks External Data Access](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/workspace-configurations/external-data-access)

---
