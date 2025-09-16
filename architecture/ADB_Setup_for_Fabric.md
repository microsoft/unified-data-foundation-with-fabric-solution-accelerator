## How to Enable External Data Access in Azure Databricks

If you cannot find "Advanced Settings" in the Azure portal, follow these steps:

1. **Go to Azure Databricks workspace in Azure Portal**
   - Open the Azure Portal: https://portal.azure.com
   - Search for your Databricks workspace and select it.

2. **Navigate to Workspace Settings**
   - In the left menu, look for "Settings" or "Workspace Settings".
   - If you do not see "Advanced" or "External Data Access", check under "Networking" or "Security".

3. **Enable External Data Access**
   - Look for a toggle or option labeled "External Data Access" or "Allow access to external data sources".
   - Set it to "Enabled".
   - Save changes.

4. **If you still cannot find it:**
   - You may need to be an Azure admin or have owner permissions.
   - The setting may be restricted by your organization's policies.
   - Contact your Azure administrator or Databricks support for assistance.

5. **Documentation Reference**
   - [Azure Databricks External Data Access](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/workspace-configurations/external-data-access)

**Note:**  
Settings may change based on Azure Databricks version and your organization's configuration. If you are blocked, escalate to your Azure admin or open a support ticket.

