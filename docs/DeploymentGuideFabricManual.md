# Manual Microsoft Fabric Deployment Guide

This guide describes how to deploy the **Unified Data Foundation with Fabric** solution accelerator using manual deployment scripts for users who prefer more granular control over the deployment process.

## When to Use Manual Scripts

- You need granular control over the deployment process
- You're working in a restricted environment where azd can't be installed
- You want to deploy only specific components
- You're integrating with existing automation pipelines
- You have existing Fabric capacity and want to use manual scripts only

## Prerequisites for Manual Deployment

- **Microsoft Fabric capacity** must already exist
- **Azure CLI** installed and authenticated (`az login`)
- **Python 3.9+** with pip
- **Git** for cloning the repository

## Environment Variables

### Required Variables

- `AZURE_FABRIC_CAPACITY_NAME`: Name of existing Fabric capacity

### Optional Variables

- `AZURE_FABRIC_WORKSPACE_NAME`: Custom workspace name (defaults to generated name if not specified)

## Quick Manual Deployment

### 1. Set Environment Variables

**Linux/macOS/Cloud Shell:**
```bash
export AZURE_FABRIC_CAPACITY_NAME="your-existing-capacity-name"
export AZURE_FABRIC_WORKSPACE_NAME="Custom Workspace Name"  # Optional
```

**Windows PowerShell:**
```powershell
$env:AZURE_FABRIC_CAPACITY_NAME="your-existing-capacity-name"
$env:AZURE_FABRIC_WORKSPACE_NAME="Custom Workspace Name"  # Optional
```

### 2. Clone Repository and Navigate

```bash
git clone https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator.git
cd unified-data-foundation-with-fabric-solution-accelerator/infra/scripts/utils
```

### 3. Run Deployment Script

**Linux/macOS/Cloud Shell:**
```bash
chmod +x run_python_script_fabric.ps1
pwsh ./run_python_script_fabric.ps1
```

**Windows PowerShell:**
```powershell
.\run_python_script_fabric.ps1
```

> **Note**: Manual scripts do **not** create the Fabric capacity or Azure infrastructure. These must exist beforehand. For complete infrastructure deployment, use `azd up` instead.

---

## Detailed Manual Deployment Steps

### Step 1: Verify Prerequisites

1. **Check Azure CLI authentication:**
   ```bash
   az account show
   ```

2. **Verify Python installation:**
   ```bash
   python --version  # Should be 3.9 or higher
   pip --version
   ```

3. **Confirm Fabric capacity exists:**
   ```bash
   az fabric capacity list --query "[].{Name:name, State:state, Location:location}" --output table
   ```

### Step 2: Prepare Environment

1. **Install Python dependencies:**
   ```bash
   pip install requests azure-identity azure-mgmt-fabric
   ```

2. **Set required environment variables:**
   
   Replace `your-capacity-name` with your actual Fabric capacity name:
   
   **Linux/macOS/Cloud Shell:**
   ```bash
   export AZURE_FABRIC_CAPACITY_NAME="your-capacity-name"
   export AZURE_FABRIC_WORKSPACE_NAME="MAAG Data Foundation Workspace"  # Optional
   ```
   
   **Windows PowerShell:**
   ```powershell
   $env:AZURE_FABRIC_CAPACITY_NAME="your-capacity-name"
   $env:AZURE_FABRIC_WORKSPACE_NAME="MAAG Data Foundation Workspace"  # Optional
   ```

### Step 3: Execute Deployment

#### Option A: Cross-Platform Shell Script (Recommended)

**For Linux/macOS/Cloud Shell:**
```bash
cd infra/scripts/utils
chmod +x run_python_script_fabric.ps1
./run_python_script_fabric.ps1
```

#### Option B: PowerShell Script

**For Windows PowerShell:**
```powershell
cd infra\scripts\utils
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_python_script_fabric.ps1
```

### Step 4: Monitor Deployment Progress

The script will output progress information including:

- Workspace creation/validation
- Lakehouse deployment status
- Notebook upload progress
- Sample data upload status
- Power BI report deployment (if applicable)

