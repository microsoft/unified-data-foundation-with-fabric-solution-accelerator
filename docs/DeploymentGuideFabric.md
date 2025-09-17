# Microsoft Fabric Deployment Guide

This guide describes how to deploy the Microsoft Fabric components of the **Unified Data Foundation with Fabric** solution accelerator. It includes deployment of [Fabric lakehouses](https://learn.microsoft.com/fabric/data-engineering/lakehouse-overview), [notebooks](https://learn.microsoft.com/fabric/data-engineering/how-to-use-notebook), sample data, and folder structure.

---

## Prerequisites

Before starting, ensure the following:

- A **Microsoft Fabric workspace** has been provisioned. If not, follow steps in [Provisioning of Microsoft Fabric](./SetupFabric.md).
- You have **Contributor or Admin** [permissions](https://learn.microsoft.com/fabric/fundamentals/roles-workspaces) in the Fabric workspace  

**Required tools:**

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) - for authentication
- [Python 3.9+](https://www.python.org/downloads/) - for running deployment scripts
- [Git](https://git-scm.com/downloads) - for cloning the repository

---

## Deployment Options

Choose from the following deployment environments based on your preference and setup:

| GitHub Codespaces | [![Azure Cloud Shell](https://img.shields.io/static/v1?style=for-the-badge&label=Azure%20Cloud%20Shell&message=Open&color=blue&logo=microsoft-azure)](https://portal.azure.com/#cloudshell/) | Local Environment |
|---|---|---|

<details>
  <summary><b>Deploy in GitHub Codespaces</b></summary>

### GitHub Codespaces

You can run this solution using GitHub Codespaces in your own fork of the repository:

1. **Fork the repository first:**
   - Navigate to the main repository on GitHub
   - Click the **Fork** button in the top-right corner
   - Select your account to create a fork

2. **Open your fork in GitHub Codespaces:**
   - In your forked repository, click the **Code** button
   - Select the **Codespaces** tab
   - Click **Create codespace on main** (this may take several minutes)

   Alternatively, you can use this direct link format with your GitHub username:
   ```
   https://codespaces.new/YOUR-GITHUB-USERNAME/MaagDataFoundationForAI
   ```

3. Accept the default values on the create Codespaces page.
4. Open a terminal window if it is not already open.
5. Continue with the [Fabric Items Deployment](#fabric-items-deployment) steps.

</details>

<details>
  <summary><b>Deploy in Azure Cloud Shell</b></summary>

### Azure Cloud Shell

You can run the Fabric deployment directly from Azure Cloud Shell without needing to install anything locally:

1. Open [Azure Cloud Shell](https://portal.azure.com/#cloudshell/) in your browser.

2. Clone the repository:
   ```bash
   git clone <repository-url>
   cd MaagDataFoundationForAI
   ```

3. Navigate to the deployment directory:
   ```bash
   cd infra/scripts/fabric
   ```

4. Continue with the [Fabric Items Deployment](#fabric-items-deployment) steps using the bash script.

</details>

<details>
  <summary><b>Deploy in Local Environment</b></summary>

### Local Environment

If you're deploying from your local machine, ensure you have the required tools installed:

1. **Required tools:**
   - [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
   - [Python 3.9+](https://www.python.org/downloads/)
   - [Git](https://git-scm.com/downloads)

2. **Clone the repository:**
   ```shell
   git clone <repository-url>
   cd MaagDataFoundationForAI
   ```

3. Continue with the [Fabric Items Deployment](#fabric-items-deployment) steps.

</details>

---

## Overview

The Microsoft Fabric deployment creates a complete medallion architecture with:

- **Folder Structure**: Organized folders for lakehouses, notebooks, and reports
- **Lakehouses**: Three-tier architecture (Bronze, Silver, Gold) with schema support
- **Sample Data**: Representative CSV files uploaded to the bronze lakehouse
- **Notebooks**: Complete set of data transformation and management notebooks
- **Automated Processing**: Initial data pipeline execution
- **Power BI Reports**: Automated deployment of Power BI reports (.pbix files) to the workspace

### Data Architecture

The MAAG solution follows a medallion architecture pattern:

- **Bronze Layer** (`maag_bronze`): Raw data ingestion from CSV files
- **Silver Layer** (`maag_silver`): Cleaned and standardized data  
- **Gold Layer** (`maag_gold`): Business-ready aggregated data

### Notebook Categories

- **Bronze to Silver**: Data cleansing and standardization notebooks
- **Silver to Gold**: Business logic and aggregation notebooks
- **Data Management**: Utilities for managing tables and troubleshooting
- **Schema**: Data model definitions for each layer

### Power BI Reports

The deployment automatically discovers and deploys any Power BI report files (`.pbix`) found in the `reports/` directory of the repository. Reports are:
- Deployed to the `reports/` folder within the Fabric workspace
- Configured with appropriate conflict resolution (Create or Overwrite)
- Tracked for deployment verification and final summary reporting

---

## Fabric Items Deployment

> ⚠️ **Important: File Replacement Behavior**
> 
> The deployment script (`create_fabric_items.py`) is designed to **always replace** existing CSV files, notebooks, and Power BI reports that have the same name as those in the repository. This behavior is **intentional** and ensures that when deploying a new version of the repository, all components are updated to the latest version.
> 
> **What gets replaced:**
> - All sample CSV files in the bronze lakehouse
> - All notebooks with matching names
> - All Power BI reports (.pbix files) with matching names
> 
> **Impact:** Any manual changes you made to these files will be overwritten. If you have customized notebooks, reports, or data files, ensure you:
> - Back them up before deployment
> - Rename them to avoid conflicts
> - Or apply your customizations after deployment
> 
> This design ensures consistency and repeatability when deploying solution updates.

### 1. Workspace Setup

Ensure you have a Microsoft Fabric workspace available. Note your **workspace ID** as it will be required for the deployment script.

### 2. Authentication

Login to Azure using the Azure CLI:

```bash
az login
```

Ensure you have appropriate permissions in the target Fabric workspace (see [pre-requisites](#prerequisites)).

### 3. Navigate to Deployment Directory

```bash
cd infra/scripts/fabric
```

### 4. Run Deployment Script

Choose the appropriate script for your platform:

#### For Linux/macOS/Cloud Shell (Bash)

```bash
# Make the script executable
chmod +x provision_fabric_items.sh

# Run the deployment
./provision_fabric_items.sh <fabric-workspace-id>
```

#### For Windows Local (PowerShell)

> ⚠️ **Important Note for PowerShell Users**
> 
> If you encounter issues running PowerShell scripts due to execution policy restrictions, temporarily adjust the `ExecutionPolicy`:
> 
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
> 
> This allows scripts to run for the current session without permanently changing system policy.

```powershell
# Run the PowerShell script
.\provision_fabric_items.ps1 -FabricWorkspaceId "<fabric-workspace-id>"
```

#### For GitHub Codespaces

```bash
# Codespaces comes with Python and Azure CLI pre-installed
# Navigate to the fabric deployment directory
cd infra/scripts/fabric

# Make the script executable
chmod +x provision_fabric_items.sh

# Run the deployment
./provision_fabric_items.sh <fabric-workspace-id>
```

**Example Usage:**

```bash
# Bash/Cloud Shell/Codespaces example
./provision_fabric_items.sh "12345678-1234-1234-1234-123456789abc"
```

```powershell
# PowerShell example (Windows local only)
.\provision_fabric_items.ps1 -FabricWorkspaceId "12345678-1234-1234-1234-123456789abc"
```

### 5. Monitor Deployment Progress

The script will perform the following operations in sequence:

1. **Environment Setup**: Install Python dependencies from `requirements.txt`
2. **Authentication**: Use Azure CLI credentials for Fabric API access
3. **Folder Creation**: Create organized folder hierarchy
4. **Lakehouse Deployment**: Create bronze, silver, and gold lakehouses
5. **Data Upload**: Upload sample CSV files with proper structure
6. **Notebook Deployment**: Upload and configure all notebooks with lakehouse attachments
7. **Initial Processing**: Execute transformation notebooks for initial data processing
8. **Power BI Report Deployment**: Discover and deploy any .pbix files from the reports directory

### 6. Review Deployment Summary

Upon successful completion, the script provides a comprehensive deployment summary showing:

```
🎉 Unified Data Foundation with Fabric deployment completed successfully!
✅ Workspace: [Your Workspace Name]
✅ Lakehouses: 3 created (Bronze, Silver, Gold)
✅ Notebooks: [X] deployed
✅ Sample data: [X] files uploaded
✅ Pipelines: 2 executed successfully
✅ Power BI Reports: [X] deployed
   📊 Report Name 1 (ID: report-id-1)
   📊 Report Name 2 (ID: report-id-2)
```

This summary helps verify that all components were deployed successfully and provides reference information for the created resources.

---

## What Gets Created

### Folder Structure

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

### Lakehouses

| Name | Purpose | Schema Support |
|------|---------|----------------|
| `maag_bronze` | Raw data ingestion | Enabled |
| `maag_silver` | Cleaned, standardized data | Enabled |
| `maag_gold` | Business-ready aggregated data | Enabled |

![Screenshot of resulting Fabric lakehouses](./images/deployment/fabric/fabric_lakehouses.png)

### Sample Data

The solution includes sample data for:
- **Finance data**: accounts, invoices, payments
- **Sales data**: orders, order lines, payments from multiple sources
- **Shared reference data**: customers, products, locations, categories

![Screenshot of resulting Fabric sample data](./images/deployment/fabric/fabric_sample_data.png)

### Notebooks

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

### Power BI Reports

Any `.pbix` files found in the `reports/` directory will be automatically deployed to the workspace's reports folder. The deployment process:
- Scans recursively through the reports directory
- Uploads each Power BI report with conflict resolution (Create or Overwrite)
- Assigns reports to the appropriate folder within the workspace
- Provides deployment tracking and verification

![Screenshot of resulting PowerBI reports](./images/deployment/fabric/fabric_powerbi_reports.png)

---

## Post-Deployment Verification

### 1. Verify Deployment

- Open your Microsoft Fabric workspace
- Confirm lakehouses (`maag_bronze`, `maag_silver`, `maag_gold`) exist
- Check notebooks are organized in correct folder structure
- Verify sample data uploaded to bronze lakehouse
- Confirm Power BI reports are deployed to the reports folder (if .pbix files were present)

### 2. Explore the Data

- Navigate to bronze lakehouse to see uploaded CSV files
- Open notebooks to understand transformation logic
- Review data in silver and gold lakehouses
- Open deployed Power BI reports to explore business insights

### 3. Test Manual Execution

Run orchestration notebooks manually if needed:
- Execute `run_bronze_to_silver` to verify bronze-to-silver pipeline
- Execute `run_silver_to_gold` to verify silver-to-gold pipeline
- Open Power BI reports to validate data connectivity and visualizations

---

## Troubleshooting

| Issue | Possible Cause | Resolution |
|-------|----------------|------------|
| Authentication Issues | Not logged in or insufficient permissions | Run `az login` and verify workspace permissions |
| Workspace Not Found | Incorrect workspace ID | Verify workspace ID is correct and accessible |
| Permission Errors | Insufficient Fabric workspace rights | Ensure Contributor or Admin role in workspace |
| Network Issues | Firewall or connectivity problems | Check internet connection and Fabric API access |
| Python Dependencies | Missing Python or pip | Ensure Python 3.9+ and pip are properly installed |
| Script Execution Error | Policy restrictions (Windows) | Use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Power BI Report Upload Failed | Invalid .pbix file or insufficient Power BI permissions | Verify .pbix file integrity and Power BI workspace access |
| Codespaces Timeout | Long-running operation | Increase Codespaces timeout or run script in segments |
| Cloud Shell Session Expired | Session timeout | Re-authenticate and resume from last successful step |

### Environment-Specific Troubleshooting

#### GitHub Codespaces
- **Issue**: Codespaces environment timeout during long operations
- **Solution**: The deployment typically completes within 10-15 minutes. If timeout occurs, restart Codespaces and re-run the script.
- **Issue**: Directory navigation in Codespaces
- **Solution**: Ensure you navigate to the correct path: `cd infra/scripts/fabric` before running the script.

#### Azure Cloud Shell
- **Issue**: Cloud Shell session expires during deployment
- **Solution**: Cloud Shell sessions last 20 minutes by default. For longer operations, periodically interact with the shell or restart if needed.
- **Issue**: Storage mount issues
- **Solution**: Ensure your Cloud Shell storage is properly mounted and accessible.

#### Local Environment
- **Issue**: Azure CLI not authenticated
- **Solution**: Run `az login` and follow the authentication flow
- **Issue**: Python/pip not found
- **Solution**: Ensure Python 3.9+ is installed and added to your system PATH
- **Issue**: Script not found error
- **Solution**: Verify you're in the correct directory: `infra/scripts/fabric`

### Common Resolution Steps

1. **Verify Prerequisites**: Ensure all required tools are installed
2. **Check Authentication**: Confirm Azure CLI login status with `az account show`
3. **Validate Permissions**: Verify workspace access rights in Fabric portal
4. **Review Logs**: Check script output for specific error messages
5. **Retry Individual Steps**: Re-run specific components if needed

---