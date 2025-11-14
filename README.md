# Unified data foundation with Fabric solution accelerator

This solution accelerator provides a unified data foundation with integrated data architecture leveraging Microsoft Fabric, OneLake, Microsoft Purview, and Azure Databricks to deliver a unified, integrated, and governed analytics platform.

Built with principles of [medallion lakehouse architecture](https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture), the solution accelerator supports data mesh concepts with a sample implementation. It provides domain schemas and sample data as a framework for shared domains (customer, product), finance, and sales across multiple channels. You can easily adopt the framework and update the domain models with your own. The solution seamlessly integrates sales channel data hosted in Azure Databricks, utilizing Fabric's data mirroring and shortcut to bring this data into the gold tier for unified analytics and reporting. Pre-built Power BI dashboards showcase advanced sales analytics. Advanced data governance is powered by Microsoft Purview, ensuring compliance and transparency.

This solution accelerator demonstrates how organizations can unify, govern, and analyze data across multiple domains and platforms using modern lakehouse architecture and robust governance, enabling rapid development of analytics solutions for diverse business needs.

We have built flexibility and options so that you do not have to provision all three platforms (Microsoft Fabric, Microsoft Purview, and Azure Databricks) all at once. Please see details in the Solution Overview section below for more details.

**Key use cases include:**

- Unified data platform uses Microsoft Fabric as core architecture components, with choices for integration with other platforms
- Customer and product master data management (data models, source file processing, data validation, consolidations)
- Sales analytics across data stored in Fabric and Azure Databricks
- Finance data management and foundation for reporting
- Power BI dashboards for sales data with actionable business insights

<br/>

<div align="center">