Expected output:
```
🚀 Starting Fabric deployment...
✅ Workspace 'MAAG Data Foundation Workspace' ready
✅ Created lakehouse: maag_bronze
✅ Created lakehouse: maag_silver
✅ Created lakehouse: maag_gold
📁 Creating folder structure...
📓 Uploading notebooks... (15 notebooks)
📊 Uploading sample data... (12 files)
📋 Deploying Power BI reports... (if .pbix files found)
🎉 Deployment completed successfully!
```

---

## Script Parameters and Options

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_FABRIC_CAPACITY_NAME` | Yes | None | Name of existing Fabric capacity |
| `AZURE_FABRIC_WORKSPACE_NAME` | No | Generated | Custom workspace name |
| `AZURE_SUBSCRIPTION_ID` | No | Default | Azure subscription to use |
| `AZURE_RESOURCE_GROUP` | No | From capacity | Resource group containing capacity |

### Script Behavior

#### Workspace Creation
- If `AZURE_FABRIC_WORKSPACE_NAME` is set, creates/uses workspace with that name
- If not set, generates workspace name based on capacity and timestamp
- Verifies workspace is associated with the specified capacity

#### Data Deployment
- Uploads sample CSV files to bronze lakehouse Files section
- Creates folder structure for organized data management
- Sets up initial data for testing transformations

#### Notebook Deployment
- Uploads all transformation notebooks with proper organization
- Creates folder structure: bronze_to_silver, silver_to_gold, data_management, schema
- Configures notebook parameters and widgets

#### Power BI Integration
- Scans `reports/` directory for .pbix files
- Uploads reports to workspace reports folder
- Configures conflict resolution (Create or Overwrite)

---

## Manual Deployment Verification

### 1. Verify Workspace Access

1. **Open Microsoft Fabric:**
   - Navigate to [Microsoft Fabric](https://fabric.microsoft.com)
   - Look for your workspace in the workspace list
   - Confirm you have access to the workspace

### 2. Check Created Components

In your Fabric workspace, verify:

- **✅ Lakehouses**: `maag_bronze`, `maag_silver`, `maag_gold` exist
- **✅ Folder Structure**: Organized folders for lakehouses, notebooks, and reports
- **✅ Sample Data**: CSV files uploaded to bronze lakehouse
- **✅ Notebooks**: All transformation notebooks deployed and organized
- **✅ Power BI Reports**: Any .pbix files from the repository deployed

### 3. Test Data Pipeline

1. **Check bronze data:**
   - Open `maag_bronze` lakehouse
   - Verify sample CSV files are loaded in the Files section

2. **Run transformation pipeline:**
   - Navigate to the notebooks folder
   - Open and run `run_bronze_to_silver` notebook
   - Verify data appears in `maag_silver` lakehouse

3. **Run aggregation pipeline:**
   - Open and run `run_silver_to_gold` notebook  
   - Verify aggregated data appears in `maag_gold` lakehouse

---

## Troubleshooting Manual Deployment

### Common Issues and Solutions

| Issue | Possible Cause | Resolution |
|-------|----------------|------------|
| Script not found | Incorrect directory | Ensure you're in `infra/scripts/utils` directory |
| Permission denied | Script not executable | Run `chmod +x run_python_script_fabric.ps1` |
| Authentication error | Not logged into Azure | Run `az login` and verify authentication |
| Capacity not found | Wrong capacity name | Verify capacity name with `az fabric capacity list` |
| Workspace creation failed | Insufficient permissions | Ensure Fabric admin permissions on capacity |
| Python import errors | Missing dependencies | Install required packages with pip |
| PowerShell execution error | Execution policy | Use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |

### Environment-Specific Issues

#### Azure Cloud Shell
- **Issue**: Session timeout during deployment
- **Solution**: Cloud Shell sessions last 20 minutes. For longer operations, periodically interact with the shell
- **Issue**: Python package installation fails
- **Solution**: Use `pip install --user` for user-local installation

#### GitHub Codespaces
- **Issue**: Permission errors accessing files
- **Solution**: Ensure proper file permissions with `chmod +x` for shell scripts
- **Issue**: Azure authentication challenges
- **Solution**: Use device code authentication: `az login --use-device-code`

#### Local Environment
- **Issue**: Python not found
- **Solution**: Ensure Python 3.9+ is installed and in PATH
- **Issue**: Azure CLI command not found
- **Solution**: Install Azure CLI and ensure it's in PATH

### Script Debugging

#### Enable Verbose Output

**For Shell Script:**
```bash
pwsh -c './run_python_script_fabric.ps1 -Verbose'
```

**For PowerShell:**
```powershell
$VerbosePreference = "Continue"
.\run_python_script_fabric.ps1 -Verbose
```

#### Check Environment Variables

```bash
# Linux/macOS/Cloud Shell
echo "Capacity: $AZURE_FABRIC_CAPACITY_NAME"
echo "Workspace: $AZURE_FABRIC_WORKSPACE_NAME"

