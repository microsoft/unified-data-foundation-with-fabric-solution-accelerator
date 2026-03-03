# Deployment Guide

This guide walks you through deploying the Unified Data Foundation with Fabric solution accelerator to your Azure subscription.

---

## Architecture Options

Choose the architecture that best fits your organizational needs:

| Option | Architecture | Description |
|:------:|--------------|-------------|
| **1** | Microsoft Fabric | Core medallion lakehouse with Power BI dashboards |
| **2** | Fabric + Purview | Adds data governance and compliance capabilities |
| **3** | Fabric + Databricks | Adds cross-platform analytics integration |
| **4** | Fabric + Purview + Databricks | Complete enterprise solution with all components |

> **Note:** Option 1 is required as the foundation. Options 2–4 build upon it.

For detailed architecture diagrams and feature descriptions, see [Technical Architecture](./TechnicalArchitecture.md).

---

## Prerequisites

Before you begin, ensure you have the following:

| Requirement | Description |
|-------------|-------------|
| **Azure subscription** | An active Azure subscription. [Create a free account](https://azure.microsoft.com/free/) if needed. |
| **Permissions** | Contributor role and RBAC permissions at the subscription level. |
| **Fabric capacity** | Microsoft Fabric capacity of F64 or higher. |

For detailed setup instructions, see [Azure Account Setup](./AzureAccountSetUp.md).

> 💡 **Recommended:** Run the [Quota Check](./QuotaCheck.md) before deployment to verify resource availability.

---

## Deploy Option 1: Microsoft Fabric (Required)

Deploys 3 lakehouses (Bronze, Silver, Gold), 48 notebooks, 2 SQL scripts, and Power BI dashboards.

| [![Azure Cloud Shell](https://img.shields.io/static/v1?style=for-the-badge&label=Azure%20Cloud%20Shell&message=Open&color=0078D4&logo=microsoft-azure&logoColor=white)](https://shell.azure.com) | [![GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub%20Codespaces&message=Open&color=181717&logo=github&logoColor=white)](https://codespaces.new/microsoft/unified-data-foundation-with-fabric-solution-accelerator?quickstart=1) | [![Dev Container](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Container&message=Open&color=blue&logo=docker&logoColor=white)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator) |
|---|---|---|

```bash
git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
cd unified-data-foundation-with-fabric-solution-accelerator
azd auth login
azd up
```

⏱️ **Deployment time:** 15–20 minutes

### Alternative Methods

| Method | Guide |
|--------|-------|
| Manual | [Manual Deployment](./DeploymentGuideFabricManual.md) |
| Detailed | [Fabric Deployment Guide](./DeploymentGuideFabric.md) |
| Local Dev | [Local Development Setup](./LocalDevelopmentSetup.md) |

### After Deployment

- [Configure Power BI Dashboard](./DeploymentGuidePowerBI.md)
- [Fabric Notebooks Guide](./NotebooksGuideFabric.md)

---

## Deploy Option 2: Add Purview (Optional)

Adds data governance, metadata management, and compliance capabilities.

> **Prerequisite:** Complete Option 1 first.

| Step | Guide |
|:----:|-------|
| 1 | [Setup Purview](./SetupPurview.md) |
| 2 | [Configure Governance](./DeploymentGuidePurview.md) |

---

## Deploy Option 3: Add Databricks (Optional)

Add Azure Databricks for cross-platform analytics and advanced data processing capabilities.

**Prerequisite:** Complete Option 1 deployment first.

| Step | Description | Guide |
|:----:|-------------|-------|
| 1 | Provision Azure Databricks | [Setup Databricks](./SetupDatabricks.md) |
| 2 | Deploy Databricks resources | [Databricks Deployment Guide](./DeploymentGuideDatabricks.md) |

This deploys 1 Silver lakehouse, 7 notebooks, 2 SQL scripts, and sample data to Databricks.

For details on the notebooks, see [Databricks Notebooks Guide](./NotebooksGuideDatabricks.md).

---

## Deploy Option 4: Complete Solution

Deploy all components for a full enterprise data platform.

**Steps:**
1. Complete Option 1 (Fabric)
2. Complete Option 2 (Purview)
3. Complete Option 3 (Databricks)

---

## Verify Your Deployment

After deployment, verify everything is working:

| Step | Action |
|:----:|--------|
| 1 | Open **Microsoft Fabric** and navigate to your workspace |
| 2 | Confirm **Bronze**, **Silver**, and **Gold** lakehouses exist |
| 3 | Execute the **runner notebooks** to process sample data |
| 4 | Open **Power BI reports** and verify dashboards display data |

---

## Clean Up Resources

To avoid ongoing costs, remove all deployed resources when no longer needed:

```bash
azd down
```

Alternatively, delete the resource group directly in the [Azure Portal](https://portal.azure.com).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment fails | Verify [capacity requirements](./DeploymentGuideFabric.md#software-requirements) are met |
| Permission errors | Confirm Contributor and RBAC roles are assigned |
| Timeout errors | Re-run `azd up` to resume deployment |

For additional help, see [FAQs](./FAQs.md) or [submit an issue](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator/issues).

---

## Next Steps

| Resource | Description |
|----------|-------------|
| [Sample Workflows](./SampleWorkflow.md) | Try guided examples with the deployed solution |
| [Power BI Configuration](./DeploymentGuidePowerBI.md) | Configure dashboards and semantic models |
| [Fabric Notebooks Guide](./NotebooksGuideFabric.md) | Understand the medallion architecture notebooks |
| [Fabric Data Agent Guide](./FabricDataAgentGuide.md) | Set up natural language querying |
| [Copilot for Power BI Guide](./CopilotForPowerBIGuide.md) | Enable AI-powered report exploration |
