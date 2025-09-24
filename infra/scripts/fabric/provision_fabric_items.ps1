<#
.SYNOPSIS
    Deploys Microsoft Fabric items for the Unified Data Foundation with Fabric (UDFWF) solution accelerator.

.DESCRIPTION
    This PowerShell script orchestrates the complete deployment of UDFWF components to Microsoft Fabric.
    It sets up a Python virtual environment, installs dependencies, and executes the Python deployment script
    that creates the following Fabric items:
    
    • Fabric workspace (if not exists) assigned to specified capacity
    • Folder structure for organizing notebooks and data
    • Three lakehouses (Bronze, Silver, Gold) for data lakehouse architecture
    • Jupyter notebooks with sample data processing pipelines
    • Sample CSV data files uploaded to Bronze lakehouse
    • Data pipelines for Bronze→Silver and Silver→Gold transformations
    • Power BI reports (.pbix files) with dataset parameter configuration
    • Workspace administrator assignments

.PARAMETER FabricCapacityName
    The name of the Microsoft Fabric capacity to use for workspace creation and assignment.
    This capacity must exist and the user must have appropriate permissions.
    If not provided, will attempt to use AZURE_FABRIC_CAPACITY_NAME environment variable.

.PARAMETER FabricWorkspaceName
    The name of the Microsoft Fabric workspace. If the workspace doesn't exist, it will be created.
    If not provided, will use AZURE_FABRIC_WORKSPACE_NAME environment variable.
    If neither parameter nor environment variable is provided, a workspace with auto-generated name will be created.

.PARAMETER FabricAdmins
    JSON array string of administrators to add to the workspace. Can include:
    • User Principal Names (UPNs): "user@contoso.com"
    • Service Principal IDs (GUIDs): "12345678-1234-1234-1234-123456789012"
    If not provided, will use AZURE_FABRIC_ADMIN_MEMBERS environment variable.

.PARAMETER FabricAdminsByObjectId
    JSON array string of object IDs (GUIDs) to add as workspace administrators. These will be tried as both User and ServicePrincipal types.
    Format: "12345678-1234-1234-1234-123456789012"
    If not provided, will use AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID environment variable.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricWorkspaceName "UDFWF-Workspace"
    
    Creates workspace with specific name and deploys all UDFWF components.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity"
    
    Creates workspace with auto-generated name and deploys all components.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricAdmins '["user1@contoso.com", "user2@contoso.com"]'
    
    Deploys components and assigns multiple user administrators to the workspace.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricAdmins '["user@contoso.com", "12345678-1234-1234-1234-123456789012"]'
    
    Deploys components and assigns both a user and service principal as administrators.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012", "87654321-4321-4321-4321-210987654321"]'
    
    Deploys components and assigns administrators by their object IDs using fallback logic for both User and ServicePrincipal types.

.EXAMPLE
    .\provision_fabric_items.ps1 -FabricCapacityName "MyCapacity" -FabricAdmins '["user@contoso.com"]' -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012"]'
    
    Deploys components using both FabricAdmins (with Graph API resolution) and FabricAdminsByObjectId (with fallback logic).

.EXAMPLE
    $env:AZURE_FABRIC_CAPACITY_NAME = "MyCapacity"; .\provision_fabric_items.ps1
    
    Uses environment variable for capacity name with auto-generated workspace name.

.EXAMPLE
    $env:AZURE_FABRIC_CAPACITY_NAME = "MyCapacity"; $env:AZURE_FABRIC_WORKSPACE_NAME = "MyWorkspace"; .\provision_fabric_items.ps1
    
    Uses environment variables for both capacity and workspace names.

.EXAMPLE
    $env:AZURE_FABRIC_CAPACITY_NAME = "MyCapacity"; $env:AZURE_FABRIC_ADMIN_MEMBERS = '["admin@contoso.com"]'; .\provision_fabric_items.ps1
    
    Uses environment variables for capacity name and administrators.

.OUTPUTS
    The script outputs detailed progress information and creates:
    • Fabric workspace with specified or auto-generated name
    • 3 lakehouses (Bronze, Silver, Gold)
    • Folder structure for notebooks
    • Multiple Jupyter notebooks with data processing pipelines
    • Sample data files in Bronze lakehouse
    • Executed data pipelines for Bronze→Silver→Gold flow
    • Power BI reports with configured dataset parameters
    • Workspace URL and summary statistics

