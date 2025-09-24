# Microsoft Fabric Deployment Guide

This guide describes how to deploy the **Unified Data Foundation with Fabric** solution accelerator using the **Azure Developer CLI (azd)** - the recommended deployment method.

## 🚀 Quick Start

We recommend Azure Developer CLI for the fastest deployment experience (check [Prerequisites](#prerequisites) first):

```bash
# Clone repository
git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
cd unified-data-foundation-with-fabric-solution-accelerator

# Optional: Customize the Fabric workspace name (defaults to "Unified Data Foundation with Fabric workspace")
azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"

# Deploy everything with one command
azd up
```

You'll be prompted for:
- **Environment name** (e.g., "dev", "test", "prod")
- **Azure region** (e.g., "eastus", "westus2")

**That's it!** `azd up` handles everything: infrastructure provisioning, Fabric workspace creation, data deployment, and admin configuration.

- Check out [deployment overview](#deployment-overview) to understand what gets created
- See alternative [deployment options](#deployment-options) for this solution accelerator
- See more [configuration options](#configuration-options) to customize your deployment
- Review the [deployment results](#deployment-results) to see what gets created

---

## Prerequisites

Before starting, ensure your deployment identity has the following requirements.

> **📋 Deployment Identity Types**
> 
> The deployment can be executed using different identity types:
> - **User Account**: Interactive deployment using your Azure AD credentials
> - **Service Principal**: Application identity for automated/CI-CD scenarios  
> - **Managed Identity**: Azure-managed identity for secure automated deployments
>
> For more details, see [Fabric Identity Support](https://learn.microsoft.com/rest/api/fabric/articles/identity-support)

### 🔐 Azure Permissions
- [ ] **Resource Group Access**: Ensure your deployment identity has permissions on target Resource Group to deploy Bicep templates and create Azure resources using appropriate [Azure RBAC built-in roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles) (e.g. has [Contributor](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#contributor) or [Owner](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#owner)) or appropriate [Azure RBAC custom role](https://learn.microsoft.com/azure/role-based-access-control/custom-roles) with necessary permissions
- [ ] **`Microsoft.Fabric` Resource Provider Access**: Verify your Azure Subscription has [Microsoft.Fabric resource provider](https://learn.microsoft.com/azure/azure-resource-manager/management/azure-services-resource-providers) enabled and your deployment identity has permissions on Resource Group to create [Microsoft Fabric capacity resource](https://learn.microsoft.com/azure/templates/microsoft.fabric/capacities?pivots=deployment-language-bicep)

### 🔗 API Permissions
- [ ] **Microsoft Graph API - `User.Read`**: Delegated permission to read signed-in user profile information using [Microsoft Graph User permissions](https://learn.microsoft.com/graph/permissions-reference#user-permissions)
- [ ] **Microsoft Graph API - `openid`**: Delegated permission for sign in and user profile authentication using [OpenID Connect scopes](https://learn.microsoft.com/entra/identity-platform/scopes-oidc)
- [ ] **Fabric REST API - Workspace Management**: Access to create and manage Fabric workspaces for workspace structure deployment using [Fabric workspace APIs](https://learn.microsoft.com/rest/api/fabric/core/workspaces)
- [ ] **Fabric REST API - Item Creation**: Access to create lakehouses, notebooks, and reports for Fabric content deployment using [Fabric item APIs](https://learn.microsoft.com/rest/api/fabric/core/items)
- [ ] **Fabric REST API - Content Upload**: Access to upload files and manage workspace content for sample data and notebook deployment using [Fabric REST API scopes](https://learn.microsoft.com/rest/api/fabric/articles/scopes)
- [ ] **Power BI API - `Tenant.Read.All`**: Delegated permission to read organization's Power BI tenant information using [Power BI REST API permissions](https://learn.microsoft.com/rest/api/power-bi/#scopes)

### 💻 Software Requirements
- [ ] **Python**: Install version 3.9+ as runtime environment for deployment scripts from [Download Python](https://www.python.org/downloads/)
- [ ] **Azure CLI**: Install latest version for Azure authentication and resource management from [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)




---

## Deployment Overview

This solution accelerator uses a two-phase deployment approach that creates a complete data foundation solution with medallion architecture (Bronze-Silver-Gold).

The deployment executes in two coordinated phases using dedicated scripts:

1. **Infrastructure Provisioning** - Executes [`main.bicep`](../infra/main.bicep) to create:
   - **Microsoft Fabric Capacity**: Dedicated compute resources with configured admin permissions
   - **Resource Group**: Container for all Azure resources

2. **Fabric Workspace Setup** - Runs [`run_python_script_fabric.ps1`](../infra/scripts/utils/run_python_script_fabric.ps1) orchestrator and [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) deployment script to create:
   - **Workspace**: Organized container with folder structure for all Fabric items
   - **Lakehouses**: 3-tier medallion architecture (`maag_bronze`, `maag_silver`, `maag_gold`)
   - **Notebooks**: Data transformation and management notebooks organized by processing layer
   - **Sample Data**: Representative CSV files uploaded to bronze lakehouse for testing
   - **Power BI Reports**: Dashboard components for data visualization (if present)

The deployment orchestration coordinates both phases, passing deployment parameters and ensuring proper sequencing. See [deployment options](#deployment-options) for different ways to run this deployment based on your preferred environment.

---

## Deployment Options

Check the following options to choose your preferred environment for running the deployment.

| **Environment** | **Setup Required** | **Best For** |
|-----------------|-------------------|--------------|
| **Local Machine** | [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installation | Development and testing |
| **Azure Cloud Shell** | azd installation during deployment | Quick deployment without local setup |
| **GitHub Codespaces** | azd installation during deployment | Collaborative development |

> **⚡ Permission Handling**: When using Azure Developer CLI with interactive authentication, most API permissions are handled automatically. Admin consent may be required for the first deployment in an organization.

Choose your preferred environment for running `azd up`:

<div align="center">

| **[🖥️ Local Environment](#local-environment)** | **[☁️ Azure Cloud Shell](#azure-cloud-shell)** | **[🚀 GitHub Codespaces](#github-codespaces)** |
|:---:|:---:|:---:|
| Deploy from your local machine | Deploy without local installation | Full cloud development environment |
| Full control over environment | Pre-authenticated & configured | VS Code in browser |
| Requires local tool installation | Always up-to-date tools | Pre-configured & collaborative |

</div>

<details>
<summary><b>🖥️ Local Environment</b></summary>

<div id="local-environment">

### Local Environment

Deploy from your local machine with full control over the environment.

#### Prerequisites:
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Python 3.9+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

#### Installation Steps:

**Windows (PowerShell):**
```powershell
# Install Azure Developer CLI
winget install microsoft.azd

# Verify installation
azd version
```

**macOS:**
```bash
# Install Azure Developer CLI
brew tap azure/azd && brew install azd

# Verify installation
azd version
```

**Linux:**
```bash
# Install Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# Verify installation
azd version
```

#### Deployment Steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
   cd unified-data-foundation-with-fabric-solution-accelerator
   ```

2. **Authenticate with Azure:**
   ```bash
   az login
   azd auth login
   ```

3. **Initialize the project:**
   ```bash
   azd init
   ```

4. **Optional: Set custom workspace name:**
   ```bash
   azd env set AZURE_FABRIC_WORKSPACE_NAME "My Production Workspace"
   ```

5. **Deploy everything:**
   ```bash
   azd up
   ```

   You'll be prompted for:
   - Environment name (e.g., "production", "dev", "test")
   - Azure location (e.g., "eastus", "westus2")

</details>

<details>
  <summary><b>☁️ Azure Cloud Shell</b></summary>

### Azure Cloud Shell

Deploy directly from Azure Cloud Shell without installing anything locally.

#### Benefits:
- **No local installation required**: Azure CLI and Python are pre-installed
- **Always up-to-date**: Latest tools are maintained automatically
- **Secure authentication**: Automatically authenticated with your Azure account
- **Persistent storage**: Files persist across sessions

#### Deployment Steps:

1. **Open Azure Cloud Shell:**
   - Navigate to [Azure Cloud Shell](https://portal.azure.com/#cloudshell/)
   - Choose **Bash** as your shell environment

2. **Install Azure Developer CLI:**
   ```bash
   # Install azd in Cloud Shell
   curl -fsSL https://aka.ms/install-azd.sh | bash
   
   # Restart your shell or reload PATH
   exec bash
   
   # Verify installation
   azd version
   ```

3. **Clone the repository:**
   ```bash
   git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
   cd unified-data-foundation-with-fabric-solution-accelerator
   ```

4. **Initialize and deploy:**
   ```bash
   # Initialize the project
   azd init
   
   # Optional: Set custom workspace name
   azd env set AZURE_FABRIC_WORKSPACE_NAME "Cloud Shell Deployment"
   
   # Deploy everything
   azd up
   ```

   During deployment, you'll be prompted for:
   - Environment name
   - Azure location

> **💡 Tip**: Cloud Shell sessions last 20 minutes. For longer deployments, periodically interact with the shell to keep it active.
</details>

<details>
  <summary><b>🚀 GitHub Codespaces</b></summary>

### GitHub Codespaces

Deploy using GitHub Codespaces for a complete cloud development environment.

#### Benefits:
- **Full development environment**: VS Code in the browser with all extensions
- **Pre-configured**: Development environment is ready to use
- **Collaborative**: Easy to share and collaborate
- **No local setup**: Everything runs in the cloud

#### Deployment Steps:

1. **Fork the repository:**
   - Navigate to [the repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator) on GitHub
   - Click the **Fork** button in the top-right corner
   - Select your account to create a fork

2. **Open GitHub Codespaces:**
   - In your forked repository, click the **Code** button
   - Select the **Codespaces** tab
   - Click **Create codespace on main**
   
   Alternatively, use this direct link with your GitHub username:
   ```
   https://codespaces.new/YOUR-GITHUB-USERNAME/unified-data-foundation-with-fabric-solution-accelerator
   ```

3. **Wait for environment setup:**
   - Codespaces will automatically set up the development environment
   - This typically takes 2-3 minutes

4. **Open terminal in Codespaces:**
   - Press `Ctrl+`` (backtick) or go to **Terminal > New Terminal**

5. **Install Azure Developer CLI:**
   ```bash
   # Install azd
   curl -fsSL https://aka.ms/install-azd.sh | bash
   
   # Reload PATH
   source ~/.bashrc
   
   # Verify installation
   azd version
   ```

6. **Authenticate with Azure:**
   ```bash
   # Login to Azure CLI
   az login --use-device-code
   
   # Login to azd (will use the same authentication)
   azd auth login --use-device-code
   ```

7. **Initialize and deploy:**
   ```bash
   # Initialize the project
   azd init
   
   # Optional: Set custom workspace name
   azd env set AZURE_FABRIC_WORKSPACE_NAME "Codespaces Deployment"
   
   # Deploy everything
   azd up
   ```

> **💡 Tip**: Use device code authentication (`--use-device-code`) in Codespaces for the most reliable authentication experience.


</details>

---


## Configuration options

---

## Deployment Results

### Fabric Components Created

The deployment creates a complete medallion architecture with:

- **Infrastructure**: Automated provisioning of Fabric capacity and workspace
- **Folder Structure**: Organized folders for lakehouses, notebooks, and reports
- **Lakehouses**: Three-tier architecture (Bronze, Silver, Gold) with schema support
- **Sample Data**: Representative CSV files uploaded to the bronze lakehouse
- **Notebooks**: Complete set of data transformation and management notebooks
- **Automated Processing**: Initial data pipeline execution
- **Power BI Reports**: Automated deployment of Power BI reports (.pbix files) to the workspace
- **User-Assigned Managed Identity**: Automatically created for secure access to Azure resources

### Azure Infrastructure

| Resource | Type | Purpose |
|----------|------|---------|
| [**Fabric Capacity**](https://learn.microsoft.com/fabric/admin/capacity-settings?tabs=power-bi-premium) | `Microsoft.Fabric/capacities` | Dedicated compute capacity for Fabric workloads |
| [**User-Assigned Managed Identity**](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) | `Microsoft.ManagedIdentity/userAssignedIdentities` | Secure authentication for automated operations |

![Screenshot of deployed Azure resources](./images/deployment/fabric/azure_resources.png)

### Fabric items

#### Fabric Workspace

Workspace created with the specified or default name.

![Screenshot of resulting Fabric workspace](./images/deployment/fabric/fabric_workspace.png)

#### Folder Structure

```
workspace/
├── lakehouses/
├── notebooks/
│   ├── bronze_to_silver/
│   ├── data_management/
│   ├── schema/
│   └── silver_to_gold/
└── reports/
```

![Screenshot of resulting Fabric workspace folder structure](./images/deployment/fabric/fabric_workspace_folders.png)

#### Lakehouses

| Name | Purpose | Schema Support |
|------|---------|----------------|
| `maag_bronze` | Raw data ingestion | Enabled |
| `maag_silver` | Cleaned, standardized data | Enabled |
| `maag_gold` | Business-ready aggregated data | Enabled |

![Screenshot of resulting Fabric lakehouses](./images/deployment/fabric/fabric_lakehouses.png)

#### Sample Data

The solution includes sample data for:
- **Finance data**: accounts, invoices, payments
- **Sales data**: orders, order lines, payments from multiple sources
- **Shared reference data**: customers, products, locations, categories

![Screenshot of resulting Fabric sample data](./images/deployment/fabric/fabric_sample_data.png)

#### Jupyter Notebooks

![Screenshot of resulting Fabric notebooks](./images/deployment/fabric/fabric_notebooks.png)

#### Main Orchestration
- `run_bronze_to_silver` - Orchestrates bronze to silver transformation
- `run_silver_to_gold` - Orchestrates silver to gold transformation

#### Bronze to Silver Transformation
- Domain-specific transformation notebooks for each data entity
- Handles data cleansing and standardization

#### Data Management
- Table management utilities (drop, truncate)
- Troubleshooting and maintenance notebooks

#### Schema Definition
- Data model definitions for each layer
- Schema creation and management

#### Silver to Gold Processing
- Business logic implementation
- Data aggregation and enrichment

#### Power BI Report

Any `.pbix` files found in the `reports/` directory will be automatically deployed to the workspace's reports folder. The deployment process:
- Scans recursively through the reports directory
- Uploads each Power BI report with conflict resolution (Create or Overwrite)
- Assigns reports to the appropriate folder within the workspace
- Provides deployment tracking and verification

![Screenshot of resulting PowerBI reports](./images/deployment/fabric/fabric_powerbi_reports.png)

---

## Additional Resources

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Power BI Deployment Guide](./DeploymentGuidePowerBI.md)
- [Solution Architecture Overview](../architecture/README.md)
- [Frequently Asked Questions](./FAQs.md)

For technical support and community discussions, visit the [project repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator) or engage with the Microsoft Fabric community.

---

*This deployment guide is part of the Unified Data Foundation with Fabric solution accelerator. For the latest updates and documentation, visit the [official repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator).*

---