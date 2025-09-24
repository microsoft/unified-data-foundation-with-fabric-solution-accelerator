<#
.SYNOPSIS
    Removes Microsoft Fabric workspace for the Unified Data Foundation with Fabric (UDFWF) solution accelerator.

.DESCRIPTION
    Orchestrates the removal of UDFWF workspace from Microsoft Fabric including:
    • Workspace lookup and verification
    • Safe deletion with confirmation prompts
    • Comprehensive error handling and user guidance

.PARAMETER FabricWorkspaceName
    Fabric workspace name to delete (optional). Uses AZURE_FABRIC_WORKSPACE_NAME env var if not provided.

.PARAMETER FabricWorkspaceId
    Fabric workspace ID (GUID) to delete (optional). Uses AZURE_FABRIC_WORKSPACE_ID env var if not provided.

.PARAMETER SkipPythonVirtualEnvironment
    Use system Python directly instead of creating virtual environment.

.PARAMETER SkipPythonDependencies
    Skip installing Python dependencies (assume pre-installed).

.PARAMETER SkipPipUpgrade
    Skip upgrading pip to latest version.

.EXAMPLE
    .\remove_python_script_fabric.ps1 -FabricWorkspaceName "UDFWF-Workspace"
    
.EXAMPLE
    .\remove_python_script_fabric.ps1 -FabricWorkspaceId "12345678-1234-1234-1234-123456789012"

.EXAMPLE
    .\remove_python_script_fabric.ps1 -FabricWorkspaceName "MyWorkspace" -SkipPythonVirtualEnvironment -SkipPythonDependencies

.NOTES
    Prerequisites: Azure CLI (logged in), PowerShell 7+, Python 3.9+, appropriate Fabric workspace permissions
    
    Environment Variables (optional):
    - AZURE_FABRIC_WORKSPACE_NAME: Default workspace name
    - AZURE_FABRIC_WORKSPACE_ID: Default workspace ID  
#>

param(
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric workspace name to delete (optional, will use AZURE_FABRIC_WORKSPACE_NAME env var if not provided)")]
    [string]$FabricWorkspaceName,
    
    [Parameter(Mandatory = $false, HelpMessage = "Enter the Fabric workspace ID (GUID) to delete (optional, will use AZURE_FABRIC_WORKSPACE_ID env var if not provided)")]
    [string]$FabricWorkspaceId,
    
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
            Write-Host "Using $Description from environment variable: $envValue" -ForegroundColor Green
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
            & $cmd --version *>$null
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
        Write-Info "Creating Python virtual environment..."
        $venvPath = Join-Path $RepoRoot ".venv"
        
        if (Test-Path $venvPath) {
            Write-Info "Virtual environment already exists, using existing one"
        } else {
            & $pythonCmd -m venv $venvPath
            if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
        }
        
        # Activate virtual environment
        if ($IsWindows -or ($null -eq $IsWindows)) {
            $pythonExec = Join-Path $venvPath "Scripts" "python.exe"
            $activateScript = Join-Path $venvPath "Scripts" "Activate.ps1"
            if (Test-Path $activateScript) { & $activateScript }
        } else {
            $pythonExec = Join-Path $venvPath "bin" "python"
            $env:PATH = "$(Join-Path $venvPath 'bin'):$env:PATH"
        }
        Write-Success "Virtual environment activated: $venvPath"
    }
    
    # Upgrade pip if not skipped
    if (-not $SkipPipUpgrade) {
        Write-Info "Upgrading pip..."
        & $pythonExec -m pip install --upgrade pip *>$null
    } else {
        Write-Info "Skipping pip upgrade"
    }
    
    # Install dependencies if not skipped
    if (-not $SkipDependencies) {
        Write-Info "Installing Python dependencies from $RequirementsPath..."
        if (-not (Test-Path $RequirementsPath)) {
            throw "Requirements file not found: $RequirementsPath"
        }
        & $pythonExec -m pip install -r $RequirementsPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to install Python dependencies." }
    } else {
        Write-Info "Skipping Python dependencies installation"
    }
    
    return $pythonExec
}

# Resolve parameters with environment variable fallbacks
$FabricWorkspaceName = Get-ParameterValue $FabricWorkspaceName "AZURE_FABRIC_WORKSPACE_NAME" "Fabric workspace name"
$FabricWorkspaceId = Get-ParameterValue $FabricWorkspaceId "AZURE_FABRIC_WORKSPACE_ID" "Fabric workspace ID"

# Validate parameters
if ([string]::IsNullOrWhiteSpace($FabricWorkspaceName) -and [string]::IsNullOrWhiteSpace($FabricWorkspaceId)) {
    Write-Error "❌ Error: Either workspace name or workspace ID is required"
    Write-Host ""
    Write-Warning "Please provide either:"
    Write-Host "1. Workspace name: -FabricWorkspaceName 'MyWorkspace'" -ForegroundColor White
    Write-Host "2. Workspace ID: -FabricWorkspaceId '12345678-1234-1234-1234-123456789012'" -ForegroundColor White
    Write-Host "3. Set the AZURE_FABRIC_WORKSPACE_NAME or AZURE_FABRIC_WORKSPACE_ID environment variable" -ForegroundColor White
    exit 1
}

if (-not [string]::IsNullOrWhiteSpace($FabricWorkspaceName) -and -not [string]::IsNullOrWhiteSpace($FabricWorkspaceId)) {
    Write-Error "❌ Error: Please specify either workspace name or workspace ID, not both"
    exit 1
}

# Display configuration
Write-Error "Starting Microsoft Fabric workspace removal script..."
if ($FabricWorkspaceName) {
    Write-Info "Target workspace name: $FabricWorkspaceName"
} else {
    Write-Info "Target workspace ID: $FabricWorkspaceId"
}

try {
    # Calculate paths - script is now in utils, but fabric scripts are in ../fabric
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $FabricScriptsDir = Join-Path (Split-Path -Parent $ScriptDir) "fabric"
    $RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
    $RequirementsPath = Join-Path $FabricScriptsDir "requirements.txt"
    
    # Initialize Python environment
    $pythonExec = Initialize-PythonEnvironment -RepoRoot $RepoRoot -SkipVirtualEnv:$SkipPythonVirtualEnvironment -SkipDependencies:$SkipPythonDependencies -SkipPipUpgrade:$SkipPipUpgrade -RequirementsPath $RequirementsPath

    # Execute Python removal script - change to fabric scripts directory
    Push-Location $FabricScriptsDir
    Write-Warning "Starting Fabric workspace removal..."
    
    # Build command arguments
    $pythonArgs = @()
    if ($FabricWorkspaceName) { $pythonArgs += "--workspaceName", $FabricWorkspaceName }
    if ($FabricWorkspaceId) { $pythonArgs += "--workspaceId", $FabricWorkspaceId }
    
    # Execute Python script
    & $pythonExec -u remove_fabric_workspace.py @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Fabric workspace removal completed successfully!"
    } else {
        Write-Error "❌ Fabric workspace removal failed with exit code: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} catch {
    Write-Error "❌ Removal failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Warning "Troubleshooting tips:"
    @(
        "1. Verify you are logged in to Azure CLI: az login",
        "2. Check that you have Admin permissions on the workspace",
        "3. Ensure the workspace name or ID is correct and accessible"
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