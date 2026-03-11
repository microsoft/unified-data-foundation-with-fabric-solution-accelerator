# Utility Scripts

This folder contains utility scripts for managing Microsoft Fabric resources and automating common tasks in the Unified Data Foundation solution.

## Table of Contents

- [Utility Scripts](#utility-scripts)
  - [Table of Contents](#table-of-contents)
  - [Get-FabricEnvironmentDefinition.ps1](#get-fabricenvironmentdefinitionps1)
  - [Get-FabricNotebookDefinition.ps1](#get-fabricnotebookdefinitionps1)
  - [Run-FabricJsonTokenizer.ps1](#run-fabricjsontokenizerps1)
  - [Run-PythonScript.ps1](#run-pythonscriptps1)
  - [run\_python\_script\_fabric\_admins.ps1](#run_python_script_fabric_adminsps1)

## Get-FabricEnvironmentDefinition.ps1
Retrieves and decodes Microsoft Fabric Environment definitions using the Fabric REST API.

**Purpose:** Download environment configurations including libraries, custom libraries, settings, and configuration files for backup or deployment purposes.

**Required Parameters:**
- `-WorkspaceId`: GUID of the Fabric workspace containing the environment
- `-EnvironmentId`: GUID of the environment to retrieve

**Optional Parameters:**
- `-FolderPath`: Path to save decoded definition files (default: `src/environment` relative to repository root)
- `-Format`: Format parameter for the environment definition (as supported by the API)
- `-SkipTokenization`: Skip automatic tokenization of JSON files after creation (default: tokenization is performed)

**Default Behavior:** Saves files to `src/environment` folder and automatically tokenizes the resulting JSON files.

**Examples:**
```powershell
# Basic usage with default folder and tokenization
.\Get-FabricEnvironmentDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -EnvironmentId "bbbbcccc-1111-dddd-2222-eeee3333ffff"

# Custom folder path
.\Get-FabricEnvironmentDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -EnvironmentId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -FolderPath "C:\temp\environment"

# Skip tokenization
.\Get-FabricEnvironmentDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -EnvironmentId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -SkipTokenization
```

## Get-FabricNotebookDefinition.ps1
Retrieves and decodes Microsoft Fabric Notebook definitions using the Fabric REST API.

**Purpose:** Download notebook configurations including notebook content (.ipynb or .py, .scala, .r, .sql files) and platform configuration.

**Required Parameters:**
- `-WorkspaceId`: GUID of the Fabric workspace containing the notebook
- `-NotebookId`: GUID of the notebook to retrieve

**Optional Parameters:**
- `-FolderPath`: Path to save decoded definition files (default: `src/definitions/notebook` relative to repository root)
- `-Format`: Format parameter for the notebook definition (supported formats: `ipynb` and `fabricGitSource`; default: `fabricGitSource`)
- `-SkipTokenization`: Skip automatic tokenization of JSON files after creation (default: tokenization is performed)

**Default Behavior:** Saves files to `src/definitions/notebook` folder and automatically tokenizes the resulting JSON files.

**Examples:**
```powershell
# Basic usage with default folder and tokenization
.\Get-FabricNotebookDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -NotebookId "bbbbcccc-1111-dddd-2222-eeee3333ffff"

# Use ipynb format
.\Get-FabricNotebookDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -NotebookId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -Format "ipynb"

# Custom folder path
.\Get-FabricNotebookDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -NotebookId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -FolderPath "C:\temp\notebook"

# Skip tokenization
.\Get-FabricNotebookDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -NotebookId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -SkipTokenization
```

## Run-FabricJsonTokenizer.ps1
Processes JSON configuration files and replaces specific values with standardized tokens for deployment automation.

**Purpose:** Tokenize Fabric resource definitions to make them reusable across different environments.

**Required Parameters:**
- `-SchemaType`: The schema type to process (valid values: `Environment`, `Notebook`)

**Optional Parameters:**
- `-JsonFilePath`: Path to the JSON file to tokenize (default: calculated based on SchemaType)
- `-OutputPath`: Output path for the tokenized JSON (default: overwrites the original file)
- `-DryRun`: Shows what would be changed without modifying files (default: false)
- `-SaveTokenMap`: Creates a separate token mapping file alongside the tokenized JSON (default: false)

**Default Behavior:** 
- Environment: Processes JSON files from `src/environment/`
- Notebook: Processes JSON files from `src/definitions/notebook/`

**Examples:**
```powershell
# Basic usage - tokenize notebook with default settings
.\Run-FabricJsonTokenizer.ps1 -SchemaType Notebook

# Dry run to preview changes
.\Run-FabricJsonTokenizer.ps1 -SchemaType Environment -DryRun

# Save token mapping file
.\Run-FabricJsonTokenizer.ps1 -SchemaType Notebook -SaveTokenMap

# Custom output path
.\Run-FabricJsonTokenizer.ps1 -SchemaType Environment -OutputPath "environment_tokenized.json"

# Custom input file
.\Run-FabricJsonTokenizer.ps1 -SchemaType Notebook -JsonFilePath "C:\custom\notebook.json"
```

## Run-PythonScript.ps1
Unified script to execute Python scripts with proper environment management.

**Purpose:** Execute Python scripts with automatic virtual environment setup and dependency management.

**Required Parameters:**
- `-ScriptPath`: Relative path to the Python script to execute (relative to repository root)

**Optional Parameters:**
- `-ScriptArguments`: Array of arguments to pass to the Python script (default: empty array)
- `-SkipPythonVirtualEnvironment`: Use system Python directly instead of creating virtual environment (default: false)
- `-SkipPythonDependencies`: Skip installing Python dependencies (default: false, assumes pre-installed)
- `-SkipPipUpgrade`: Skip upgrading pip to latest version (default: false)
- `-RequirementsPath`: Path to requirements.txt file (default: repository root `requirements.txt`)

**Default Behavior:** Creates a virtual environment, upgrades pip, installs dependencies from `requirements.txt`, then executes the specified Python script.

**Examples:**
```powershell
# Basic usage with full environment setup
.\Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/deploy_fabric_items.py"

# Skip virtual environment and use system Python
.\Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/deploy_fabric_items.py" -SkipPythonVirtualEnvironment

# Skip dependency installation (assume pre-installed)
.\Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/delete_fabric_items.py" -SkipPythonDependencies

# Pass arguments to the Python script
.\Run-PythonScript.ps1 -ScriptPath "infra/scripts/fabric/deploy_fabric_items.py" -ScriptArguments @("--verbose", "--config", "config.json")

# Use custom requirements file
.\Run-PythonScript.ps1 -ScriptPath "src/sample_data.py" -RequirementsPath "src/requirements_basics.txt"
```

## run_python_script_fabric_admins.ps1
Adds administrators to all available Microsoft Fabric workspaces.

**Purpose:** Add specified administrators to all Microsoft Fabric workspaces that the current user has access to, supporting both user principal names (UPNs) and service principal object IDs.

**Optional Parameters:**
- `-FabricAdmins`: JSON array of administrators using UPNs or GUIDs (e.g., `["user@contoso.com", "guid-for-service-principal"]`). Uses `AZURE_FABRIC_ADMIN_MEMBERS` env var if not provided.
- `-FabricAdminsByObjectId`: JSON array of object IDs for workspace administrators with fallback logic for User/ServicePrincipal types. Uses `AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID` env var if not provided.
- `-SkipPythonVirtualEnvironment`: Use system Python directly instead of creating virtual environment (default: false)
- `-SkipPythonDependencies`: Skip installing Python dependencies (default: false, assumes pre-installed)
- `-SkipPipUpgrade`: Skip upgrading pip to latest version (default: false)

**Default Behavior:** Reads administrators from environment variables, creates a virtual environment, installs dependencies, and adds administrators to all accessible workspaces.

**Examples:**
```powershell
# Add administrators using UPNs
.\run_python_script_fabric_admins.ps1 -FabricAdmins '["user@contoso.com", "admin@company.com"]'

# Add administrators using object IDs
.\run_python_script_fabric_admins.ps1 -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012"]'

# Add both UPNs and object IDs
.\run_python_script_fabric_admins.ps1 -FabricAdmins '["user@contoso.com"]' -FabricAdminsByObjectId '["12345678-1234-1234-1234-123456789012"]'

# Use environment variables (default behavior)
.\run_python_script_fabric_admins.ps1

# Skip virtual environment setup
.\run_python_script_fabric_admins.ps1 -FabricAdmins '["user@contoso.com"]' -SkipPythonVirtualEnvironment
```