.NOTES
    Prerequisites:
    - Azure CLI installed and authenticated (az login)
    - PowerShell 7+ (for cross-platform compatibility)
    - Python 3.9+ with pip available in PATH
    - Appropriate permissions in the specified Fabric capacity
    - Power BI and Fabric API permissions for the authenticated user/service principal
    
    The script automatically:
    - Creates and manages a Python virtual environment (.venv in repository root) for local development
    - Installs required Python dependencies from requirements.txt (unless running in CI/CD environment)
    - Handles cross-platform execution (Windows/Linux/macOS)
    - Provides detailed error messages and troubleshooting guidance
    - Detects CI/CD environments (GitHub Actions, Azure Pipelines) and adapts behavior accordingly
    
    CI/CD Behavior:
    - When running in CI/CD environments (CI=true or GITHUB_ACTIONS=true), the script skips virtual environment
      creation and assumes Python dependencies are pre-installed by the CI/CD pipeline
    - This prevents conflicts with CI/CD Python environment management
    
    Environment Variables (optional):
    - AZURE_FABRIC_CAPACITY_NAME: Default capacity name
    - AZURE_FABRIC_WORKSPACE_NAME: Default workspace name  
    - AZURE_FABRIC_ADMIN_MEMBERS: Default administrators JSON array
    - AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID: Default administrators by object ID JSON array
#>