[**SOLUTION OVERVIEW**](#solution-overview) \| [**QUICK DEPLOY**](#quick-deploy) \| [**BUSINESS SCENARIO**](#business-use-case) \| [**SUPPORTING DOCUMENTATION**](#supporting-documentation)

</div>
<br/>

 **Note:** With any AI solutions you create using these templates, you are responsible for assessing all associated risks and for complying with all applicable laws and safety standards. Learn more in the transparency documents for [Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/agents/transparency-note) and [Agent Framework](https://github.com/microsoft/agent-framework/blob/main/TRANSPARENCY_FAQ.md).

<h2><img src="./docs/images/readme/solution-overview.png" width="48" />
Solution overview
</h2>
We have built a flexible and configurable architecture with plug-and-play options, providing you with four architecture choices. You can deploy any of the following four architectures based on your organizational needs:


1. **Core Medallion Architecture in Microsoft Fabric only**
2. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview**
3. **Core Medallion Architecture in Microsoft Fabric + Azure Databricks**
4. **Core Medallion Architecture in Microsoft Fabric + Microsoft Purview + Azure Databricks**

For a detailed feature description of each architecture option, please refer to [Solution Architecture and Options](./docs/TechnicalArchitecture.md).

### Solution architecture

The architecture below illustrates the solution architecture built with option 4. 

| ![image](./docs/images/readme/solution-architecture.png) |
| -------------------------------------------------------- |
|                                                          |

### How to customize
If you'd like to customize the solution accelerator, here are some common areas to start:

You can modify the data models and notebooks in different folders under the `src` folder. Please note if any part is modified, you will need to modify the associated parts accordingly, as the data model (schemas and tables), notebooks, Power BI semantic models, Power BI dashboards, and sample data are a cohesive set of resources working together as designed. 

[Customize Schema](./src/fabric/notebooks/schema)

[Update Data Management Notebooks](./src/fabric/notebooks/data_management)

[Update Bronze to Silver Data Processing Notebooks](./src/fabric/notebooks/bronze_to_silver)

[Update Silver to Gold Data Processing Notebooks](./src/fabric/notebooks/silver_to_gold)

[Update Runner Notebooks if Notebooks have been added or dropped](./src/fabric/notebooks)

<br/>

### Additional resources

[What's New in Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/fundamentals/whats-new)

[Microsoft Fabric Blog](https://blog.fabric.microsoft.com/en-us/blog)

[Microsoft Fabric Power BI Adoption roadmap](https://learn.microsoft.com/en-us/power-bi/guidance/fabric-adoption-roadmap) 

<br/>

### Key features
<details open>
  <summary>Click to learn more about the key features this solution enables</summary>

  - **Core Medallion Architecture in Fabric** <br/>Core medallion architecture in unified Microsoft Fabric Platform, with cross-domain data models covering shared (customer, product), finance, and sales across multiple channels. The solution is packaged with 48 Fabric PySpark Notebooks and 2 SQL scripts. All of them are deployed to the Fabric workspace with an automated deployment process. 
    
  - **Raw data in Bronze to Silver Lakehouse Tables with Automated Execution** <br/>Complete and automated process for raw data processing from bronze to validated data populated to silver tables. 
    
  - **Silver Lakehouse Data Flows into Gold Lakehouse with Automated Execution** <br/>Completed and automated process for validated data in silver tables flowing into gold tables for enrichment and utilization. 
    
  - **Power BI Semantic Models and Sales Analysis Dashboard** <br/>Power BI semantic models using gold tables, producing dashboards with comprehensive sales analysis. 
    
  - **Integration with Azure Databricks** <br/>
    Integration with Azure Databricks with Mirroring and Shortcut to eliminate the need for data movement. Additional sales data from Azure Databricks is made available to Fabric via data mirroring and shortcut. 

  - **Microsoft Purview for Data Governance** <br/>
    Microsoft Purview reviews and governs selected resources in the Microsoft Fabric workspace, providing capabilities such as scanning data, data discovery, and metadata for the data stored in the Fabric workspace gold tier.

</details>



<br /><br />

<h2><img src="./docs/images/readme/quick-deploy.png" width="48" />
Quick deploy
</h2>

### How to install or deploy
If you choose option 1, "Core Medallion Architecture in Microsoft Fabric only", you can deploy using either:
- [Automated deployment with Azure Developer CLI](./docs/DeploymentGuideFabric.md) (recommended for quick setup)
- [Manual deployment scripts](./docs/DeploymentGuideFabricManual.md) for users who prefer more granular control over the deployment process

For other architecture options, please follow the instructions provided in [deployment guide for all options](./docs/DeploymentGuide.md).
<br/>

### Prerequisites and costs
To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups, resources, app registrations, and assign roles at the resource group level**. This should include Contributor role at the subscription level and Role Based Access Control role on the subscription and/or resource group level. Follow the steps in [Azure Account Set Up](./docs/AzureAccountSetUp.md).

 Depending on your selected architecture option, you may also need to complete the provisioning steps outlined in [Provisioning Azure Databricks](./docs/SetupDatabricks.md) and/or [Provisioning Purview](./docs/SetupPurview.md).

Licensing and cost for establishing Fabric can be found at  [Microsoft Fabric concepts and licenses](https://learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity) and [Microsoft Fabric Pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/).

Consumption model and pricing information for Azure Databricks can be found at [Serverless DBU consumption by SKU - Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/resources/pricing).

Microsoft Purview billing models can be found at [Microsoft Purview billing models](https://learn.microsoft.com/en-us/purview/purview-billing-models).

_Note: This is not meant to outline all costs as selected SKUs, scaled use, customizations, and integrations into your own tenant can affect the total consumption of this sample solution. The sample pricing sheet is meant to give you a starting point to customize the estimate for your specific needs._

<br/>

| Product | Description | Cost |
|---|---|---|
| [Microsoft Fabric](https://learn.microsoft.com/en-us/fabric) | Core Medallion Architecture in Microsoft Fabric, and Unified Data Platform for integration with other platforms such as Azure Databricks and Snowflakes. | [Pricing](https://learn.microsoft.com/en-us/fabric/enterprise/buy-subscription#prerequisites) |
| [Azure Databricks](https://azure.microsoft.com/en-us/products/databricks/) | Azure Databricks stores sales data for one channel and the data is used by Microsoft Fabric through data mirroring and shortcut. | [Pricing](https://azure.microsoft.com/en-us/pricing/details/databricks/) |
| [Microsoft Purview](https://learn.microsoft.com/en-us/purview/) | Data Governance, data security, and risk management. | [Pricing](https://azure.microsoft.com/en-us/pricing/details/purview/) |

<br/>

>⚠️ **Important:** To avoid unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.

<br /><br />

<h2><img src="./docs/images/readme/business-scenario.png" width="48" />
Business use case
</h2>
After successful deployment of the Core Medallion Architecture in Microsoft Fabric, the Fabric workspace will be your main UI where you can access the lakehouses, PySpark data processing and data management notebooks, and Power BI semantic models, and integration with Azure Databricks if you have chosen option 3. If you choose option 1, no Databricks folder will be created. Both data engineer and sales analyst roles will be using the same Fabric workspace to perform their tasks. The diagram below illustrates the data engineer UI. Sales analysts will be able to use the Power BI semantic models and dashboards within the folder named `reports`.  Use cases can be summarized as below:

- Data Engineer creates or updates PySpark notebooks to complete data processing and data management tasks
- Data Engineer creates or updates T-SQL scripts to manage the data using Fabric SQL End Points
- Data Engineer tests end-to-end data flow
- Sales Analysts create or update Power BI Semantic models based off Gold tier lakehouse
- Sales Analysts create or update Power BI dashboards. 

|![image](./docs/images/readme/fabric-workspace-ui.png)|
|---|

<br/>

The data engineer can also upload additional source data to the bronze lakehouse and recreate the data processing flow from bronze to silver and then to gold. 

⚠️ The sample data used in this repository is synthetic and generated using Python Programs. The data is intended for use as sample data only.

### Business value
<details>
  <summary>Click to learn more about what value this solution provides</summary>

  - **Build Modern Lakehouse Architecture** <br/>Demonstrate how organizations can unify, govern, and analyze data across multiple domains and platforms using modern lakehouse architecture and robust governance, enabling rapid development of analytics solutions for diverse business needs. The solution accelerator provides a complete set of sample data for testing. 

  - **Processing Raw Source Data in Bronze Lakehouse and Validate in Silver Lakehouse, and Enrich Data In Gold Lakehouse** <br/>
    Provide core solution with domain models, data processing and data management code with automated execution to copy raw source data in Bronze lakehouse to populate Silver Lakehouse data models and then Gold Lakehouse Data models, to prepare data for analysis. 

  - **Seamless Integration with Azure Databricks with Data Mirroring and Shortcut, Microsoft Purview for Data Governance**<br/>

    Provide architecture options to integrate with Azure Databricks and Microsoft Purview for data governance. 

  - **Semantic Models and Power BI Dashboards** <br/>
    Provide Semantic Models and Power BI Dashboards for Sales Analysis, such as year-over-year sales analysis, best-selling products, and sales distribution across customer segments. 

</details>

<br /><br />

<h2><img src="./docs/images/readme/supporting-documentation.png" width="48" />
Supporting documentation
</h2>

### Security guidelines

This template uses Azure Key Vault to store all connections to communicate between resources.

This template also uses [Managed Identity](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) for local development and deployment.

To ensure continued best practices in your own repository, we recommend that anyone creating solutions based on our templates ensure that the [GitHub secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) setting is enabled.

You may want to consider additional security measures, such as:

* Enabling Microsoft Defender for Cloud to [secure your Azure resources](https://learn.microsoft.com/en-us/azure/defender-for-cloud/).
* Protecting the Azure Container Apps instance with a [firewall](https://learn.microsoft.com/azure/container-apps/waf-app-gateway) and/or [Virtual Network](https://learn.microsoft.com/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli).

<br/>

### Frequently asked questions

[Click here](./docs/FAQs.md) to learn more about common questions about this solution.

<br/>

### Cross references
Check out similar solution accelerators

| Solution Accelerator | Description |
|---|---|
| [Agentic applications for unified data foundation](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator) | Agentic AI application that provides nature language query of the data using unified data foundation.  Description of solution accelerator |

<br/>   


## Provide feedback

Have questions, find a bug, or want to request a feature? [Submit a new issue](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator/issues) on this repo and we'll connect.

<br/>

## Responsible AI Transparency FAQ 
Please refer to [Transparency FAQ](./TRANSPARENCY_FAQ.md) for responsible AI transparency details of this solution accelerator.

<br/>

## Disclaimers

To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, “Microsoft Products and Services”), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services. 

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit https://aka.ms/exporting. 

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer’s implementation of the Online Services. 

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.  

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, “HIGH-RISK USE”), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.  
