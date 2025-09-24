<#
.SYNOPSIS
    Deploys Microsoft Fabric items for the Unified Data Foundation with Fabric (UDFWF) solution accelerator.

.DESCRIPTION
    Orchestrates complete deployment of UDFWF components to Microsoft Fabric including:
    • Fabric workspace with lakehouse architecture (Bronze/Silver/Gold)
    • Jupyter notebooks with data processing pipelines
    • Sample data and Power BI reports
    • Workspace administrator assignments

.PARAMETER FabricCapacityName
    Microsoft Fabric capacity name (required). Uses AZURE_FABRIC_CAPACITY_NAME env var if not provided.

.PARAMETER FabricWorkspaceName
    Fabric workspace name (optional). Uses AZURE_FABRIC_WORKSPACE_NAME env var or auto-generates if not provided.

.PARAMETER FabricAdmins
    JSON array of administrators: ["user@contoso.com", "guid-for-service-principal"]
    Uses AZURE_FABRIC_ADMIN_MEMBERS env var if not provided.

.PARAMETER FabricAdminsByObjectId
    JSON array of object IDs for workspace administrators with fallback logic for User/ServicePrincipal types.
    Uses AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID env var if not provided.

.PARAMETER SkipPythonVirtualEnvironment
    Use system Python directly instead of creating virtual environment.

.PARAMETER SkipPythonDependencies
    Skip installing Python dependencies (assume pre-installed).

.PARAMETER SkipPipUpgrade
    Skip upgrading pip to latest version.

.EXAMPLE
    .\run_python_script_fabric.ps1 -FabricCapacityName "MyCapacity" -FabricWorkspaceName "UDFWF-Workspace"
    
.EXAMPLE
    .\run_python_script_fabric.ps1 -FabricCapacityName "MyCapacity" -SkipPythonVirtualEnvironment -SkipPythonDependencies

.NOTES
    Prerequisites: Azure CLI (logged in), PowerShell 7+, Python 3.9+, appropriate Fabric capacity permissions
    
    Environment Variables (optional):
    - AZURE_FABRIC_CAPACITY_NAME: Default capacity name
    - AZURE_FABRIC_WORKSPACE_NAME: Default workspace name  
    - AZURE_FABRIC_ADMIN_MEMBERS: Default administrators JSON array
    - AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID: Default administrators by object ID
#>