param(
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric capacity name (optional, will use AZURE_FABRIC_CAPACITY_NAME env var if not provided)")]
    [string]$FabricCapacityName,
    
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric workspace name (optional)")]
    [string]$FabricWorkspaceName,
    
    [Parameter(Mandatory = $false, HelpMessage = 'JSON array of administrators to add to the workspace (e.g., ''["user1@contoso.com", "12345678-1234-1234-1234-123456789012"]'')')]
    [string]$FabricAdmins,
    
    [Parameter(Mandatory = $false, HelpMessage = 'JSON array of object IDs (GUIDs) to add as workspace administrators (e.g., ''["12345678-1234-1234-1234-123456789012", "87654321-4321-4321-4321-210987654321"]'')')]
    [string]$FabricAdminsByObjectId
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Check if FabricCapacityName is provided, otherwise use environment variable
if ([string]::IsNullOrWhiteSpace($FabricCapacityName)) {
    $FabricCapacityName = $env:AZURE_FABRIC_CAPACITY_NAME
    if ([string]::IsNullOrWhiteSpace($FabricCapacityName)) {
        Write-Host "❌ Error: Fabric capacity name is required" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please provide the capacity name either:" -ForegroundColor Yellow
        Write-Host "1. As a parameter: -FabricCapacityName 'MyCapacity'" -ForegroundColor White
        Write-Host "2. Set the AZURE_FABRIC_CAPACITY_NAME environment variable" -ForegroundColor White
        exit 1
    }
    else {
        Write-Host "Using Fabric capacity name from environment variable: $FabricCapacityName" -ForegroundColor Cyan
    }
}

# Check if FabricWorkspaceName is provided, otherwise use environment variable
if ([string]::IsNullOrWhiteSpace($FabricWorkspaceName)) {
    $FabricWorkspaceName = $env:AZURE_FABRIC_WORKSPACE_NAME
    if (-not [string]::IsNullOrWhiteSpace($FabricWorkspaceName)) {
        Write-Host "Using Fabric workspace name from environment variable: $FabricWorkspaceName" -ForegroundColor Cyan
    }
}

# Check if FabricAdmins is provided, otherwise use environment variable
if ([string]::IsNullOrWhiteSpace($FabricAdmins)) {
    $FabricAdmins = $env:AZURE_FABRIC_ADMIN_MEMBERS
    if (-not [string]::IsNullOrWhiteSpace($FabricAdmins)) {
        Write-Host "Using Fabric admins from environment variable" -ForegroundColor Cyan
    }
}

# Check if FabricAdminsByObjectId is provided, otherwise use environment variable
if ([string]::IsNullOrWhiteSpace($FabricAdminsByObjectId)) {
    $FabricAdminsByObjectId = $env:AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID
    if (-not [string]::IsNullOrWhiteSpace($FabricAdminsByObjectId)) {
        Write-Host "Using Fabric admins by object ID from environment variable" -ForegroundColor Cyan
    }
}

Write-Host "Starting Microsoft Fabric deployment script..." -ForegroundColor Green
Write-Host "Fabric Capacity Name: $FabricCapacityName" -ForegroundColor Cyan

if ($FabricWorkspaceName) {
    Write-Host "Fabric Workspace Name: $FabricWorkspaceName" -ForegroundColor Cyan
    Write-Host "Mode: Create/use workspace with specified name" -ForegroundColor Yellow
}
else {
    Write-Host "Mode: Create workspace with auto-generated name" -ForegroundColor Yellow
}

if ($FabricAdmins) {
    Write-Host "Fabric Admins: $FabricAdmins" -ForegroundColor Cyan
}
else {
    Write-Host "Fabric Admins: None specified" -ForegroundColor Yellow
}

if ($FabricAdminsByObjectId) {
    Write-Host "Fabric Admins by Object ID: $FabricAdminsByObjectId" -ForegroundColor Cyan
}
else {
    Write-Host "Fabric Admins by Object ID: None specified" -ForegroundColor Yellow
}

try {
    # Get script directory and calculate repository root directory
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))  # Go up 3 levels from infra/scripts/fabric to repo root
    $RequirementsPath = Join-Path $ScriptDir "requirements.txt"
    
    Write-Host "Script directory: $ScriptDir" -ForegroundColor Yellow

    Write-Host "Repository root: $RepoRoot" -ForegroundColor Yellow

    # Validate that Python is available
    Write-Host "Checking Python installation..." -ForegroundColor Yellow
    
    # Try python3 first, then python
    $pythonCmd = $null
    try {
        $null = python3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "python3"
        }
    }
    catch { }
    
    if (-not $pythonCmd) {
        try {
            $null = python --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = "python"
            }
        }
        catch { }
    }
    
    if (-not $pythonCmd) {
        throw "Python is not installed or not available in PATH. Please install Python 3.9+ and try again."
    }
    
    Write-Host "Python found: $pythonCmd" -ForegroundColor Green

    # Check if we're running in a CI environment (GitHub Actions, Azure DevOps, etc.)
    $isCI = $env:CI -eq "true" -or $env:GITHUB_ACTIONS -eq "true" -or $env:AZURE_PIPELINES -eq "true"
    
    if ($isCI) {
        Write-Host "Running in CI environment - using system Python instead of virtual environment..." -ForegroundColor Cyan
        $venvPython = $pythonCmd
        
        # Upgrade pip in CI environment
        Write-Host "Upgrading pip..." -ForegroundColor Yellow
        & $pythonCmd -m pip install --upgrade pip --quiet
    }
    else {
        # Create and activate Python virtual environment (local development)
        Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow
        $VenvPath = Join-Path $RepoRoot ".venv"
        
        if (-not (Test-Path $VenvPath)) {
            Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
            & $pythonCmd -m venv "$VenvPath"
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create Python virtual environment."
            }
        }
        
        # Activate virtual environment
        $ActivateScript = if ($IsWindows -or $env:OS -eq "Windows_NT") {
            Join-Path $VenvPath "Scripts\Activate.ps1"
        }
        else {
            Join-Path $VenvPath "bin\activate.ps1"
        }
        
        if (Test-Path $ActivateScript) {
            & $ActivateScript
        }
        else {
            throw "Virtual environment activation script at '$ActivateScript' not found."
        }

        # Upgrade pip
        Write-Host "Upgrading pip..." -ForegroundColor Yellow
        
        # Get Python executable from virtual environment
        $venvPython = if ($IsWindows -or $env:OS -eq "Windows_NT") {
            Join-Path $VenvPath "Scripts\python.exe"
        }
        else {
            Join-Path $VenvPath "bin\python3"
        }
        
        # Upgrade pip
        & $venvPython -m pip install --upgrade pip --quiet
    }

    # Install dependencies from requirements.txt (only if not in CI where deps are pre-installed)
    if (-not $isCI) {
        Write-Host "Installing requirements..." -ForegroundColor Yellow
        
        # Install requirements
        if (-not (Test-Path $RequirementsPath)) {
            throw "requirements.txt not found at: $RequirementsPath"
        }
        
        & $venvPython -m pip install -r "$RequirementsPath" --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install Python dependencies."
        }
    }
    else {
        Write-Host "Running in CI environment - assuming dependencies are already installed..." -ForegroundColor Cyan
    }

    # Change to script directory for Python execution
    Push-Location $ScriptDir

    # Run the Python deployment script
    Write-Host "Starting Fabric items deployment..." -ForegroundColor Yellow
    
    # Build command arguments
    $pythonArgs = @("--capacityName", $FabricCapacityName)
    if ($FabricWorkspaceName) {
        $pythonArgs += "--workspaceName", $FabricWorkspaceName
    }
    
    # Handle fabric admins JSON array
    if ($FabricAdmins) {
        try {
            $adminsArray = $FabricAdmins | ConvertFrom-Json
            if ($adminsArray -and $adminsArray.Count -gt 0) {
                $pythonArgs += "--fabricAdmins"
                $pythonArgs += $adminsArray
            }
        }
        catch {
            Write-Host "Warning: Failed to parse fabric admins JSON array, proceeding without..." -ForegroundColor Yellow
        }
    }
    
    # Handle fabric admins by object ID JSON array
    if ($FabricAdminsByObjectId) {
        try {
            $adminsByObjectIdArray = $FabricAdminsByObjectId | ConvertFrom-Json
            if ($adminsByObjectIdArray -and $adminsByObjectIdArray.Count -gt 0) {
                $pythonArgs += "--fabricAdminsByObjectId"
                $pythonArgs += $adminsByObjectIdArray
            }
        }
        catch {
            Write-Host "Warning: Failed to parse fabric admins by object ID JSON array, proceeding without..." -ForegroundColor Yellow
        }
    }
    
    # Run Python script
    & $venvPython -u create_fabric_items.py @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Fabric deployment completed successfully!" -ForegroundColor Green
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
    exit 1
}
finally {
    # Cleanup
    if ($env:VIRTUAL_ENV -and (Get-Command deactivate -ErrorAction SilentlyContinue)) {
        deactivate
    }
    
    if (Get-Location -Stack -ErrorAction SilentlyContinue) {
        Pop-Location
    }
}
