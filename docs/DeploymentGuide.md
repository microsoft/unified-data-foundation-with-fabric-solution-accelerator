# Deployment Guide

## **Prerequisites**

We have built a flexible and configurable architecture with plug-and-play options, providing you with four architecture choices. You can deploy any of the following four architectures based on your organizational needs:


1. **Core Medallion Architecture in Microsoft Fabric only**
2. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview**
3. **Core Medallion Architecture in Microsoft Fabric + Azure Databricks**
4. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview + Azure Databricks**

For a detailed feature description of each architecture, please refer to [Solution Architecture and Options](./TechnicalArchitecture.md).

Below is the list of technology stacks utilized by the solution accelerator:

- [Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/) for Unified Data Foundation core components (For Architecture Options 1, 2, 3, and 4)
- [Microsoft Purview](https://learn.microsoft.com/en-us/purview/) for added data governance support (For Architecture Options 2 and 4) 
- [Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/) for added integration with Azure Databricks data into Fabric via mirroring and shortcut (For Architecture Options 3 and 4) 

### **Initial Provisioning (Setup) for Fabric, Databricks, and Purview** 


Your organization may already have established Fabric, Databricks, or Purview. If any of the platforms have not been provisioned, you can follow the instructions below to provision the platform(s). Each respective guide describes the required privileges and steps to complete the initial provisioning. We recommend that you request your global administrator of your Azure Tenant to help you complete the tasks below: 

- [Provisioning Microsoft Fabric](./SetupFabric.md) (For Architecture Options 1, 2, 3, and 4)
- [Provisioning Microsoft Purview](./SetupPurview.md) (For Architecture Options 2 and 4)
- [Provisioning Azure Databricks](./SetupDatabricks.md) (For Architecture Options 3 and 4)

### **Deploy and Configure Microsoft Fabric Resources** (For Architecture Options 1, 2, 3, and 4)


Please follow the [Fabric Deployment Guide](./DeploymentGuideFabric.md) to deploy resources to the Microsoft Fabric workspace already set up. The resources include 3 lakehouses (bronze, silver, and gold), 48 notebooks, 2 SQL scripts, and sample data. For detailed information on the notebooks and SQL scripts, please see [Guide to Fabric Notebooks](./NotebooksGuideFabric.md).

Please follow the [Power BI Configuration Guide](./DeploymentGuidePowerBI.md) to set up Power BI data sources and semantic models to populate the dashboards. The resources include Power BI semantic models and dashboards. 

### **Configure Microsoft Purview** (For Architecture Options 2 and 4)


Please follow the [Microsoft Purview Configuration Guide](./DeploymentGuidePurview.md) to configure Purview to work with the resources deployed to the Microsoft Fabric workspace. The guide also provides steps users can perform after successful configuration. 

### **Deploy and Configure Azure Databricks Resources** (For Architecture Options 3 and 4)


Please follow the [Azure Databricks Deployment Guide](./DeploymentGuideDatabricks.md) to deploy resources to Azure Databricks and set up the integration with the Microsoft Fabric workspace previously created.  The resources include 1 silver lakehouse, 7 notebooks, 2 SQL scripts, and sample data. For detailed information on the notebooks and SQL scripts, please see [Guide to Databricks Notebooks](./NotebooksGuideFabric.md).