param(
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric capacity name (optional, will use AZURE_FABRIC_CAPACITY_NAME env var if not provided)")]
    [string]$FabricCapacityName,
    
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric workspace name (optional)")]
    [string]$FabricWorkspaceName,
    
    [Parameter(Mandatory = $false, HelpMessage = 'JSON array of administrators to add to the workspace (e.g., ''["user1@contoso.com", "12345678-1234-1234-1234-123456789012"]'')')]
    [string]$FabricAdmins,
    
    [Parameter(Mandatory = $false, HelpMessage = 'JSON array of object IDs (GUIDs) to add as workspace administrators (e.g., ''["12345678-1234-1234-1234-123456789012", "87654321-4321-4321-4321-210987654321"]'')')]
    [string]$FabricAdminsByObjectId,
    
    [Parameter(Mandatory = $false, HelpMessage = "Skip creating and using Python virtual environment (use system Python directly)")]
    [switch]$SkipPythonVirtualEnvironment,
    
    [Parameter(Mandatory = $false, HelpMessage = "Skip installing Python dependencies from requirements.txt (assume dependencies are already installed)")]
    [switch]$SkipPythonDependencies,
    
    [Parameter(Mandatory = $false, HelpMessage = "Skip upgrading pip to the latest version")]
    [switch]$SkipPipUpgrade
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Helper function to get parameter value with environment variable fallback
function Get-ParameterValue {
    param([string]$ParameterValue, [string]$EnvVarName, [string]$Description)
    
    if ([string]::IsNullOrWhiteSpace($ParameterValue)) {
        $envValue = [Environment]::GetEnvironmentVariable($EnvVarName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            Write-Host "Using $Description from environment variable" -ForegroundColor Cyan
            return $envValue
        }
    }
    return $ParameterValue
}

# Helper function for colored output
function Write-Info { param([string]$Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param([string]$Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host $Message -ForegroundColor Red }

# Helper function to find Python executable
function Get-PythonCommand {
    $pythonCommands = @("python3", "python")
    foreach ($cmd in $pythonCommands) {
        try {
            $null = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0) { return $cmd }
        } catch { }
    }
    throw "Python is not installed or not available in PATH. Please install Python 3.9+ and try again."
}

# Helper function to setup Python environment
function Initialize-PythonEnvironment {
    param(
        [string]$RepoRoot,
        [bool]$SkipVirtualEnv,
        [bool]$SkipDependencies,
        [bool]$SkipPipUpgrade,
        [string]$RequirementsPath
    )
    
    $pythonCmd = Get-PythonCommand
    Write-Success "Python found: $pythonCmd"
    
    if ($SkipVirtualEnv) {
        Write-Info "Skipping Python virtual environment - using system Python"
        $pythonExec = $pythonCmd
    } else {
        Write-Warning "Setting up Python virtual environment..."
        $venvPath = Join-Path $RepoRoot ".venv"
        
        if (-not (Test-Path $venvPath)) {
            & $pythonCmd -m venv "$venvPath"
            if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
        }
        
        # Activate virtual environment
        $activateScript = if ($IsWindows -or $env:OS -eq "Windows_NT") {
            Join-Path $venvPath "Scripts\Activate.ps1"
        } else {
            Join-Path $venvPath "bin\activate.ps1"
        }
        
        if (Test-Path $activateScript) { & $activateScript } 
        else { throw "Virtual environment activation script not found at '$activateScript'." }
        
        $pythonExec = if ($IsWindows -or $env:OS -eq "Windows_NT") {
            Join-Path $venvPath "Scripts\python.exe"
        } else {
            Join-Path $venvPath "bin\python3"
        }
    }
    
    # Upgrade pip if not skipped
    if (-not $SkipPipUpgrade) {
        Write-Warning "Upgrading pip..."
        & $pythonExec -m pip install --upgrade pip --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Warning: Failed to upgrade pip, continuing with existing version..."
        }
    } else {
        Write-Info "Skipping pip upgrade"
    }
    
    # Install dependencies if not skipped
    if (-not $SkipDependencies) {
        Write-Warning "Installing requirements..."
        if (-not (Test-Path $RequirementsPath)) {
            throw "requirements.txt not found at: $RequirementsPath"
        }
        & $pythonExec -m pip install -r "$RequirementsPath" --quiet
        if ($LASTEXITCODE -ne 0) { throw "Failed to install Python dependencies." }
    } else {
        Write-Info "Skipping Python dependencies installation"
    }
    
    return $pythonExec
}

# Resolve parameters with environment variable fallbacks
$FabricCapacityName = Get-ParameterValue $FabricCapacityName "AZURE_FABRIC_CAPACITY_NAME" "Fabric capacity name"
$FabricWorkspaceName = Get-ParameterValue $FabricWorkspaceName "AZURE_FABRIC_WORKSPACE_NAME" "Fabric workspace name"
$FabricAdmins = Get-ParameterValue $FabricAdmins "AZURE_FABRIC_ADMIN_MEMBERS" "Fabric admins"
$FabricAdminsByObjectId = Get-ParameterValue $FabricAdminsByObjectId "AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID" "Fabric admins by object ID"

# Validate required parameters
if ([string]::IsNullOrWhiteSpace($FabricCapacityName)) {
    Write-Error "❌ Error: Fabric capacity name is required"
    Write-Host ""
    Write-Warning "Please provide the capacity name either:"
    Write-Host "1. As a parameter: -FabricCapacityName 'MyCapacity'" -ForegroundColor White
    Write-Host "2. Set the AZURE_FABRIC_CAPACITY_NAME environment variable" -ForegroundColor White
    exit 1
}

# Display configuration
Write-Success "Starting Microsoft Fabric deployment script..."
Write-Info "Fabric Capacity: $FabricCapacityName"

$mode = if ($FabricWorkspaceName) { "Create/use workspace: $FabricWorkspaceName" } else { "Create workspace with auto-generated name" }
Write-Warning $mode

$adminInfo = @(
    if ($FabricAdmins) { "Fabric Admins: $FabricAdmins" }
    if ($FabricAdminsByObjectId) { "Fabric Admins by Object ID: $FabricAdminsByObjectId" }
) | Where-Object { $_ }

if ($adminInfo) {
    $adminInfo | ForEach-Object { Write-Info $_ }
} else {
    Write-Warning "No administrators specified"
}

try {
    # Calculate paths - script is now in utils, but fabric scripts are in ../fabric
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $FabricScriptsDir = Join-Path (Split-Path -Parent $ScriptDir) "fabric"
    $RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
    $RequirementsPath = Join-Path $FabricScriptsDir "requirements.txt"
    
    # Initialize Python environment
    $pythonExec = Initialize-PythonEnvironment -RepoRoot $RepoRoot -SkipVirtualEnv:$SkipPythonVirtualEnvironment -SkipDependencies:$SkipPythonDependencies -SkipPipUpgrade:$SkipPipUpgrade -RequirementsPath $RequirementsPath

    # Execute Python deployment script - change to fabric scripts directory
    Push-Location $FabricScriptsDir
    Write-Warning "Starting Fabric items deployment..."
    
    # Build command arguments
    $pythonArgs = @("--capacityName", $FabricCapacityName)
    if ($FabricWorkspaceName) { $pythonArgs += "--workspaceName", $FabricWorkspaceName }
    
    # Handle JSON array parameters
    @(
        @{Param = $FabricAdmins; ArgName = "--fabricAdmins"; ErrorMsg = "fabric admins"},
        @{Param = $FabricAdminsByObjectId; ArgName = "--fabricAdminsByObjectId"; ErrorMsg = "fabric admins by object ID"}
    ) | ForEach-Object {
        if ($_.Param) {
            try {
                $array = $_.Param | ConvertFrom-Json
                if ($array -and $array.Count -gt 0) {
                    $pythonArgs += $_.ArgName
                    $pythonArgs += $array
                }
            } catch {
                Write-Warning "Warning: Failed to parse $($_.ErrorMsg) JSON array, proceeding without..."
            }
        }
    }
    
    # Execute Python script
    & $pythonExec -u create_fabric_items.py @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Fabric deployment completed successfully!"
    } else {
        throw "Python script execution failed with exit code: $LASTEXITCODE"
    }
} catch {
    Write-Error "❌ Deployment failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Warning "Troubleshooting tips:"
    @(
        "1. Ensure you are logged in to Azure CLI: az login",
        "2. Verify you have permissions in the Fabric capacity and workspace", 
        "3. Check that the capacity name is correct and accessible"
    ) | ForEach-Object { Write-Host $_ -ForegroundColor White }
    exit 1
} finally {
    # Cleanup
    if ($env:VIRTUAL_ENV -and (Get-Command deactivate -ErrorAction SilentlyContinue)) {
        deactivate
    }
    if (Get-Location -Stack -ErrorAction SilentlyContinue) {
        Pop-Location
    }
}
