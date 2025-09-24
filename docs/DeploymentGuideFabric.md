# Microsoft Fabric Deployment Guide

This guide describes how to deploy the **Unified Data Foundation with Fabric** solution accelerator using the **Azure Developer CLI (azd)** - the recommended deployment method.

## Prerequisites

Before starting, ensure you have the following requirements. **All permissions must be granted to the deployment identity**, which can be a user account, managed identity, or service principal depending on your deployment approach.

> **📋 Deployment Identity Types**
> 
> The deployment can be executed using different identity types:
> - **User Account**: Interactive deployment using your Azure AD credentials
> - **Service Principal**: Application identity for automated/CI-CD scenarios  
> - **Managed Identity**: Azure-managed identity for secure automated deployments
>
> For more details, see [Fabric Identity Support](https://learn.microsoft.com/rest/api/fabric/articles/identity-support)

### 🔑 Required Permissions

#### Azure Resource Management Permissions

| **Permission Type** | **Required Role** | **Scope** | **Purpose** |
|---------------------|-------------------|-----------|-------------|
| Resource Group Access | [Contributor](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#contributor) or [Owner](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#owner) | Target Resource Group | Deploy Bicep templates and create Azure resources |
| Fabric Capacity Creation | Contributor/Owner | Subscription or Resource Group | Create [Microsoft Fabric capacity](https://learn.microsoft.com/fabric/enterprise/licenses#capacity) |
| Managed Identity Creation | Contributor/Owner | Subscription or Resource Group | Create [User-Assigned Managed Identity](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) |

#### Microsoft Graph API Permissions

| **Permission Name** | **Type** | **Purpose** | **Documentation** |
|---------------------|----------|-------------|-------------------|
| `User.Read` | Delegated | Read signed-in user profile information | [Microsoft Graph User permissions](https://learn.microsoft.com/graph/permissions-reference#user-permissions) |
| `openid` | Delegated | Sign in and read user profile for authentication | [OpenID Connect scopes](https://learn.microsoft.com/entra/identity-platform/scopes-oidc) |

#### Microsoft Fabric REST API Permissions

| **Permission Area** | **Required Access** | **Purpose** | **Documentation** |
|---------------------|---------------------|-------------|-------------------|
| Workspace Management | Create and manage Fabric workspaces | Deploy and configure workspace structure | [Fabric workspace APIs](https://learn.microsoft.com/rest/api/fabric/core/workspaces) |
| Item Creation | Create lakehouses, notebooks, and reports | Deploy Fabric items and content | [Fabric item APIs](https://learn.microsoft.com/rest/api/fabric/core/items) |
| Content Upload | Upload files and manage workspace content | Deploy sample data and notebooks | [Fabric REST API scopes](https://learn.microsoft.com/rest/api/fabric/articles/scopes) |

> **💡 Fabric Permission Setup**: For detailed guidance on creating an Entra app with appropriate Fabric permissions, see [Create Entra app with Fabric permissions](https://learn.microsoft.com/rest/api/fabric/articles/get-started/create-entra-app)

#### Power BI Service API Permissions

| **Permission Name** | **Type** | **Purpose** | **Documentation** |
|---------------------|----------|-------------|-------------------|
| `Tenant.Read.All` | Delegated | Read organization's Power BI tenant information | [Power BI REST API permissions](https://learn.microsoft.com/rest/api/power-bi/#scopes) |

### � Software Prerequisites

#### Required Tools

| **Tool** | **Minimum Version** | **Purpose** | **Installation Guide** |
|----------|---------------------|-------------|------------------------|
| Python | 3.9+ | Runtime environment for deployment scripts | [Download Python](https://www.python.org/downloads/) |
| Azure CLI | Latest | Azure authentication and resource management | [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |

#### Python Dependencies (automatically installed)

| **Package** | **Version** | **Purpose** |
|-------------|-------------|-------------|
| `azure-identity` | ≥1.15.0 | Azure authentication |
| `azure-core` | ≥1.29.0 | Azure SDK core functionality |
| `azure-storage-file-datalake` | ≥12.14.0 | Data Lake storage operations |
| `requests` | ≥2.31.0 | HTTP client for REST API calls |
| `python-dateutil` | ≥2.8.2 | Date/time utilities |

> **📦 Complete Dependencies**: See [requirements.txt](../infra/scripts/fabric/requirements.txt) for the full dependency list

### 🏢 Microsoft Fabric Licensing Requirements

| **Component** | **License Requirement** | **Notes** |
|---------------|-------------------------|-----------|
| Fabric Capacity | [F-SKU or P-SKU capacity](https://learn.microsoft.com/fabric/enterprise/licenses#capacity) | Required to host Fabric workspaces and items |
| User Access | [Microsoft Fabric (Free) license](https://learn.microsoft.com/fabric/enterprise/licenses#per-user-licenses) minimum | Users need appropriate licenses to access deployed content |
| Power BI Content | Pro/PPU license for F2-F32 capacities | F64+ capacities support Free license users with viewer role |

> **📚 License Details**: For comprehensive licensing information, see [Microsoft Fabric Licenses](https://learn.microsoft.com/fabric/enterprise/licenses)

## 🚀 Deployment Environment Options

| **Environment** | **Setup Required** | **Best For** |
|-----------------|-------------------|--------------|
| **Local Machine** | [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installation | Development and testing |
| **Azure Cloud Shell** | azd installation during deployment | Quick deployment without local setup |
| **GitHub Codespaces** | azd installation during deployment | Collaborative development |

> **⚡ Permission Handling**: When using Azure Developer CLI with interactive authentication, most API permissions are handled automatically. Admin consent may be required for the first deployment in an organization.

---

## 🚀 Quick Start

For the fastest deployment experience:

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

---

## Deployment Overview

The **Azure Developer CLI (azd)** automates the complete deployment process with a single `azd up` command. The deployment creates a complete data foundation solution with medallion architecture (Bronze-Silver-Gold) including infrastructure, data assets, and analytics components.

### Deployment Logic

1. **Infrastructure Provisioning**: Creates Azure resources using Bicep templates
2. **Access Configuration**: Sets up admin permissions for users and managed identity
3. **Fabric Workspace Setup**: Creates or configures Microsoft Fabric workspace and underlying data assets: lakehouses, sample data, notebooks and Power BI reports

### What Gets Created

#### In Azure:
- **Microsoft Fabric Capacity**: Dedicated compute resources
- **User-Assigned Managed Identity**: Secure access for automated operations

#### In Microsoft Fabric:
- **Workspace**: Container for all Fabric items
- **Lakehouses**: 3-tier medallion architecture (`maag_bronze`, `maag_silver`, `maag_gold`)
- **Notebooks**: Data transformation and management notebooks organized by layer
- **Sample Data**: Representative CSV files for testing and demonstration
- **Power BI Reports**: Any `.pbix` files from the repository (if present)

---

## Detailed Deployment Options

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