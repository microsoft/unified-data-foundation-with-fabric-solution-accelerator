<#
.SYNOPSIS
    Deploys Microsoft Fabric items (lakehouses, notebooks, folders) to a Fabric workspace.

.DESCRIPTION
    This script automates the deployment of UDFF (Unified Data Foundation with Fabric) components 
    to Microsoft Fabric including folder structure, lakehouses, sample data, notebooks, and Power BI reports.

.PARAMETER FabricCapacityName
    The name of the Microsoft Fabric capacity to use for workspace creation.

.PARAMETER FabricWorkspaceName
    The name of the Microsoft Fabric workspace. If the workspace doesn't exist, it will be created.
    If not provided, a workspace with auto-generated name will be created.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricWorkspaceName "UDFF-Workspace"

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity"

.NOTES
    Prerequisites:
    - Azure CLI installed and authenticated (az login)
    - Python 3.9+ with pip
    - Appropriate permissions in the Fabric capacity and workspace
#>

param(
    [Parameter(Mandatory = $true, HelpMessage = "Enter the Fabric capacity name")]
    [ValidateNotNullOrEmpty()]
    [string]$FabricCapacityName,
    
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric workspace name (optional)")]
    [string]$FabricWorkspaceName
)

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "Starting Microsoft Fabric deployment script..." -ForegroundColor Green
Write-Host "Fabric Capacity Name: $FabricCapacityName" -ForegroundColor Cyan

if ($FabricWorkspaceName) {
    Write-Host "Fabric Workspace Name: $FabricWorkspaceName" -ForegroundColor Cyan
    Write-Host "Mode: Create/use workspace with specified name" -ForegroundColor Yellow
}
else {
    Write-Host "Mode: Create workspace with auto-generated name" -ForegroundColor Yellow
}

try {
    # Validate that Python is available
    Write-Host "Checking Python installation..." -ForegroundColor Yellow
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python is not installed or not available in PATH. Please install Python 3.9+ and try again."
    }
    Write-Host "Found: $pythonVersion" -ForegroundColor Green

    # Validate that pip is available
    Write-Host "Checking pip installation..." -ForegroundColor Yellow
    pip --version > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip is not available. Please ensure pip is installed and try again."
    }
    Write-Host "pip is available" -ForegroundColor Green

    # Install Python dependencies
    Write-Host "Installing Python dependencies from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Python dependencies. Please check requirements.txt and try again."
    }
    Write-Host "Dependencies installed successfully" -ForegroundColor Green

    # Run the Python deployment script
    Write-Host "Starting Fabric items deployment..." -ForegroundColor Yellow
    Write-Host "This may take several minutes to complete..." -ForegroundColor Cyan
    
    # Build command arguments
    $pythonArgs = @("--capacityName", $FabricCapacityName)
    if ($FabricWorkspaceName) {
        $pythonArgs += "--workspaceName", $FabricWorkspaceName
    }
    
    # Run Python unbuffered so prints show immediately
    python -u create_fabric_items.py @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Fabric deployment completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Open your Microsoft Fabric workspace" -ForegroundColor White
        Write-Host "2. Verify that lakehouses (maag_bronze, maag_silver, maag_gold) have been created" -ForegroundColor White
        Write-Host "3. Check that notebooks are organized in the correct folder structure" -ForegroundColor White
        Write-Host "4. Explore the sample data in the bronze lakehouse" -ForegroundColor White
        Write-Host "5. Review any deployed Power BI reports in the reports folder" -ForegroundColor White
        Write-Host "6. Note the workspace ID for future deployments" -ForegroundColor White
    }
    else {
        throw "Python script execution failed with exit code: $LASTEXITCODE"
    }
}
catch {
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "1. Ensure you are logged in to Azure CLI: az login" -ForegroundColor White
    Write-Host "2. Verify you have permissions in the Fabric capacity and workspace" -ForegroundColor White
    Write-Host "3. Check that the capacity name is correct and accessible" -ForegroundColor White
    Write-Host "4. Ensure Python 3.9+ and pip are properly installed" -ForegroundColor White
    Write-Host "5. Check your internet connection and Fabric API access" -ForegroundColor White
    exit 1
}
