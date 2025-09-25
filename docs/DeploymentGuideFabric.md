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
- See more [advanced configuration options](#advanced-configuration-options) to customize your deployment
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
- [ ] **Azure Developer CLI**: Install latest version for simplified deployment orchestration from [Install Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
---

## Deployment Overview

This solution accelerator uses a two-phase deployment approach that creates a complete data foundation solution with medallion architecture (Bronze-Silver-Gold). The deployment is designed to be **idempotent** and **safe to re-run**, intelligently detecting existing resources and only creating what's missing.

The deployment executes in two coordinated phases using dedicated scripts:

1. **Infrastructure Provisioning** - Executes [`main.bicep`](../infra/main.bicep) to create Azure resources using [ARM idempotency](https://learn.microsoft.com/azure/azure-resource-manager/templates/deployment-tutorial-local-template?tabs=azure-powershell#deploy-template):
   - **Microsoft Fabric Capacity**: Dedicated compute resources with configured admin permissions (updates configuration if parameters change)
   - **Resource Group**: Container for all Azure resources

2. **Fabric Workspace Setup** - Runs [`run_python_script_fabric.ps1`](../infra/scripts/utils/run_python_script_fabric.ps1) orchestrator and [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) deployment script to intelligently manage Fabric resources:
   - **Workspace**: Detects existing workspace by name or creates new one, assigns to specified capacity
   - **Lakehouses**: Creates missing 3-tier medallion architecture (`maag_bronze`, `maag_silver`, `maag_gold`) while preserving existing data
   - **Notebooks**: Updates existing notebooks with latest content or creates missing ones with proper lakehouse references ⚠️ *overwrites customizations*
   - **Sample Data**: Uploads CSV files to bronze lakehouse ⚠️ *overwrites existing files with same names*
   - **Power BI Reports**: Creates or overwrites dashboard components for data visualization ⚠️ *replaces existing reports with same names*
   - **Administrators**: Adds new workspace administrators without removing existing ones

The deployment orchestration coordinates both phases, passing deployment parameters and ensuring proper sequencing. See [deployment options](#deployment-options) for different ways to run this deployment based on your preferred environment.

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

## Deployment Options

This solution accelerator provides flexible deployment options to suit different environments and workflows.

### Azure Developer CLI

The **[Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)** is Microsoft's unified command-line tool that simplifies the deployment of cloud applications. It provides an opinionated approach to deploying and managing the complete application lifecycle, from infrastructure provisioning to application deployment.

For this solution accelerator, `azd` orchestrates the entire deployment process with a single command, handling both Azure infrastructure provisioning and Fabric workspace configuration automatically.

> **📋 Prerequisites Check**: Ensure you meet the [software requirements](#-software-requirements) and have the necessary [Azure](#-azure-permissions) and [API permissions](#-api-permissions) before proceeding.

**Quick deployment steps:**

```bash
# Clone and navigate to the repository
git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
cd unified-data-foundation-with-fabric-solution-accelerator

# Authenticate with Azure services (required)
az login
azd auth login

# Optional: Customize workspace name (defaults to "Unified Data Foundation with Fabric workspace")
azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"

# Deploy everything with one command
azd up
```

During `azd up`, you'll be prompted to configure:
- **Environment name**: Logical name for your deployment (e.g., "dev", "test", "prod")
- **Azure subscription**: Target subscription for resource deployment
- **Azure region**: Geographic location for resources (e.g., "eastus", "westus2", "westeurope")

> **💡 Tip**: Use `azd env list` to view existing environments and `azd env select` to switch between them. Learn more about [azd environments](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables).

**Choose your deployment environment:**

Azure Developer CLI can be used from multiple environments. Choose the one that best fits your workflow and requirements:

| Environment | Best For | Prerequisites | Azure CLI | Python |
|-------------|----------|---------------|-----------|---------|
| **🖥️ Local Machine** | Full control, custom tooling, offline development | Install all [software requirements](#-software-requirements) | ✅ Required | ✅ 3.9+ |
| **☁️ Azure Cloud Shell** | Quick start, no local installation | Azure account with [required permissions](#prerequisites) | ✅ Pre-installed | ✅ Pre-installed |
| **🚀 GitHub Codespaces** | Cloud development, team consistency | GitHub account + Azure account | ✅ Pre-configured | ✅ Pre-configured |
| **📦 VS Code Dev Container** | Containerized consistency across teams | [Docker Desktop](https://www.docker.com/products/docker-desktop) + [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) | ✅ Containerized | ✅ Containerized |

**Environment-specific setup:**

<details>
<summary><strong>🖥️ Local Machine</strong> - Full control and customization</summary>

Deploy from your local development environment with complete control over tools, configuration, and customization capabilities.

**Prerequisites:**
Ensure you have all the [software requirements](#-software-requirements) installed:
- **[Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)** - Main deployment orchestration tool
- **[Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)** - Azure authentication and resource management
- **[Python 3.9+](https://www.python.org/downloads/)** - Runtime for Fabric deployment scripts
- **[Git](https://git-scm.com/downloads/)** - Version control and repository cloning

**Deployment Steps:**
1. **Install Prerequisites**: Follow the [Azure Developer CLI installation guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) for your operating system

2. **Verify Installations and Clone Repository**:
   ```bash
   # Verify installations
   azd version         # Should show azd version (minimum supported version)
   az version          # Should show Azure CLI version
   python --version    # Should show Python 3.9+
   git --version       # Should show Git version
   
   # Clone repository
   git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
   cd unified-data-foundation-with-fabric-solution-accelerator
   ```

3. **Authenticate**: Ensure you have the required [Azure](#-azure-permissions) and [API permissions](#-api-permissions)

4. **Configure and Deploy**:
   ```bash
   # Azure CLI authentication
   az login
   
   # Azure Developer CLI authentication
   azd auth login
   
   # Optional: Customize workspace name
   azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"
   
   # Deploy infrastructure + Fabric workspace
   azd up
   ```

**References:**
- [Azure Developer CLI Reference](https://learn.microsoft.com/azure/developer/azure-developer-cli/reference)
- [Manage environments and variables](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables)

</details>

<details>
<summary><strong>☁️ Azure Cloud Shell</strong> - Zero-setup cloud deployment</summary>

Deploy directly from Azure's cloud-based terminal environment with pre-installed tools and automatic Azure authentication. Azure Cloud Shell provides a browser-accessible shell experience with [pre-configured tools](https://learn.microsoft.com/azure/cloud-shell/features) including Azure CLI and Python.

**Prerequisites:** 
- Azure account with the required [Azure permissions](#-azure-permissions) and [API permissions](#-api-permissions)
- Web browser with access to Azure portal

**Deployment Steps:**
1. **Access Cloud Shell**: 
   - Open [Azure Cloud Shell](https://shell.azure.com) directly, or
   - Navigate to [Azure Portal](https://portal.azure.com) and click the Cloud Shell icon (>_)
   - Choose **Bash** or **PowerShell** environment (both supported)

2. **Install and Deploy**:
   ```bash
   # Install latest azd version
   curl -fsSL https://aka.ms/install-azd.sh | bash
   exec bash  # Restart shell to make azd available
   
   # Verify installation and authentication
   azd version          # Confirm azd is installed
   az account show      # Verify Azure authentication (pre-authenticated)
   azd auth login       # Follow device code flow if needed
   
   # Clone repository and deploy
   git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
   cd unified-data-foundation-with-fabric-solution-accelerator
   
   # Optional: Customize workspace name
   azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"
   
   # Deploy everything
   azd up
   ```

**Cloud Shell Features:**
- **Pre-authenticated**: Automatically uses your Azure portal credentials
- **Persistent Storage**: 5GB of persistent storage in `$HOME` directory
- **Pre-installed Tools**: Azure CLI, Git, Python, and many development tools
- **Cross-Platform**: Works from any modern web browser

**Troubleshooting:**
- If azd installation fails, try the [alternative installation methods](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd#other-install-methods)
- Cloud Shell sessions timeout after 20 minutes of inactivity; use `azd env list` to check existing environments after reconnection

**References:**
- [Azure Cloud Shell Overview](https://learn.microsoft.com/azure/cloud-shell/overview)
- [Azure Cloud Shell Features](https://learn.microsoft.com/azure/cloud-shell/features)
- [Troubleshooting Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/troubleshooting)

</details>

<details>
<summary><strong>🚀 GitHub Codespaces</strong> - Complete cloud development environment</summary>

Deploy from a comprehensive cloud-based development environment running [Visual Studio Code in the browser](https://docs.github.com/codespaces/the-codespace-lifecycle/using-the-vs-code-command-palette-in-codespaces). GitHub Codespaces provides a complete development environment with pre-configured tools and dependencies.

**Prerequisites:** 
- [GitHub account](https://github.com/signup) with access to GitHub Codespaces
- Azure account with the required [Azure permissions](#-azure-permissions) and [API permissions](#-api-permissions)

**Deployment Steps:**
1. **Create Codespace**:
   - Navigate to the [solution accelerator repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator)
   - Click **Code** → **Codespaces** → **Create codespace on main**
   - Wait for the environment to initialize (typically 2-3 minutes)

2. **Install Tools and Deploy**:
   ```bash
   # Check if Azure Developer CLI is available, install if needed
   azd version || {
       curl -fsSL https://aka.ms/install-azd.sh | bash
       exec bash  # Restart shell
   }
   
   # Use device code authentication (required in Codespaces)
   az login --use-device-code
   azd auth login --use-device-code
   
   # Optional: Customize workspace name  
   azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"
   
   # Deploy the solution
   azd up
   ```

**Note**: Repository forking is only required if you plan to:
- Modify the solution accelerator code
- Set up automated CI/CD pipelines  
- Contribute changes back to the project

**References:**
- [GitHub Codespaces Documentation](https://docs.github.com/codespaces)
- [Creating a codespace for a repository](https://docs.github.com/codespaces/developing-in-codespaces/creating-a-codespace-for-a-repository)
- [Managing billing for GitHub Codespaces](https://docs.github.com/billing/managing-billing-for-github-codespaces)

</details>

<details>
<summary><strong>📦 VS Code Dev Container</strong> - Containerized development consistency</summary>

Deploy from a containerized development environment that provides consistent tooling across teams, machines, and operating systems. [Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) ensure that every developer has exactly the same development environment.

**Prerequisites:**
- **[Docker Desktop](https://www.docker.com/products/docker-desktop)** - Container runtime engine
- **[Visual Studio Code](https://code.visualstudio.com/)** - Code editor
- **[Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)** - VS Code extension for container development
- Azure account with the required [Azure permissions](#-azure-permissions) and [API permissions](#-api-permissions)

**Initial Setup:**
1. **Install Prerequisites**:
   - Download and install Docker Desktop for your OS ([Windows](https://docs.docker.com/desktop/install/windows-install/), [macOS](https://docs.docker.com/desktop/install/mac-install/), [Linux](https://docs.docker.com/desktop/install/linux-install/))
   - Install [Visual Studio Code](https://code.visualstudio.com/download)
   - Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Verify and Deploy**:
   ```bash
   # Verify Docker installation
   docker --version          # Verify Docker is installed
   docker run hello-world    # Test Docker functionality
   
   # Clone repository
   git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
   ```

**Deployment Steps:**
1. **Open in Container**:
   - Open the cloned folder in VS Code
   - When prompted, click **Reopen in Container**
   - **Alternative**: Use Command Palette (`Ctrl+Shift+P`) → "Dev Containers: Reopen in Container"
   - Wait for container to build and initialize (may take several minutes on first run)

2. **Authenticate and Deploy**:
   ```bash
   # All tools should be pre-installed in the container
   azd version              # Azure Developer CLI
   az version               # Azure CLI  
   python --version         # Python runtime
   
   # Azure authentication
   az login                 # Azure CLI authentication
   azd auth login          # Azure Developer CLI authentication
   
   # Optional: Customize workspace name
   azd env set AZURE_FABRIC_WORKSPACE_NAME "My Custom Workspace Name"
   
   # Deploy the complete solution
   azd up
   ```

**Container Environment Includes:**
- **Azure CLI** - Azure resource management and authentication
- **Azure Developer CLI** - Application lifecycle management
- **Python 3.11+** - Runtime for deployment scripts and Fabric APIs
- **Git** - Version control operations
- **PowerShell** - Cross-platform shell for automation scripts
- **All project dependencies** - Pre-installed Python packages and requirements

**References:**
- [Developing inside a Container](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container specification](https://containers.dev/)
- [Docker Desktop documentation](https://docs.docker.com/desktop/)
- [Container configuration reference](https://code.visualstudio.com/docs/devcontainers/devcontainer-cli)

</details>

### GitHub Actions (CI/CD)

For automated deployments, use the included [GitHub Actions workflow](../.github/workflows/azure-dev.yml) that provides enterprise-grade CI/CD capabilities.

**Key Features:**
- **Automated Deployment**: Triggered on push to main branch or manual dispatch
- **Environment Management**: Support for multiple deployment stages (dev, staging, prod)
- **Federated Authentication**: Secure, secretless authentication with Azure
- **Static Code Analysis**: Automated Bicep validation and linting

**Trigger Options:**
- Push to main branch
- Manual workflow dispatch  
- Pull request validation (infrastructure validation only)

<details>
<summary><strong>📋 Required GitHub Variables Configuration</strong></summary>

Configure these repository variables in **Settings → Secrets and variables → Actions → Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | Service Principal (App Registration) client ID for federated authentication | `12345678-1234-1234-1234-123456789012` |
| `AZURE_TENANT_ID` | Azure Active Directory tenant ID where the service principal resides | `87654321-4321-4321-4321-210987654321` |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID for resource deployment | `abcdef01-2345-6789-abcd-ef0123456789` |
| `AZURE_LOCATION` | Azure region for resource deployment | `eastus`, `westus2`, `westeurope` |
| `AZURE_ENV_NAME` | Environment name used for resource naming and identification | `dev`, `test`, `prod` |
| `AZURE_RESOURCE_GROUP_NAME` | Target resource group name for deployment | `rg-unified-data-foundation-dev` |

</details>

<details>
<summary><strong>🔧 Setup Requirements</strong></summary>

**Service Principal Setup:**
1. Create a [service principal with federated credentials](https://learn.microsoft.com/azure/developer/github/connect-from-azure) for GitHub Actions
2. Assign appropriate Azure RBAC permissions (Contributor role on target Resource Group)

**GitHub Repository Configuration:**
3. Configure GitHub repository variables with the values from the table above
4. Set up GitHub environments (`udfwf-build`, `udfwf-dev`) for deployment approval workflows

**Security Best Practices:**
- Use federated authentication instead of storing secrets
- Limit service principal permissions to minimum required scope
- Enable environment protection rules for production deployments

</details>

**What happens during `azd up`:**

The Azure Developer CLI orchestrates a complete deployment process:

1. **Infrastructure Provisioning**: Creates Azure resources using [`main.bicep`](../infra/main.bicep)
2. **Environment Configuration**: Sets up deployment parameters and variables  
3. **Fabric Workspace Setup**: Runs [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) to create Fabric workspace, lakehouses, and notebooks
4. **Data Deployment**: Uploads sample data and configures the medallion architecture
5. **Validation**: Verifies successful deployment of all components

**Common Deployment Scripts:**

All deployment environments execute the same underlying infrastructure and application deployment scripts:
- **[`main.bicep`](../infra/main.bicep)** - Azure infrastructure provisioning using Bicep templates
- **[`run_python_script_fabric.ps1`](../infra/scripts/utils/run_python_script_fabric.ps1)** - PowerShell orchestrator for cross-platform execution
- **[`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py)** - Python deployment script for Fabric workspace configuration

> **🎯 Environment Selection Guide**: 
> - **First-time users**: Start with **Azure Cloud Shell** for zero-setup experience
> - **Active developers**: Use **Local Machine** for full development capabilities  
> - **Team collaboration**: Choose **GitHub Codespaces** for consistent cloud environments
> - **Enterprise consistency**: Implement **VS Code Dev Container** for standardized tooling
>
> For detailed feature comparison, see the [Azure Developer CLI documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview).

**Next Steps:**
- Review the [deployment results](#deployment-results) to understand what gets created
- Explore [advanced configuration options](#advanced-configuration-options) to customize your deployment
- Check the [FAQs](./FAQs.md) for common questions and troubleshooting tips

---

## Advanced Configuration Options

The solution accelerator provides flexible configuration options to customize your deployment. Parameters can be configured through **Azure Developer CLI environment variables** (`azd env set`) for local deployments or through **GitHub repository variables** for CI/CD deployments.

> **📁 Configuration Files Reference:**
> - Infrastructure: [`infra/main.bicep`](../infra/main.bicep) - Azure resource definitions
> - Deployment orchestration: [`azure.yaml`](../azure.yaml) - AZD project configuration  
> - CI/CD workflow: [`.github/workflows/azure-dev.yml`](../.github/workflows/azure-dev.yml) - GitHub Actions pipeline
> - Fabric deployment: [`infra/scripts/fabric/create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) - Fabric workspace setup

### 🏗️ Infrastructure Configuration

Configure the Azure infrastructure components through Bicep template parameters defined in [`main.bicep`](../infra/main.bicep).

<details>
<summary><strong>Azure Resources</strong></summary>

| Parameter | AZD Environment Variable | GitHub Actions Variable | Description | Default | Example |
|-----------|-------------------------|------------------------|-------------|---------|---------|
| **Solution Name** | `solutionName` | `AZURE_ENV_NAME` | Friendly name for the application/solution (3-20 chars) | `udfwfsa` | `mycompany-fabric` |
| **Location** | `AZURE_LOCATION` | `AZURE_LOCATION` | Azure region for resource deployment | Resource group location | `eastus`, `westus2`, `westeurope` |
| **Fabric Capacity SKU** | `skuName` | Not directly supported* | Fabric capacity tier and performance level | `F2` | `F4`, `F8`, `F16`, `F32`, `F64`, `F128`, `F256`, `F512`, `F1024`, `F2048` |
| **Enable Telemetry** | `enableTelemetry` | Not directly supported* | Enable/disable usage telemetry collection | `true` | `false` |

*_GitHub Actions can use additional parameters through Bicep parameter files or workflow modifications._

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

```bash
# Set environment variables (used by main.parameters.json)
azd env set AZURE_LOCATION "westeurope"
azd env set skuName "F8"
azd env set enableTelemetry false
azd up
```

</details>

<details>
<summary><strong>🚀 GitHub Actions</strong></summary>

Modify [`azure-dev.yml`](../.github/workflows/azure-dev.yml) Deploy Infrastructure step:

```yaml
- name: Deploy Infrastructure
  uses: azure/bicep-deploy@v2
  with:
    parameters: |
      {
        "solutionName": "${{ env.AZURE_ENV_NAME_DEV }}",
        "skuName": "F8",
        "enableTelemetry": false
      }
```

</details>

**Fabric Capacity SKU Selection Guide:**
- **F2-F4**: Development and testing environments
- **F8-F32**: Small to medium production workloads
- **F64-F256**: Large enterprise production workloads  
- **F512-F2048**: High-performance analytics and data science workloads

For detailed capacity planning, see [Fabric capacity planning](https://learn.microsoft.com/fabric/admin/capacity-planning).

</details>

### 🏢 Fabric Workspace Configuration

Customize the Fabric workspace setup and naming conventions. These parameters are used by the [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) script during post-provisioning.

<details>
<summary><strong>Workspace Settings</strong></summary>

| Parameter | AZD Environment Variable | GitHub Actions Variable | Description | Default | Example |
|-----------|-------------------------|------------------------|-------------|---------|---------|
| **Capacity Name** | `AZURE_FABRIC_CAPACITY_NAME` | Bicep output | Microsoft Fabric capacity name (auto-generated from deployment) | Generated from Bicep | `fc-udfwfsa-abc123` |
| **Workspace Name** | `AZURE_FABRIC_WORKSPACE_NAME` | `AZURE_FABRIC_WORKSPACE_NAME_DEV` | Custom name for the Fabric workspace | `Unified Data Foundation with Fabric workspace` | `"MyCompany Data Foundation"`, `"Analytics Platform - DEV"` |

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

```bash
azd env set AZURE_FABRIC_WORKSPACE_NAME "Analytics Platform - DEV"
azd up
```

</details>

<details>
<summary><strong>🚀 GitHub Actions</strong></summary>

Modify [`azure-dev.yml`](../.github/workflows/azure-dev.yml) environment variables:

```yaml
env:
  AZURE_FABRIC_WORKSPACE_NAME_DEV: "Analytics Platform (dev)"
```

</details>

**Workspace Naming Best Practices:**
- Use descriptive names that indicate purpose and environment
- Consider organizational naming conventions
- Include environment indicators for multi-environment deployments (Dev, Test, Prod)
- Avoid special characters that might cause conflicts with Fabric APIs

</details>

### 👥 Fabric Workspace Administrator Configuration

Manage workspace administrators and security permissions for the Fabric workspace. These parameters are processed by both the Bicep template ([`main.bicep`](../infra/main.bicep)) for capacity-level admins and the Fabric deployment script ([`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py)) for workspace-level admins.

<details>
<summary><strong>Admin Assignment Options</strong></summary>

| Parameter | AZD Environment Variable | GitHub Actions Support | Description | Format | Example |
|-----------|-------------------------|------------------------|-------------|--------|---------|
| **Fabric Admins** | `AZURE_FABRIC_ADMIN_MEMBERS` | Bicep output | List of administrators (UPNs and Service Principal IDs) | JSON array | `["user1@contoso.com", "12345678-1234-1234-1234-123456789012"]` |
| **Admins by Object ID** | `AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID` | Not directly supported* | List of object IDs with fallback user/service principal detection | JSON array | `["87654321-4321-4321-4321-210987654321"]` |

*_GitHub Actions workflow uses Bicep output for admin configuration. See examples below for customization._

**Administrator Types Supported:**
- **User Principal Names (UPNs)**: `user@domain.com` format for individual users
- **Service Principal IDs**: GUID format for application registrations  
- **Object IDs**: Direct Azure AD object identifiers with automatic type detection

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

```bash
azd env set AZURE_FABRIC_ADMIN_MEMBERS '["user@contoso.com", "sp-guid"]'
azd env set AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID '["object-id-guid"]'
azd up
```

</details>

<details>
<summary><strong>🚀 GitHub Actions</strong></summary>

**Option A**: Update [`main.parameters.json`](../infra/main.parameters.json):

```json
{
  "parameters": {
    "solutionName": { "value": "${AZURE_ENV_NAME}" },
    "fabricAdminMembers": { "value": ["user@contoso.com"] }
  }
}
```

**Option B**: Override in workflow [`azure-dev.yml`](../.github/workflows/azure-dev.yml):

```yaml
- name: Deploy Infrastructure  
  uses: azure/bicep-deploy@v2
  with:
    parameters: |
      {
        "fabricAdminMembers": ["user@contoso.com", "sp-guid"]
      }
```

</details>

**Administrator Assignment Behavior:**
- **Automatic Default Admin**: The deployment identity (user or service principal) is automatically added as a Fabric capacity admin
- **Duplicate Detection**: Prevents adding the same principal multiple times
- **Fallback Logic**: Object ID method tries both User and ServicePrincipal types automatically
- **Graph API Resolution**: UPN method uses Microsoft Graph API for identity resolution

**Permission Requirements:**
Administrators configured through these parameters will have **Admin** role on the Fabric workspace, providing:
- Full workspace management capabilities
- Ability to manage workspace items (lakehouses, notebooks, reports)
- User and permission management within the workspace
- Workspace settings configuration

</details>

### 🐍 Python Environment Configuration Options

Configure deployment behavior and troubleshooting options. These parameters are handled by the PowerShell orchestration script ([`run_python_script_fabric.ps1`](../infra/scripts/utils/run_python_script_fabric.ps1)).

<details>
<summary><strong>Deployment Customization</strong></summary>

These options are primarily used for configuring the appropriate environment for each deployment process based on elements such as underlying operating system or specialized environments such as containerized deployments or GitHub-hosted runners.

| Parameter | PowerShell Switch | AZD Support | GitHub Actions Support | Description | Use Case |
|-----------|-------------------|-------------|------------------------|-------------|----------|
| **Skip Virtual Environment** | `-SkipPythonVirtualEnvironment` | Manual override | ✅ Used in workflow | Use system Python instead of virtual environment | System-wide Python management, containerized environments |
| **Skip Dependencies** | `-SkipPythonDependencies` | Manual override | ✅ Used in workflow | Skip installing Python packages (assume pre-installed) | Pre-configured environments, repeated deployments |
| **Skip Pip Upgrade** | `-SkipPipUpgrade` | Manual override | ✅ Used in workflow | Skip upgrading pip to latest version | Environments with controlled pip versions |

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

These parameters are automatically optimized in [`azure.yml`](../azure.yaml):

```yaml
hooks:
  postprovision:
    windows:
      shell: pwsh
      run: ./infra/scripts/utils/run_python_script_fabric.ps1
      interactive: true
      continueOnError: false
    posix:
      shell: pwsh
      run: ./infra/scripts/utils/run_python_script_fabric.ps1 -SkipPythonVirtualEnvironment
      interactive: true
      continueOnError: false
  predown:
    windows:
      shell: pwsh
      run: ./infra/scripts/utils/run_python_script_fabric_remove.ps1
      interactive: true
      continueOnError: false
    posix:
      shell: pwsh
      run: ./infra/scripts/utils/run_python_script_fabric_remove.ps1 -SkipPythonVirtualEnvironment
      interactive: true
      continueOnError: false
```

</details>

<details>
<summary><strong>🚀 GitHub Actions</strong></summary>

These parameters are automatically optimized in [`azure-dev.yml`](../.github/workflows/azure-dev.yml):

```yaml
- name: Run Fabric Provisioning Script
  run: |
    pwsh ./run_python_script_fabric.ps1 \
      -SkipPythonVirtualEnvironment \
      -SkipPythonDependencies \
      -SkipPipUpgrade
```

</details>

</details>

---

## Known Limitations

This section documents known limitations in the deployment process and their workarounds.

### 🔒 Power BI API Parameter Updates

**Issue**: Service Principals cannot update Power BI dataset parameters via API, resulting in HTTP 403 errors.

**Impact**: 
- During automated deployment, if deployment identity is a Service Principal or a Managed Identity, Power BI reports are deployed but dataset parameters (SQL endpoint connection strings) may not be automatically configured
- Reports may show connection errors until manually configured

**Technical Details**:
The [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) script handles this gracefully:

```python
try:
    powerbi_client.update_powerbi_dataset_parameters(dataset_id=dataset['id'], parameters=[
        {"name": "sqlEndpoint", "newValue": sql_endpoint},
        {"name": "database", "newValue": database_name}
    ])
    print(f"✅ Dataset parameters updated successfully for '{report_name}'")
except Exception as param_error:
    if "HTTP 403" in str(param_error):
        print(f"⚠️ WARNING: Cannot update dataset parameters automatically for '{report_name}'")
        print(f"    Reason: API access restricted for service principal: {str(param_error)}")
        print(f"    Manual action required:")
        print(f"📋 Continuing deployment without dataset parameter updates...")
```

**Workaround**: 
- The deployment continues successfully despite this limitation
- Follow the manual configuration steps in the [Power BI Deployment Guide](./DeploymentGuidePowerBI.md) to complete the report setup
- This typically involves updating the `sqlEndpoint` and `database` parameters in the Power BI service

---

### 👤 Graph API Principal (user or service principal) Lookup Limitations

**Issue**: The deployment identity may lack permissions to query user object IDs from Azure Active Directory via Microsoft Graph API.

**Impact**:
- When using `--fabricAdmins` with user principal names (UPNs), the script may fail to resolve user identities
- Service Principals may successfully create workspaces but fail to add human users as administrators
- This can result in workspaces that are only accessible to the deployment service principal

**Technical Details**:
The [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) script implements fallback logic:

```python
def detect_principal_type(admin_identifier, graph_client=None):
    try:
        # Use Graph API to resolve the principal
        principal_type, object_id, principal_data = graph_client.resolve_principal(admin_identifier)
        return principal_type, object_id, principal_data
    except GraphApiError as e:
        # Convert Graph API errors to ValueError for backward compatibility
        print(f"⚠️ WARNING: Graph API lookup failed for '{admin_identifier}': {str(e)}")
        # Fallback to original logic if Graph API is not available
        if is_valid_guid(admin_identifier):
            return "ServicePrincipal", admin_identifier, {"id": admin_identifier, "displayName": "Unknown"}
```

**Workarounds**:

1. **Use Object IDs Instead**: Configure administrators using the `--fabricAdminsByObjectId` parameter or `AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID` environment variable as described in the [advanced configuration options](#advanced-configuration-options):
   ```bash
   azd env set AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID '["87654321-4321-4321-4321-210987654321"]'
   ```
   
   The script automatically tries both User and ServicePrincipal types for object IDs:
   ```python
   for principal_type in ["User", "ServicePrincipal"]:
       # Try both User and ServicePrincipal types
   ```

2. **Post-Deployment Admin Assignment**: Use the dedicated admin management scripts:
   - [`add_fabric_workspace_admins.py`](../infra/scripts/fabric/add_fabric_workspace_admins.py) - Direct Python script for admin assignment
   - [`run_python_script_fabric_admins.ps1`](../infra/scripts/utils/run_python_script_fabric_admins.ps1) - PowerShell orchestrator script
   
   These scripts can add administrators to all available Fabric workspaces after initial deployment.

---

### 🔐 Fabric REST API Permission Issues

**Issue**: Service Principals may lack sufficient permissions to access Microsoft Fabric REST APIs.

**Impact**: 
- Deployment fails during workspace creation or management operations
- Graceful exit with clear guidance on permission requirements

**Technical Details**:
The [`create_fabric_items.py`](../infra/scripts/fabric/create_fabric_items.py) script provides specific error handling for authorization failures:

```python
except FabricApiError as e:
    if e.status_code == 401:
        print(f"⚠️ WARNING: Unauthorized access to Fabric APIs. Please review your Fabric permissions and Ensure you have proper Fabric licensing and permissions.")
        print("   📋 Check the following resources:")
        print("   • Fabric licenses: https://learn.microsoft.com/fabric/enterprise/licenses")
        print("   • Identity support: https://learn.microsoft.com/rest/api/fabric/articles/identity-support")
        print("   • Create Entra app with appropriate Fabric permissions: https://learn.microsoft.com/rest/api/fabric/articles/get-started/create-entra-app")
        sys.exit(0)  # Graceful exit with guidance
```

**Resolution**:
1. **Verify Fabric Licensing**: Ensure your organization has appropriate [Microsoft Fabric licenses](https://learn.microsoft.com/fabric/enterprise/licenses)
2. **Review Identity Configuration**: Follow the [Fabric Identity Support](https://learn.microsoft.com/rest/api/fabric/articles/identity-support) documentation
3. **Configure Service Principal**: If using a service principal, ensure it's properly configured following [Create Entra App](https://learn.microsoft.com/rest/api/fabric/articles/get-started/create-entra-app) guidance
4. **Check API Permissions**: Verify the deployment identity has the required Fabric REST API permissions as listed in the [prerequisites](#prerequisites)

The script performs a graceful exit (`sys.exit(0)`) rather than failing abruptly, allowing you to resolve permissions and retry the deployment.

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