# Deployment Guide

## Overview

This solution offers a flexible and configurable architecture with modular components. You can deploy any of the **four architecture options** based on your organizational needs.

| Option | Components | Use Case |
|--------|-----------|----------|
| **Option 1** | Fabric + Power BI | Core data foundation |
| **Option 2** | Option 1 + Purview | Add data governance |
| **Option 3** | Option 1 + Databricks | Add advanced analytics |
| **Option 4** | Option 1 + 2 + 3 | Complete enterprise solution |

For a detailed feature description of each architecture option, please refer to [Solution Architecture and Options](./TechnicalArchitecture.md).

---

## Technology Stack

The solution accelerator utilizes the following Microsoft technologies:

| Technology | Purpose | Included in |
|-----------|---------|------------|
| [Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/) | Unified Data Foundation core components | Options 1, 2, 3, 4 |
| [Microsoft Purview](https://learn.microsoft.com/en-us/purview/) | Data governance and metadata management | Options 2, 4 |
| [Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/) | Advanced analytics and Fabric integration | Options 3, 4 |

---

## Prerequisites and Preparation

### Quota Check (Recommended)

💡 Before deployment, check your Azure quota availability for optimal planning.

📖 Follow: [Quota Check Instructions](./QuotaCheck.md) to ensure sufficient capacity.

---

## Deployment Options

### Option 1: Medallion Architecture with Power BI in Fabric

**Deploy the foundational architecture** - 3 Lakehouses (Bronze, Silver, Gold), 48 Notebooks, 2 SQL scripts, and Power BI Dashboard.

**Choose your deployment method:**

| Method | Guide | Best For |
|--------|-------|----------|
| **Automated** (Recommended) | [Automated Deployment Guide](./DeploymentGuideFabric.md) | Production, one-command setup |
| **Manual** | [Manual Deployment Guide](./DeploymentGuideFabricManual.md) | Granular control, restricted environments |
| **Local Development** | [Local Development Setup Guide](./LocalDevelopmentSetup.md) | Development, testing, customization |

**After Deployment:**
- Configure Power BI dashboard: [Power BI Dashboard Configuration](./DeploymentGuidePowerBI.md)
- Learn about notebooks: [Guide to Medallion Architecture Fabric Notebooks](./NotebooksGuideFabric.md)

---

### Option 2: Add Data Governance with Purview

**Enhance Option 1 with governance and compliance** - Adds metadata management, lineage tracking, and data governance policies.

**Prerequisites:** You have completed Option 1 deployment.

**Setup Steps:**

1. **Provision Purview** (if needed):  
   📖 [Provisioning Microsoft Purview](./SetupPurview.md)

2. **Configure Purview for Fabric:**  
   📖 [Guide to set up Purview to Govern Fabric Workspace Resources](./DeploymentGuidePurview.md)

---

### Option 3: Add Azure Databricks Integration

**Extend Option 1 with Databricks** - Integrates Databricks with Fabric for hybrid analytics and advanced data processing.

**Prerequisites:** You have completed Option 1 deployment.

**Setup Steps:**

1. **Provision Azure Databricks:**  
   📖 [Provisioning Azure Databricks](./SetupDatabricks.md)

2. **Deploy Databricks Resources:**  
   📖 [Azure Databricks Lakehouse Deployment Guide](./DeploymentGuideDatabricks.md)

**Deployed Resources:**
- 1 Silver lakehouse in Databricks
- 7 Notebooks for data processing
- 2 SQL scripts
- Sample data for Databricks

**Learn more:** [Guide to Databricks Lakehouse Notebooks](./NotebooksGuideDatabricks.md)

---

### Option 4: Complete Solution

**Deploy all components** - Combines Options 1, 2, and 3 for a complete enterprise data platform.

**Requirements:**
- Complete Option 1 (Fabric)
- Complete Option 2 (Purview)
- Complete Option 3 (Databricks)

---

## Next Steps

After successful deployment, you can begin using the solution:

📖 **Try Sample Workflows:** Follow the guided examples in [Sample Questions](./SampleWorkflow.md)

**For Development & Customization:**
- [Local Development Setup Guide](./LocalDevelopmentSetup.md) - Set up a local development environment for customizations and testing

**Additional Resources:**
- [Solution Architecture Overview](./TechnicalArchitecture.md)
- [FAQ & Troubleshooting](./FAQs.md)
- [Microsoft Fabric Documentation](https://learn.microsoft.com/en-us/fabric/)
- [Microsoft Purview Documentation](https://learn.microsoft.com/en-us/purview/)
- [Azure Databricks Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
