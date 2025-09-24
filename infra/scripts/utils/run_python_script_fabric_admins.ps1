<#
.SYNOPSIS
    Adds administrators to all available Microsoft Fabric workspaces.

.DESCRIPTION
    Adds specified administrators to all Microsoft Fabric workspaces that the current user has access to.
    Supports both user principal names (UPNs) and service principal object IDs.

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
    .\run_python_script_fabric_admins.ps1 -FabricAdmins '["user@contoso.com", "admin@company.com"]'
    
.EXAMPLE
    .\run_python_script_fabric_admins.ps1 -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012"]'

.EXAMPLE
    .\run_python_script_fabric_admins.ps1 -FabricAdmins '["user@contoso.com"]' -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012"]'

.NOTES
    Prerequisites: Azure CLI (logged in), PowerShell 7+, Python 3.9+, appropriate Fabric workspace permissions
    
    Environment Variables (optional):
    - AZURE_FABRIC_ADMIN_MEMBERS: Default administrators JSON array
    - AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID: Default administrators by object ID
#>

param(
    [Parameter(Mandatory = $false, HelpMessage = 'JSON array of administrators to add to all workspaces (e.g., ''["user1@contoso.com", "12345678-1234-1234-1234-123456789012"]'')')]
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
$FabricAdmins = Get-ParameterValue $FabricAdmins "AZURE_FABRIC_ADMIN_MEMBERS" "Fabric admins"
$FabricAdminsByObjectId = Get-ParameterValue $FabricAdminsByObjectId "AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID" "Fabric admins by object ID"

# Validate that at least one admin parameter is provided
if ([string]::IsNullOrWhiteSpace($FabricAdmins) -and [string]::IsNullOrWhiteSpace($FabricAdminsByObjectId)) {
    Write-Error "❌ Error: At least one of FabricAdmins or FabricAdminsByObjectId is required"
    Write-Host ""
    Write-Warning "Please provide administrators either:"
    Write-Host "1. As parameters: -FabricAdmins '[\"user@contoso.com\"]'" -ForegroundColor White
    Write-Host "2. As parameters: -FabricAdminsByObjectId '[\"12345678-1234-1234-1234-123456789012\"]'" -ForegroundColor White
    Write-Host "3. Set the AZURE_FABRIC_ADMIN_MEMBERS or AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID environment variables" -ForegroundColor White
    exit 1
}

# Display configuration
Write-Success "Starting Microsoft Fabric workspace administrators management..."

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

    # Execute Python script - change to fabric scripts directory
    Push-Location $FabricScriptsDir
    Write-Warning "Starting workspace administrators management..."
    
    # Build command arguments
    $pythonArgs = @()
    
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
    & $pythonExec -u add_fabric_workspace_admins.py @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Fabric workspace administrators management completed successfully!"
    } else {
        throw "Python script execution failed with exit code: $LASTEXITCODE"
    }
} catch {
    Write-Error "❌ Workspace administrators management failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Warning "Troubleshooting tips:"
    @(
        "1. Ensure you are logged in to Azure CLI: az login",
        "2. Verify you have Admin permissions on the workspaces you want to modify", 
        "3. Check that the administrator identifiers are correct and accessible"
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
