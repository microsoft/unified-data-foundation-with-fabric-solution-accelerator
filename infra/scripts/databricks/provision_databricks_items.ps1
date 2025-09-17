<#
.SYNOPSIS
    Deploys Databricks items (notebooks, data, catalog) to a Databricks workspace.

.DESCRIPTION
    This script automates the deployment of MAAG solution components to Databricks.

.PARAMETER WorkspaceUrl
    The Databricks workspace URL (e.g. https://adb-xxxx.azuredatabricks.net).

.PARAMETER Token
    The Databricks personal access token (starts with dapi...).

.PARAMETER SolutionName
    The solution name (e.g. maag).

.PARAMETER CatalogName
    The Unity Catalog name (e.g. maagcatalog).

.PARAMETER SchemaName
    The schema name (e.g. sales).

.PARAMETER ClusterId
    The Databricks cluster ID

.PARAMETER CatalogManagedLocation
    The external location name or URI for the catalog managed storage

.EXAMPLE
    .\provision_databricks_items.ps1 `
        -WorkspaceUrl "https://adb-xxxx.azuredatabricks.net" `
        -Token "dapi..." `
        -SolutionName "maag" `
        -CatalogName "maagcatalog" `
        -SchemaName "sales" `
        -ClusterId "xxxx-xxxxxx-abcdxab" `
        -CatalogManagedLocation "abfss://container@storageaccount.dfs.core.windows.net/maag"

.NOTES
    Prerequisites:
    - Python 3.8+ with pip
    - Appropriate permissions in Databricks
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidatePattern("https://.*")]
    [string]$WorkspaceUrl,

    [Parameter(Mandatory = $false)]
    [ValidatePattern("^dapi.*")]
    [string]$Token,

    [Parameter(Mandatory = $false)]
    [string]$SolutionName,

    [Parameter(Mandatory = $false)]
    [string]$CatalogName,

    [Parameter(Mandatory = $false)]
    [string]$SchemaName,

    [Parameter(Mandatory = $false)]
    [string]$ClusterId,

    [Parameter(Mandatory = $false)]
    [string]$CatalogManagedLocation
)

$ErrorActionPreference = "Stop"

function Prompt-IfMissing {
    param(
        [string]$Value,
        [string]$Message
    )
    if (-not $Value -or $Value -eq "") {
        # Only prompt if running in an interactive host
        if ($Host.UI.RawUI.KeyAvailable -or $env:CI -eq $null) {
            Write-Host -NoNewline "$($Message): " -ForegroundColor Yellow
            $Value = Read-Host
        }
        else {
            throw "Missing required parameter: $Message"
        }
    }
    return $Value
}

# Prompt if running interactively
$WorkspaceUrl = Prompt-IfMissing $WorkspaceUrl "Enter Databricks Workspace URL (e.g. https://adb-xxxx.azuredatabricks.net)"
$Token = Prompt-IfMissing $Token "Enter Databricks Token"
$SolutionName = Prompt-IfMissing $SolutionName "Enter Solution Name (e.g. maag)"
$CatalogName = Prompt-IfMissing $CatalogName "Enter Catalog Name (e.g. maagcatalog)"
$SchemaName = Prompt-IfMissing $SchemaName "Enter Schema Name (e.g. sales)"
$ClusterId = Prompt-IfMissing $ClusterId "Enter Cluster ID"
$CatalogManagedLocation = Prompt-IfMissing $CatalogManagedLocation "Enter Catalog Managed Location (external location name or URI)"

Write-Host "`n[INFO] Starting Databricks deployment..." -ForegroundColor Green
Write-Host "Workspace: $WorkspaceUrl" -ForegroundColor Cyan
Write-Host "Solution: $SolutionName, Catalog: $CatalogName, Schema: $SchemaName" -ForegroundColor Cyan

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
python --version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    python3 --version > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python is not installed. Please install Python 3.8+ and try again."
    }
}

# Check pip
Write-Host "Checking pip installation..." -ForegroundColor Yellow
pip --version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "pip is not installed. Please install pip and try again."
}


# Use requirements.txt in infra/scripts/databricks
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$requirements = Join-Path $scriptDir 'requirements.txt'
if (-not (Test-Path $requirements)) {
    throw "Could not find requirements.txt at $requirements. Please check your repository structure."
}
Write-Host "Installing Python dependencies from $requirements..." -ForegroundColor Yellow
pip install -r "$requirements" --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Python dependencies. Please check requirements.txt and try again."
}


# Run the deployment script
Write-Host "Starting Databricks items deployment..." -ForegroundColor Yellow
Write-Host "This may take several minutes to complete..." -ForegroundColor Cyan

python -u create_databricks_items_maag.py `
    --workspaceUrl "$WorkspaceUrl" `
    --token "$Token" `
    --solutionname "$SolutionName" `
    --catalogname "$CatalogName" `
    --schemaname "$SchemaName" `
    --cluster-id "$ClusterId" `
    --catalog-managed-location "$CatalogManagedLocation"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Databricks deployment completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Open your Databricks workspace" -ForegroundColor White
    Write-Host "2. Verify that notebooks and sample data have been uploaded" -ForegroundColor White
    Write-Host "3. Check that Unity Catalog and schema are created as expected" -ForegroundColor White
    Write-Host "4. Explore the uploaded notebooks and data" -ForegroundColor White
}
else {
    throw "Python script execution failed with exit code: $LASTEXITCODE"
}
