# Provisioning Azure Databricks

This guide helps an organization to set up  set up Azure Databricks for Microsoft Fabric Mirrored Catalog. For more, see [Microsoft Fabric Mirrored Catalog From Azure Databricks](https://learn.microsoft.com/en-us/fabric/mirroring/azure-databricks).

---

## Prerequisites

- Microsoft Fabric is already provisioned. [Provisioning Microsoft Fabric](./SetupFabric.md)
- You have access to the Azure Portal and permission to create resources (or ask your Azure admin).

---

## Step 1: Create Azure Databricks workspace
You can create an Azure Databricks workspace in several ways (Azure Portal, Databricks CLI, ARM/Terraform templates). The fastest method is the Azure Portal — see Microsoft’s guide: [Deploy a workspace using the Azure Portal](https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace) for full details. The steps below walk through the Portal-based creation..


1. Go to the [Azure Portal](https://portal.azure.com/).
2. Click **Create a resource** and search for "Azure Databricks".
3. Click **Create** and fill in the required fields:
   - Choose your Subscription and Resource Group (or create a new one).
   - Enter a Workspace Name.
   - Select the **Premium** pricing tier.
![create DataBricks workspace](../docs/images/deployment/databricks-create-workspace.png)

4. Click **Review + Create** and then **Create**.
5. When deployment is complete, click **Go to resource**.
6. Click **Launch Workspace** and copy the workspace URL for later.
![databricks connection new](../docs/images/deployment/databricks-workspace-url.png)

---

## Step 2: Add Users and Admins

1. In your Databricks workspace, click your user icon (top right) > **Settings**.
2. Go to **Identity and access** > **Users**.
3. Click **Manage** and add users who need access.
4. To make a user an admin: click the three dots `...` next to their name, choose **Edit**, and turn on **Admin access**.


![databricks workspace user management](../docs/images/deployment/databricks-manage-workspace-users.png)

---

## Step 3: Enable External Data Access

External data access is required for Fabric to mirror Databricks data. Request your global tenant administrator to help you to set up this. 

1. In Databricks workspace, click the **Catalog** icon (left menu).
2. Click the **gear** icon at the top of the Catalog pane and select **Metastore**.
3. On the **Details** tab, enable **External data access**.
4. If you see a message that only a global admin can enable this, ask your Azure admin for help. When complete the admin will see this view:
  
  
  ![databricks external data access enabled](../docs/images/deployment/databricks-external-data-access-enabled.png)

---

## Step 4: Find Required Values in Databricks Workspace
You will need the following values for deployment process later. Be sure to record them for future reference.

- **Workspace URL:**  
   - Use the URL copied in Step 1 → Substep 6.
   

- **Personal Access Token (PAT):**  
  - In Databricks workspace, click your profile icon (top-right) and select Settings. 
  - Navigate to **Developer → Access tokens → Manage.** 
  - Click **Generate new token**, add a comment, and set the lifetime.
  - Copy the token (it begins with `dapi...`) and store it in a secure location. You will not be able to view this token again after closing the dialog.
  
  
  ![Generate Databricks PAT](./images/deployment/2-DatabricksGeneratePAT.png)  

- **Cluster ID (create a cluster / compute to obtain this):**
  If you do not yet have a cluster, create one before running the deployment scripts (instructions below).


  **How to create a cluster:**
    1. In your Databricks workspace, click **Compute** → **Create Compute**. 
    ![Create Compute](./images/deployment/ADB-Cluster1.png)  
    2. Enter a **Compute name**, choose the runtime version, worker type and node count appropriate for your workloads.
    3. Click **Create**. Wait until the cluster status displays `Running` (or `Started`) — you can verify this by the green dot next to the cluster name.
    ![Compute running](./images/deployment/ADB-Cluster2.png)


  **How to get the Cluster ID:**

  1. Open your Databricks workspace.
  2. In the left navigation pane, go to Compute.
  3. Select the cluster you want to inspect.
  4. On the cluster details page, click the ... (More Actions) menu in the top-right corner.
  5. Choose View JSON from the dropdown. A JSON window will open with the cluster configuration details.
    ![Compute running](./images/deployment/ADB-Cluster3.png)
  6.  Search (Ctrl + F) for "cluster_id".
  7.  Copy the value next to "cluster_id" — that’s your Cluster ID.
    ![Compute running](./images/deployment/ADB-Cluster4.png)
    

    >Notes: Creating a cluster requires appropriate Databricks permissions. If you cannot create a cluster, ask your administrator to provision one or supply you with the Cluster ID.

- **Catalog Managed Location:**
  - In Databricks workspace, go to **Catalogs → Settings**.  


    ![Catalog Settings](./images/deployment/4-databricksSettingIcon.png) 

  - Under **External Location**, select your location to view its details.


    ![External Location](./images/deployment/5-DatabricksExternalLocations.png) 

  - The managed location is shown as a URL (commonly starting with `abfss://`).  

    ![Catalog Location](./images/deployment/6-DatabricksCatalogLocation.png)  

---

## Step 5: Connect Databricks to Fabric

1. In your Fabric workspace, click **+ New item**.
2. Search for "Azure Databricks" and select **Mirrored Azure Databricks Catalog**.
3. Choose **New connection**.
4. Enter your Databricks workspace URL (copied earlier, e.g., `https://adb-<WorkspaceID>.azuredatabricks.net`).
5. Name your connection, select **Microsoft Entra ID** for authentication, and sign in.
6. Click **Connect**.

After setup, you can reuse this connection by choosing **Existing connection**.

---

## Next Steps


For deploying Databricks resources, follow instructions the [Deployment Guide for Databricks](./DeploymentGuideDatabricks.md).