# Windows PowerShell
Write-Host "Capacity: $env:AZURE_FABRIC_CAPACITY_NAME"
Write-Host "Workspace: $env:AZURE_FABRIC_WORKSPACE_NAME"
```

#### Validate Azure Context

```bash
# Check current subscription
az account show --query "{Name:name, ID:id, TenantId:tenantId}" --output table

# List available Fabric capacities
az fabric capacity list --query "[].{Name:name, State:state, ResourceGroup:resourceGroup}" --output table
```

---

## Cleanup Manual Deployment

### Remove Workspace and Contents

**Using Azure CLI:**
```bash
# List workspaces to find workspace ID
az fabric workspace list --query "[].{Name:displayName, ID:id}" --output table

# Delete workspace (replace with actual workspace ID)
az fabric workspace delete --workspace-id "12345678-1234-1234-1234-123456789012"
```

**Using PowerShell:**
```powershell
# Remove specific workspace
$workspaceId = "12345678-1234-1234-1234-123456789012"
az fabric workspace delete --workspace-id $workspaceId
```

### Selective Cleanup

If you want to remove only specific components:

1. **Remove individual lakehouses:**
   - Navigate to the workspace in Fabric portal
   - Delete lakehouses individually: `maag_bronze`, `maag_silver`, `maag_gold`

2. **Remove notebooks:**
   - Navigate to notebooks folder
   - Delete notebook folders: `bronze_to_silver`, `silver_to_gold`, `data_management`, `schema`

3. **Remove Power BI reports:**
   - Navigate to reports folder
   - Delete individual .pbix reports

---

## Integration with CI/CD

### Azure DevOps Integration

Create a pipeline step for manual deployment:

```yaml
- task: AzureCLI@2
  displayName: 'Deploy Fabric Components'
  inputs:
    azureSubscription: '$(serviceConnectionName)'
    scriptType: 'powershell'
    scriptLocation: 'scriptPath'
    scriptPath: 'infra/scripts/utils/run_python_script_fabric.ps1'
  env:
    AZURE_FABRIC_CAPACITY_NAME: $(fabricCapacityName)
    AZURE_FABRIC_WORKSPACE_NAME: $(fabricWorkspaceName)
```

### GitHub Actions Integration

Create a workflow step for manual deployment:

```yaml
- name: Deploy Fabric Components
  run: |
    cd infra/scripts/utils
    chmod +x run_python_script_fabric.ps1
    pwsh ./run_python_script_fabric.ps1
  env:
    AZURE_FABRIC_CAPACITY_NAME: ${{ secrets.FABRIC_CAPACITY_NAME }}
    AZURE_FABRIC_WORKSPACE_NAME: ${{ vars.FABRIC_WORKSPACE_NAME }}
```

---

## Next Steps

After successful manual deployment:

1. **Test the Solution**: Run the verification steps to ensure everything works correctly
2. **Customize for Your Needs**: Modify notebooks and data for your specific requirements
3. **Set Up Monitoring**: Configure alerts and monitoring for your Fabric workspace
4. **Consider Automation**: Evaluate migrating to `azd up` for simpler deployments in the future

For more advanced deployment scenarios or to migrate to the automated azd approach, see the main [DeploymentGuideFabric.md](./DeploymentGuideFabric.md).

---

## Additional Resources

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [Fabric Workspace Management](https://learn.microsoft.com/fabric/admin/workspaces)
- [Azure CLI Fabric Extension](https://learn.microsoft.com/cli/azure/fabric)
- [Main Deployment Guide (azd)](./DeploymentGuideFabric.md)
- [Solution Architecture Overview](../architecture/README.md)

---

*This manual deployment guide is part of the Unified Data Foundation with Fabric solution accelerator. For the latest updates and documentation, visit the [official repository](https://github.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator).*