#!/bin/bash
# provision_databricks_items.sh
# Cross-platform Databricks deployment script (Linux/macOS)

set -e

# Function to prompt for missing arguments
prompt_if_missing() {
  local var_name="$1"
  local prompt_msg="$2"
  local var_value="${!var_name}"
  if [ -z "$var_value" ]; then
    read -rp "$prompt_msg: " var_value
    eval "$var_name=\"$var_value\""
  fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --workspaceUrl) workspaceUrl="$2"; shift 2;;
    --token) token="$2"; shift 2;;
    --solutionname) solutionname="$2"; shift 2;;
    --catalogname) catalogname="$2"; shift 2;;
    --schemaname) schemaname="$2"; shift 2;;
    --cluster-id) cluster_id="$2"; shift 2;;
    --catalog-managed-location) catalog_managed_location="$2"; shift 2;;
    --fabric-admins) fabric_admins="$2"; shift 2;;
    *) echo "Unknown argument: $1"; exit 1;;
  esac
done

# Prompt for missing arguments
prompt_if_missing workspaceUrl "Enter Databricks Workspace URL (e.g. https://adb-xxxx.azuredatabricks.net)"
prompt_if_missing token "Enter Databricks Token"
prompt_if_missing solutionname "Enter Solution Name (e.g. maag)"
prompt_if_missing catalogname "Enter Catalog Name (e.g. maagcatalog)"
prompt_if_missing schemaname "Enter Schema Name (e.g. sales)"
prompt_if_missing cluster_id "Enter Cluster ID"
prompt_if_missing catalog_managed_location "Enter Catalog Managed Location (external location name or URI)"

# Check for fabric admins from environment variable if not provided
# Note: This parameter is for consistency with Fabric deployment scripts
# but is not currently used in Databricks deployment
if [ -z "$fabric_admins" ]; then
  fabric_admins="$AZURE_FABRIC_ADMIN_MEMBERS"
  if [ -n "$fabric_admins" ]; then
    echo "Fabric admins parameter detected from environment variable (not used in Databricks deployment)"
  fi
fi

# Parse fabric admins JSON array if provided (for potential future Fabric integration)
fabric_admins_args=()
if [ -n "$fabric_admins" ]; then
  # Check if jq is available for JSON parsing
  if command -v jq &> /dev/null; then
    # Parse JSON array using jq
    while IFS= read -r admin; do
      fabric_admins_args+=("$admin")
    done < <(echo "$fabric_admins" | jq -r '.[]' 2>/dev/null || echo "")
    
    if [ ${#fabric_admins_args[@]} -gt 0 ]; then
      echo "Parsed ${#fabric_admins_args[@]} administrator(s) from JSON array"
    else
      echo "Warning: Failed to parse fabric admins JSON array, skipping..."
    fi
  else
    echo "Warning: jq not available for JSON parsing, fabric admins parameter ignored"
  fi
fi

# Check Python
if ! command -v python &> /dev/null; then
  echo "Python is not installed. Please install Python 3.8+ and try again."; exit 1
fi

# Check pip
if ! command -v pip &> /dev/null; then
  echo "pip is not installed. Please install pip and try again."; exit 1
fi

# Create and activate Python virtual environment
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="$script_dir/.venv"

echo "Setting up Python virtual environment..."
if [ ! -d "$venv_dir" ]; then
  python -m venv "$venv_dir"
  if [ $? -ne 0 ]; then
    echo "Failed to create Python virtual environment."; exit 1
  fi
  echo "Created virtual environment at: $venv_dir"
else
  echo "Using existing virtual environment at: $venv_dir"
fi

# Activate virtual environment
source "$venv_dir/bin/activate"
if [ $? -ne 0 ]; then
  echo "Failed to activate virtual environment."; exit 1
fi
echo "Activated virtual environment"

# Verify pip is available in virtual environment
if ! command -v pip &> /dev/null; then
  echo "pip is not available in the virtual environment."; exit 1
fi
echo "pip is available in virtual environment"

# Install dependencies from local requirements.txt
requirements="$script_dir/requirements.txt"
if [ ! -f "$requirements" ]; then
  echo "Could not find requirements.txt at $requirements. Please check your repository structure."; exit 1
fi
echo "Installing Python dependencies from $requirements..."
pip install -r "$requirements" --quiet

# Run the deployment script from the current directory

python -u create_databricks_items_maag.py \
  --workspaceUrl "$workspaceUrl" \
  --token "$token" \
  --solutionname "$solutionname" \
  --catalogname "$catalogname" \
  --schemaname "$schemaname" \
  --cluster-id "$cluster_id" \
  --catalog-managed-location "$catalog_managed_location"

if [ $? -eq 0 ]; then
  echo "✅ Databricks deployment completed successfully!"
  echo
  echo "Next steps:"
  echo "1. Open your Databricks workspace"
  echo "2. Verify that notebooks and sample data have been uploaded"
  echo "3. Check that Unity Catalog and schema are created as expected"
  echo "4. Explore the uploaded notebooks and data"
else
  echo "❌ Databricks deployment failed. Check the output above for errors."
  exit 1
fi
