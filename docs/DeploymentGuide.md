# Deployment Guide

## **Prerequisites**

We have built a flexible and configurable architecture with plug-and-play options, providing you with four architecture choices. You can deploy any of the following four architectures based on your organizational needs:

1. **Core Medallion Architecture in Microsoft Fabric only**
2. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview**
3. **Core Medallion Architecture in Microsoft Fabric + Azure Databricks**
4. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview + Azure Databricks**

For a detailed feature description of each architecture, please refer to [Solution Architecture and Options](./TechnicalArchitecture.md).

Below is the list of technology stacks utilized by the solution accelerator:

- [Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/) for Unified Data Foundation core components (for Architecture Options 1, 2, 3, and 4)
- [Microsoft Purview](https://learn.microsoft.com/en-us/purview/) for added data governance support (for Architecture Options 2 and 4)
- [Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/) for added integration with Azure Databricks data into Fabric via mirroring and shortcut (for Architecture Options 3 and 4)

### **Deploy and Configure Microsoft Fabric Resources** (For Architecture Option 1)

Please follow the instructions in [Fabric Deployment Guide](./DeploymentGuideFabric.md) to deploy all resources for the medallion architecture. The resources include 3 lakehouses (bronze, silver, and gold), 48 notebooks, 2 SQL scripts, and sample data. For detailed information on the notebooks and SQL scripts, please see [Guide to Fabric Notebooks](./NotebooksGuideFabric.md).

Please follow the [Power BI Configuration Guide](./DeploymentGuidePowerBI.md) to choose your option to set up the Power BI dashboard.

### **Deploy and Configure Purview** (For Architecture Option 2)

**Prerequisites**: You have deployed architecture option 1. 

Please follow the instructions in [Provisioning Microsoft Purview](./SetupPurview.md) if your organization has not provisioned Purview. Otherwise, please follow the [Microsoft Purview Configuration Guide](./DeploymentGuidePurview.md) to configure Purview to work with the resources deployed to the Microsoft Fabric workspace. The guide also provides steps users can perform after successful configuration.

### **Deploy and Configure Azure Databricks** (For Architecture Option 3)

**Prerequisites**: You have deployed architecture option 1. 

Please follow the instructions in [Provisioning Azure Databricks](./SetupDatabricks.md) to create the Azure Databricks workspace and obtain the necessary information first, and then follow the instructions in the [Azure Databricks Deployment Guide](./DeploymentGuideDatabricks.md) to deploy resources to the Azure Databricks workspace and set up the integration with the Microsoft Fabric workspace previously created. The resources include 1 silver lakehouse, 7 notebooks, 2 SQL scripts, and sample data. For detailed information on the notebooks and SQL scripts, please see [Guide to Databricks Notebooks](./NotebooksGuideFabric.md).

### **Deploy and Configure Azure Databricks** (For Architecture Option 4)

If you have deployed all the steps described for options 1, 2, and 3, you will have deployed architecture option 4. 

