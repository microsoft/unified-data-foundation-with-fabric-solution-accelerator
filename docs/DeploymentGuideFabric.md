# Deployment Guide for Medallion Architecture and PBI in Fabric

Deploy the **Unified Data Foundation with Fabric** solution accelerator using Azure Developer CLI - get a complete data platform with medallion architecture in minutes.

---

## Key Sections

| Section | Description |
|---------|-------------|
| [Prerequisites](#1-prerequisites) | Required permissions, tools, and setup |
| [Deployment Overview](#2-deployment-overview) | Overview of deployed resources and architecture |
| [Deployment Options](#3-deployment-options) | Local, cloud, and CI/CD deployment methods |
| [Deployment Commands](#4-deployment-commands) | One-command deployment instructions |
| [Deployment Results](#5-deployment-results) | Expected outcomes and verification steps |
| [Advanced Configuration Options](#6-advanced-configuration-options) | Optional customization parameters |
| [Known Limitations](#7-known-limitations) | Important constraints to review |
| [Environment Cleanup](#8-environment-cleanup) | How to remove deployed resources |
| [Additional Resources](#9-additional-resources) | Support and further reading |

### Alternative Deployment Methods

This guide focuses on automated deployment using Azure Developer CLI. For
manual deployment or existing Fabric capacity integration, refer to the
[Manual Deployment Guide](./DeploymentGuideFabricManual.md).

---

## 1. Prerequisites

To deploy this solution, ensure you have the following tools and permissions.

### Software Requirements

You need these tools installed to run the deployment commands.

| Tool | Version | Purpose | Download |
|------|---------|---------|----------|
| **Azure Developer CLI** | Latest | Orchestrates deployment | [Install azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) |
| **Azure CLI** | Latest | Authentication | [Install az](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **Python** | 3.9+ | Fabric configuration scripts | [Install Python](https://www.python.org/downloads/) |

> **💡 Tip**: You can skip installing tools by using [Azure Cloud Shell](https://shell.azure.com) or GitHub Codespaces.

### Permissions

Your deployment identity (User or Service Principal) requires the following permissions.

#### 🔐 Azure Permissions

- **Resource Group Access**: Ensure your deployment identity has permissions on target Resource Group to deploy Bicep templates and create Azure resources using appropriate [Azure RBAC built-in roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles) (e.g. has [Contributor](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#contributor) or [Owner](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#owner)) or appropriate [Azure RBAC custom role](https://learn.microsoft.com/azure/role-based-access-control/custom-roles) with necessary permissions
- **`Microsoft.Fabric` Resource Provider Access**: Verify your Azure Subscription has [Microsoft.Fabric resource provider](https://learn.microsoft.com/azure/azure-resource-manager/management/azure-services-resource-providers) enabled and your deployment identity has permissions on Resource Group to create [Microsoft Fabric capacity resource](https://learn.microsoft.com/azure/templates/microsoft.fabric/capacities?pivots=deployment-language-bicep)

#### 🔗 API Permissions

- **Microsoft Graph API - `User.Read`**: Delegated permission to read signed-in user profile information using [Microsoft Graph User permissions](https://learn.microsoft.com/graph/permissions-reference#user-permissions)
- **Microsoft Graph API - `openid`**: Delegated permission for sign in and user profile authentication using [OpenID Connect scopes](https://learn.microsoft.com/entra/identity-platform/scopes-oidc)
- **Fabric REST API - Workspace Management**: Access to create and manage Fabric workspaces for workspace structure deployment using [Fabric workspace APIs](https://learn.microsoft.com/rest/api/fabric/core/workspaces)
- **Fabric REST API - Item Creation**: Access to create lakehouses, notebooks, and reports for Fabric content deployment using [Fabric item APIs](https://learn.microsoft.com/rest/api/fabric/core/items)
- **Fabric REST API - Content Upload**: Access to upload files and manage workspace content for sample data and notebook deployment using [Fabric REST API scopes](https://learn.microsoft.com/rest/api/fabric/articles/scopes)
- **Power BI API - `Tenant.Read.All`**: Delegated permission to read organization's Power BI tenant information using [Power BI REST API permissions](https://learn.microsoft.com/rest/api/power-bi/#scopes)

<details>
<summary><strong>✅ Quick Check</strong> — Verify your tools are ready</summary>

```bash
# Check Azure CLI
az --version
az account show

# Check Azure Developer CLI
azd version

# Check Python
python --version
```

</details>

## 2. Deployment Overview

This solution accelerator uses a **two-phase deployment approach** to provision a complete data platform. The process is fully automated, idempotent, and safe to re-run.

### 1️⃣ Phase 1: Infrastructure (Azure)

*Powered by Bicep & Azure Resource Manager*
This phase creates the physical resources in your Azure subscription.

- **Resource Group**: A container for your resources.
- **Fabric Capacity**: The compute engine (F SKU) that powers your data workloads.

### 2️⃣ Phase 2: Data Platform (Fabric)

*Powered by Python & Fabric REST APIs*
This phase configures the logical architecture inside Microsoft Fabric through 10 deployment steps:

1. **Workspace Setup**: Creates or configures the workspace on your Capacity
2. **Workspace Administrators**: Adds administrators to the workspace
3. **Folder Structure**: Creates organized folder structure (lakehouses, notebooks, reports, environment)
4. **Lakehouses**: Deploys the Medallion Architecture (`Bronze` → `Silver` → `Gold`)
5. **Sample Data**: Loads sample CSV datasets into the Bronze lakehouse
6. **Notebooks**: Deploys 50+ notebooks for data transformation and management
7. **Data Pipelines**: Executes sequential data transformation jobs (Bronze→Silver→Gold)
8. **Power BI Reports**: Deploys Power BI reports and configures dataset connections
9. **Environment**: Creates Fabric Environment with custom Python libraries
10. **Data Agent**: Configures AI Data Agent with Lakehouse data source (preview feature)

#### Deployment Architecture

The Fabric deployment is orchestrated by [`deploy_udf_solution.py`](../infra/scripts/fabric/deploy_udf_solution.py), which coordinates modular helper functions:

| Helper Module | Purpose | Key Functions |
|---------------|---------|---------------|
| [`udf_workspace.py`](../infra/scripts/fabric/helpers/udf_workspace.py) | Workspace creation and capacity assignment | `setup_workspace()` |
| [`udf_workspace_admins.py`](../infra/scripts/fabric/helpers/udf_workspace_admins.py) | Administrator management with Graph API integration | `setup_workspace_administrators()` |
| [`udf_folder.py`](../infra/scripts/fabric/helpers/udf_folder.py) | Folder structure creation | `setup_folder_structure()` |
| [`udf_lakehouse.py`](../infra/scripts/fabric/helpers/udf_lakehouse.py) | Lakehouse deployment and data loading | `setup_lakehouses()`, `load_csv_data_to_lakehouse()` |
| [`udf_notebook.py`](../infra/scripts/fabric/helpers/udf_notebook.py) | Notebook deployment with lakehouse references | `deploy_notebooks()` |
| [`udf_jobs.py`](../infra/scripts/fabric/helpers/udf_jobs.py) | Sequential notebook execution | `schedule_notebook_jobs_sequential()` |
| [`udf_powerbi.py`](../infra/scripts/fabric/helpers/udf_powerbi.py) | Power BI report deployment and dataset configuration | `deploy_powerbi_reports()` |
| [`udf_environment.py`](../infra/scripts/fabric/helpers/udf_environment.py) | Environment creation with custom libraries | `setup_environment()` |
| [`udf_data_agent.py`](../infra/scripts/fabric/helpers/udf_data_agent.py) | Data Agent configuration | `setup_data_agent()` |
| [`utils.py`](../infra/scripts/fabric/helpers/utils.py) | Common utilities | Token replacement, file operations, logging |

This modular architecture enables:
- **Independent testing** of each deployment component
- **Graceful error handling** with detailed progress tracking
- **Easy customization** by modifying individual helper modules
- **Reusability** across different deployment scenarios

### 🔄 Idempotency & Re-runs

The deployment is designed to be **safe to re-run**. If you run `azd up` again:

- **Infrastructure**: Only updates settings if they have changed (e.g., resizing Capacity).
- **Workspace**: Detects existing workspace and skips creation.
- **Content**:
  - *Notebooks/Reports*: Updated to the latest version (overwrites changes).
  - *Data*: Preserved (sample data is re-uploaded if missing).
  - *Admins*: New admins are added; existing ones remain.

The deployment orchestration coordinates both phases, passing deployment parameters and ensuring proper sequencing. See [deployment options](#3-deployment-options) for different ways to run this deployment based on your preferred environment.

---

## 3. Deployment Options

Choose your deployment environment based on your workflow and requirements. All options use the same [Deployment commands](#4-deployment-commands) with environment-specific setup.

| Environment | Best For | Setup Required | Notes |
|-------------|----------|----------------|-------|
| **[Local Machine](#1-local-machine)** | Full development control | Install [software requirements](#software-requirements) | Most flexible, requires local setup |
| **[Azure Cloud Shell](#2-azure-cloud-shell)** | Zero setup | Just a web browser | Pre-configured tools, session timeouts |
| **[GitHub Codespaces](#3-github-codespaces)** | Team consistency | GitHub account | Cloud development environment |
| **[Visual Studio Code (WEB)](#4-visual-studio-code-web)** | Zero setup| Just a web browser | Web-based VS Code, session timeouts |
| **[Dev Container](#5-vs-code-dev-container)** | Standardized tooling | Docker Desktop + VS Code | Containerized consistency |
| **[GitHub Actions](#6-github-actions-cicd)** | Automated CI/CD | Service principal setup | Production deployments |

<details>
<summary><strong>1. Local Machine</strong></summary>

Deploy with full control over your development environment.

**Setup requirements**: Install the [software requirements](#software-requirements)

**Deployment**: Use the standard [Deployment commands](#4-deployment-commands)

</details>

<details>
<summary><strong>2. Azure Cloud Shell</strong></summary>

Deploy from Azure's browser-based terminal with zero local installation.

**Setup**: Open [Azure Cloud Shell](https://shell.azure.com) and install Azure Developer CLI:

```bash

curl -fsSL https://aka.ms/install-azd.sh | bash && exec bash
```

**Deployment**: Run the [Deployment commands](#4-deployment-commands) (Azure CLI pre-authenticated)

</details>

<details>
<summary><strong>3. GitHub Codespaces</strong></summary>

Deploy from a cloud development environment with pre-configured tools.

**Setup**:

1. Go to the [Unified Data Foundation with Fabric solution in GitHub Codespace](https://codespaces.new/microsoft/unified-data-foundation-with-fabric-solution-accelerator?quickstart=1)
2. Follow the instructions on screen to create a new codespace with default setup.
3. Wait for the environment to initialize (2-3 minutes)
4. All tools are pre-installed; proceed to deployment

**Deployment**: Install azd and run [Deployment commands](#4-deployment-commands) with device authentication:

```bash
# Install azd if needed
curl -fsSL https://aka.ms/install-azd.sh | bash && exec bash

# Use device code authentication  
az login --use-device-code
azd auth login --use-device-code

# Continue with deployment commands
```

</details>

<details>
<summary><strong>4. Visual Studio Code (WEB)</strong></summary>

Deploy from VS Code in the browser with zero local installation.

**Setup**:

1. Open the following link to launch VS Code Web:

    [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvdW5pZmllZC1kYXRhLWZvdW5kYXRpb24td2l0aC1mYWJyaWMtc29sdXRpb24tYWNjZWxlcmF0b3IvcmVmcy9oZWFkcy9tYWluL2luZnJhL3ZzY29kZV93ZWIiLCAiaW5kZXhVcmwiOiAiL2luZGV4Lmpzb24iLCAidmFyaWFibGVzIjogeyJhZ2VudElkIjogIiIsICJjb25uZWN0aW9uU3RyaW5nIjogIiIsICJ0aHJlYWRJZCI6ICIiLCAidXNlck1lc3NhZ2UiOiAiIiwgInBsYXlncm91bmROYW1lIjogIiIsICJsb2NhdGlvbiI6ICIiLCAic3Vic2NyaXB0aW9uSWQiOiAiIiwgInJlc291cmNlSWQiOiAiIiwgInByb2plY3RSZXNvdXJjZUlkIjogIiIsICJlbmRwb2ludCI6ICIifSwgImNvZGVSb3V0ZSI6IFsiYWktcHJvamVjdHMtc2RrIiwgInB5dGhvbiIsICJkZWZhdWx0LWF6dXJlLWF1dGgiLCAiZW5kcG9pbnQiXX0=)
2. When prompted, sign in using your Microsoft account linked to your Azure subscription. 
   Select the appropriate subscription to continue.
3. Once the solution opens, the AI Foundry terminal will automatically start running the following command to install the required dependencies:

    ```bash
    sh install.sh
    ```

   During this process, you’ll be prompted with the message:

    ```text
    What would you like to do with these files?
    - Overwrite with versions from template
    - Keep my existing files unchanged
    ```

    Choose “**Overwrite with versions from template**” and provide a unique environment name when prompted.

**Deployment**: Install azd and run [Deployment commands](#4-deployment-commands) with device authentication:

```bash
# Install azd if needed
curl -fsSL https://aka.ms/install-azd.sh | bash && exec bash

# Use device code authentication  
az login --use-device-code
azd auth login --use-device-code

# Continue with deployment commands
```

</details>

<details>
<summary><strong>5. VS Code Dev Container</strong></summary>

Deploy from a containerized environment for team consistency.

**Setup**:

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop) and [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone repository and open in VS Code
3. Reopen in container when prompted

**Deployment**: All tools pre-installed - run [Deployment commands](#4-deployment-commands) directly

</details>

<details>
<summary><strong>6. GitHub Actions (CI/CD)</strong></summary>

Automated deployment using the included [workflow](../.github/workflows/azure-dev.yml).

**Setup**: Configure [repository variables](https://docs.github.com/en/actions/learn-github-actions/variables) and set up [service principal with federated credentials](https://learn.microsoft.com/azure/developer/github/connect-from-azure)

**Triggers**: Push to main branch or manual workflow dispatch

</details>

---

## 4. Deployment Commands

**One-command deployment** - Deploy everything with Azure Developer CLI ([prerequisites required](#1-prerequisites)):

```bash
# Clone and navigate to repository
git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
cd unified-data-foundation-with-fabric-solution-accelerator

# Authenticate (required)
az login
azd auth login

# Optional: Customize workspace name
azd env set FABRIC_WORKSPACE_NAME "My Analytics Platform"

# Deploy everything
azd up
```

During deployment, you'll specify:

- **Environment name** (e.g., "udfwf-dev"). This will be used to build the name of the deployed Azure resources.
- **Azure subscription**.
- **Azure resource group**.

**What you get**: Complete medallion architecture with Fabric capacity, lakehouses (Bronze/Silver/Gold), notebooks, sample data, and Power BI reports.

> **💡 Alternative Deployment Option**
> This guide uses Azure Developer CLI for automated deployment. If you prefer more granular control or have an existing Fabric capacity, see the [Manual Deployment Guide](./DeploymentGuideFabricManual.md).

### Next Steps

- **First deployment**: Follow the commands above - they work in [multiple environments](#3-deployment-options)
- **Need different setup**: See [deployment environment options](#3-deployment-options) (Cloud Shell, Codespaces, etc.)
- **Understand the process**: Review [deployment overview](#2-deployment-overview) for technical details
- **See what's created**: Check [deployment results](#5-deployment-results) for detailed component overview with screenshots
- **Want to customize**: Explore [configuration options](#6-advanced-configuration-options) for naming, capacity sizing, and admin setup
- **Limitations**: Review [known limitations](#7-known-limitations) for common issues and workarounds
- **Remove environment**: Use [environment cleanup](#8-environment-cleanup) to completely remove your deployment

---

## 5. Deployment Results

After successful deployment, you'll have a complete data platform implementing medallion architecture.

### Azure Infrastructure

| Resource | Purpose |
|----------|---------|
| **[Fabric Capacity](https://learn.microsoft.com/fabric/admin/capacity-settings?tabs=power-bi-premium)** | Dedicated compute for Fabric workloads |

![Screenshot of deployed Azure resources](./images/deployment/fabric/azure_resources.png)

### Fabric Components

#### Fabric Workspace

Workspace created with the specified or default name.

![Screenshot of resulting Fabric workspace](./images/deployment/fabric/fabric_workspace.png)

#### Folder Structure

```text
your-workspace/
├── lakehouses/          # Bronze, Silver, Gold lakehouses
├── notebooks/           # Data transformation pipelines
│   ├── bronze_to_silver/
│   ├── silver_to_gold/
│   ├── data_management/
│   └── schema/
└── reports/            # Power BI dashboards
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

#### Notebooks

**Automation Components** (50+ notebooks total):

- **Orchestration notebooks** (2): `run_bronze_to_silver`, `run_silver_to_gold` - Main pipeline execution
- **Bronze to Silver transformations** (17): Domain-specific data processing for finance, sales, and shared entities
- **Silver to Gold transformations** (19): Business-ready aggregations and data modeling
- **Schema definitions** (8): Data models for Silver and Gold layers across all domains
- **Data management utilities** (5): Table operations, troubleshooting, and maintenance tools
- **Data Agent configuration** (1): AI Data Agent setup notebook

![Screenshot of resulting Fabric notebooks](./images/deployment/fabric/fabric_notebooks.png)

#### Power BI Reports

Power BI reports are automatically deployed as part of **Step 8** of the deployment process. Any `.pbix` files found in the `reports/` directory will be deployed to the workspace's reports folder with automatic dataset configuration:

- **Report Deployment**: Scans recursively through the reports directory and uploads each report
- **Conflict Resolution**: Uses Create or Overwrite mode for idempotent deployments
- **Dataset Configuration**: Automatically configures dataset parameters to connect to the Gold lakehouse SQL endpoint
  - Updates `ServerName` parameter with lakehouse connection string
  - Updates `DatabaseName` parameter with lakehouse name
- **Folder Organization**: Assigns reports to the reports folder within the workspace
- **Error Handling**: Continues deployment if individual reports fail, with detailed logging

**Note**: Dataset parameter updates require appropriate Power BI API permissions. Service Principals may experience limitations - see [Known Limitations](#7-known-limitations) for details.

##### PowerBI files

![Screenshot of resulting PowerBI reports](./images/deployment/fabric/fabric_powerbi_reports.png)

##### PowerBI Dashboard

![Screenshot of resulting PowerBI dashboard](./images/deployment/fabric/fabric_powerbi_dashboard.png)

---

## 6. Advanced Configuration Options

The solution accelerator provides flexible configuration options to customize your deployment. Parameters can be configured through **Azure Developer CLI environment variables** (`azd env set`) for local deployments or through **GitHub repository variables** for CI/CD deployments.

> **📁 Configuration Files Reference:**
>
> - Infrastructure: [`infra/main.bicep`](../infra/main.bicep) - Azure resource definitions
> - Deployment orchestration: [`azure.yaml`](../azure.yaml) - AZD project configuration  
> - CI/CD workflow: [`.github/workflows/azure-dev.yml`](../.github/workflows/azure-dev.yml) - GitHub Actions pipeline
> - Fabric deployment: [`infra/scripts/fabric/deploy_udf_solution.py`](../infra/scripts/fabric/deploy_udf_solution.py) - Fabric workspace setup orchestrator
> - Helper modules: [`infra/scripts/fabric/helpers/`](../infra/scripts/fabric/helpers/) - Modular deployment functions

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

*GitHub Actions can use additional parameters through Bicep parameter files or workflow modifications.*

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

Customize the Fabric workspace setup and naming conventions. These parameters are used by the [`deploy_udf_solution.py`](../infra/scripts/fabric/deploy_udf_solution.py) script during post-provisioning.

> **⚠️ Important**: Variables marked as "Bicep output" (like `AZURE_FABRIC_CAPACITY_NAME`, `SOLUTION_SUFFIX`, `AZURE_FABRIC_CAPACITY_ADMINISTRATORS`) are automatically set by the deployment process and should **NOT** be manually configured. These are outputs from [`main.bicep`](../infra/main.bicep) and will be populated after infrastructure deployment.

<details>
<summary><strong>Workspace Settings</strong></summary>

| Parameter | AZD Environment Variable | GitHub Actions Variable | Description | Default | Example |
|-----------|-------------------------|------------------------|-------------|---------|---------|
| **Capacity Name** | `AZURE_FABRIC_CAPACITY_NAME` | Bicep output (auto-set) | Microsoft Fabric capacity name - **DO NOT SET MANUALLY** (automatically populated from Bicep deployment) | Generated from Bicep | `fc-udfwfsa-abc123` |
| **Workspace Name** | `FABRIC_WORKSPACE_NAME` | `FABRIC_WORKSPACE_NAME` | Custom name for the Fabric workspace | `Unified_Data_Foundation_{solution_suffix}` | `"MyCompany Data Foundation"`, `"Analytics Platform - DEV"` |

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

```bash
azd env set FABRIC_WORKSPACE_NAME "Analytics Platform - DEV"
azd up
```

</details>

<details>
<summary><strong>🚀 GitHub Actions</strong></summary>

Modify [`azure-dev.yml`](../.github/workflows/azure-dev.yml) environment variables:

```yaml
env:
  FABRIC_WORKSPACE_NAME: "Analytics Platform (dev)"
```

</details>

**Workspace Naming Best Practices:**

- Use descriptive names that indicate purpose and environment
- Consider organizational naming conventions
- Include environment indicators for multi-environment deployments (Dev, Test, Prod)
- Avoid special characters that might cause conflicts with Fabric APIs

</details>

### 👥 Fabric Workspace Administrator Configuration

Manage workspace administrators and security permissions for the Fabric workspace. These parameters are processed by both the Bicep template ([`main.bicep`](../infra/main.bicep)) for capacity-level admins and the Fabric deployment script ([`deploy_udf_solution.py`](../infra/scripts/fabric/deploy_udf_solution.py)) for workspace-level admins.

<details>
<summary><strong>Admin Assignment Options</strong></summary>

| Parameter | AZD Environment Variable | GitHub Actions Support | Description | Format | Example |
|-----------|-------------------------|------------------------|-------------|--------|---------|
| **Capacity Administrators** | `AZURE_FABRIC_CAPACITY_ADMINISTRATORS` | Bicep output (auto-set) | **DO NOT SET MANUALLY** - Automatically populated from Bicep deployment with capacity-level administrators | JSON array (read-only) | `["user1@contoso.com", "12345678-1234-1234-1234-123456789012"]` |
| **Workspace Administrators** | `FABRIC_WORKSPACE_ADMINISTRATORS` | Via environment variables | Comma-separated list of workspace-level administrator identities. Accepts **User Principal Names (UPNs)** like `user@domain.com` OR **Azure Entra ID Object IDs (GUIDs)** obtained from Azure portal | Comma-separated string | `"user@contoso.com, admin@contoso.com"` OR `"87654321-4321-4321-4321-210987654321, 12345678-1234-1234-1234-123456789012"` |

*GitHub Actions workflow uses Bicep output for admin configuration. See examples below for customization.*

**Administrator Identity Formats:**

`FABRIC_WORKSPACE_ADMINISTRATORS` accepts flexible identity formats:

- **User Principal Names (UPNs)**: `user@domain.com` format for individual users (requires Graph API permissions to resolve)
- **Azure Entra ID Object IDs (GUIDs)**: `12345678-1234-1234-1234-123456789012` format - recommended when Graph API permissions are unavailable
  - Get user object IDs: `az ad user show --id user@contoso.com --query id -o tsv`
  - Get service principal object IDs: `az ad sp show --id <app-id> --query id -o tsv`
- **Mixed Format**: Combine UPNs and GUIDs in the same comma-separated list

**Configuration Examples:**

<details>
<summary><strong>🖥️ Azure Developer CLI</strong></summary>

```bash
# NOTE: Do NOT manually set AZURE_FABRIC_CAPACITY_ADMINISTRATORS - it's automatically set by Bicep deployment

# Option 1: Set workspace administrators using UPNs (requires Graph API permissions)
azd env set FABRIC_WORKSPACE_ADMINISTRATORS "user@contoso.com, admin@contoso.com"

# Option 2: Set workspace administrators using Azure Entra ID Object IDs (recommended when Graph API unavailable)
azd env set FABRIC_WORKSPACE_ADMINISTRATORS "87654321-4321-4321-4321-210987654321, 12345678-1234-1234-1234-123456789012"

# Option 3: Mix UPNs and Object IDs
azd env set FABRIC_WORKSPACE_ADMINISTRATORS "user@contoso.com, 12345678-1234-1234-1234-123456789012"

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

Configure deployment behavior and troubleshooting options. These parameters are handled by the PowerShell orchestration script ([`Run-PythonScript.ps1`](../infra/scripts/utils/Run-PythonScript.ps1)).

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

These parameters are automatically optimized in [`azure.yaml`](../azure.yaml):

```yaml
hooks:
  postprovision:
    windows:
      shell: pwsh
      run: ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/deploy_udf_solution.py"
      interactive: true
      continueOnError: false
    posix:
      shell: pwsh
      run: ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/deploy_udf_solution.py" -SkipPythonVirtualEnvironment
      interactive: true
      continueOnError: false
  predown:
    windows:
      shell: pwsh
      run: ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/remove_udf_solution.py"
      interactive: true
      continueOnError: false
    posix:
      shell: pwsh
      run: ./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/remove_udf_solution.py" -SkipPythonVirtualEnvironment
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
    pwsh ./infra/scripts/utils/Run-PythonScript.ps1 `
      -ScriptPath "infra/scripts/fabric/deploy_udf_solution.py" `
      -SkipPythonVirtualEnvironment `
      -SkipPythonDependencies `
      -SkipPipUpgrade
```

</details>

</details>

---

## 7. Known Limitations

This section documents known limitations in the deployment process and their workarounds.

### 🔒 Power BI API Parameter Updates

**Issue**: Service Principals cannot update Power BI dataset parameters via API, resulting in HTTP 403 errors.

**Impact**:

- During automated deployment, if deployment identity is a Service Principal or a Managed Identity, Power BI reports are deployed but dataset parameters (SQL endpoint connection strings) may not be automatically configured
- Reports may show connection errors until manually configured

**Technical Details**:
Power BI dataset parameter updates are handled by the deployment process. Note that Service Principals may have restricted API access for this operation.

```python
# From the deployment helper modules
try:
    powerbi_client.update_powerbi_dataset_parameters(
        dataset_id=dataset['id'], 
        parameters=[
            {"name": "sqlEndpoint", "newValue": sql_endpoint},
            {"name": "database", "newValue": lakehouse_name}
        ]
    )
    print(f"✅ Dataset parameters updated successfully for '{report_name}'")
except Exception as param_error:
    if "HTTP 403" in str(param_error):
        print(f"⚠️ WARNING: Cannot update dataset parameters automatically")
        print(f"    Manual configuration required in Power BI service")
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
The [`udf_workspace_admins.py`](../infra/scripts/fabric/helpers/udf_workspace_admins.py) helper module implements fallback logic:

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

1. **Use Object IDs Directly**: Configure administrators using their Azure AD object IDs, which don't require Graph API resolution. Get object IDs using Azure CLI:

   ```bash
   # Get user object ID
   az ad user show --id user@contoso.com --query id -o tsv
   
   # Set administrators using object IDs (comma-separated)
   azd env set FABRIC_WORKSPACE_ADMINISTRATORS "87654321-4321-4321-4321-210987654321, 12345678-1234-1234-1234-123456789012"
   azd up
   ```

   The helper module automatically detects whether an identifier is a UPN or object ID and handles accordingly.

2. **Post-Deployment Admin Assignment**: If Graph API permissions cannot be granted, add administrators manually after deployment through the Fabric portal workspace settings, or use the dedicated helper module [`udf_workspace_admins.py`](../infra/scripts/fabric/helpers/udf_workspace_admins.py) with appropriate credentials that have Graph API access.

---

### 🔐 Fabric REST API Permission Issues

**Issue**: Service Principals may lack sufficient permissions to access Microsoft Fabric REST APIs.

**Impact**:

- Deployment fails during workspace creation or management operations
- Graceful exit with clear guidance on permission requirements

**Technical Details**:
The [`deploy_udf_solution.py`](../infra/scripts/fabric/deploy_udf_solution.py) script provides specific error handling for authorization failures:

```python
except FabricApiError as e:
    if e.status_code == 401:
        print(f"⚠️ WARNING: Unauthorized access to Fabric APIs. Please review your Fabric permissions and ensure you have proper Fabric licensing and permissions.")
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
4. **Check API Permissions**: Verify the deployment identity has the required Fabric REST API permissions as listed in the [prerequisites](#1-prerequisites)

The script performs a graceful exit (`sys.exit(0)`) rather than failing abruptly, allowing you to resolve permissions and retry the deployment.

---

## 8. Environment Cleanup

When you no longer need your deployed environment, Azure Developer CLI provides a streamlined approach to completely remove all resources and clean up your Microsoft Fabric workspace.

### Complete Environment Removal

The `azd down` command orchestrates a complete environment cleanup process that:

1. **Removes Fabric Workspace**: Safely deletes the Microsoft Fabric workspace and all associated items
2. **Deprovisions Azure Resources**: Removes all Azure infrastructure components deployed via Bicep templates
3. **Preserves Local Environment**: Keeps your local development environment and configurations intact

**Quick cleanup command:**

```bash
# Navigate to your solution directory
cd unified-data-foundation-with-fabric-solution-accelerator

# Remove everything deployed by azd up
azd down
```

### Cleanup Process Details

Based on the [`azure.yaml`](../azure.yaml) configuration, the cleanup process follows these orchestrated steps:

#### Phase 1: Fabric Workspace Cleanup (predown hook)

Before removing Azure infrastructure, the cleanup process first handles the Microsoft Fabric workspace:

**Windows (PowerShell):**

```powershell
./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/remove_udf_solution.py"
```

**Unix/Linux (PowerShell Core):**

```bash
./infra/scripts/utils/Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/remove_udf_solution.py" -SkipPythonVirtualEnvironment
```

This orchestration script ([`Run-PythonScript.ps1`](../infra/scripts/utils/Run-PythonScript.ps1)) manages:

- **Python Environment Setup**: Creates or reuses Python virtual environment with required dependencies
- **Script Execution**: Runs the specified Python script with proper error handling
- **Cross-Platform Support**: Handles differences between Windows and Unix-based systems

The core removal logic is handled by [`remove_udf_solution.py`](../infra/scripts/fabric/remove_udf_solution.py), which:

- **Workspace Lookup**: Finds the workspace by name or ID (defaults to "Unified Data Foundation with Fabric workspace")
- **Comprehensive Removal**: Deletes all workspace items including notebooks, lakehouses, and datasets
- **Confirmation Prompts**: Provides interactive confirmation to prevent accidental deletions
- **Error Handling**: Gracefully handles missing workspaces or permission issues

#### Phase 2: Azure Infrastructure Cleanup

After successful Fabric workspace removal, `azd down` proceeds to deprovision all Azure resources that were created through the [`main.bicep`](../infra/main.bicep) template, including:

- **Microsoft Fabric Capacity**: Dedicated compute resources
- **Resource Group**: Complete resource group removal (if specified)

### Safety Features

The cleanup process includes several safety mechanisms:

- **Interactive Confirmation**: Prompts before deleting workspaces to prevent accidental removal
- **Graceful Error Handling**: Continues with infrastructure cleanup even if Fabric workspace removal fails
- **Detailed Logging**: Provides comprehensive output for troubleshooting and audit purposes
- **Non-Destructive Failures**: Missing workspaces or permission issues don't prevent infrastructure cleanup

---

## 9. Additional Resources

- **Documentation**: [Microsoft Fabric](https://learn.microsoft.com/fabric/) | [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- **Guides**: [Power BI Deployment](./DeploymentGuidePowerBI.md) | [FAQs](./FAQs.md)
- **Repository**: [Solution Accelerator](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator)

For support, visit the [project repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator) or engage with the Microsoft Fabric community.

