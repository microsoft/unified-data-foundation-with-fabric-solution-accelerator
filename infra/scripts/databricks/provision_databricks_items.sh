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
    *) echo "Unknown argument: $1"; exit 1;;
  esac
done

# Prompt for missing arguments
prompt_if_missing workspaceUrl "Enter Databricks Workspace URL (e.g. https://adb-xxxx.azuredatabricks.net)"
# Well-known Azure AD application ID for Azure Databricks (same across all tenants)
DATABRICKS_RESOURCE_ID="2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"

# Auto-acquire token via Azure CLI if not provided
if [ -z "$token" ]; then
  echo "[AUTH] No token provided. Attempting Azure CLI login (Entra ID)..."
  # Check if user is already logged in
  if az account show &>/dev/null; then
    echo "[AUTH] Active Azure CLI session detected."
  else
    echo "[AUTH] No active Azure CLI session found. Running 'az login'..."
    az login > /dev/null
    if [ $? -ne 0 ]; then
      echo "[AUTH] az login failed. Falling back to manual entry."
      prompt_if_missing token "Enter Databricks Token (PAT or Entra ID)"
    fi
  fi
  if [ -z "$token" ]; then
    token=$(az account get-access-token --resource "$DATABRICKS_RESOURCE_ID" --query accessToken -o tsv 2>/dev/null)
    if [ -n "$token" ]; then
      echo "[AUTH] Successfully obtained token via Azure CLI (Entra ID)."
    else
      echo "[AUTH] Azure CLI token failed. Falling back to manual entry."
      prompt_if_missing token "Enter Databricks Token (PAT or Entra ID)"
    fi
  fi
fi
prompt_if_missing solutionname "Enter Solution Name (e.g. maag)"
prompt_if_missing catalogname "Enter Catalog Name (e.g. maagcatalog)"
prompt_if_missing schemaname "Enter Schema Name (e.g. sales)"
# Auto-detect Cluster ID via Databricks REST API if not provided
if [ -z "$cluster_id" ]; then
  echo "[AUTO] Attempting to detect Databricks cluster ID..."
  clusters_json=$(curl -sf -X GET "${workspaceUrl}/api/2.0/clusters/list" \
    -H "Authorization: Bearer ${token}" 2>/dev/null || true)
  if [ -n "$clusters_json" ]; then
    detected_id=$(echo "$clusters_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
clusters = data.get('clusters', [])
running = [c for c in clusters if c.get('state') == 'RUNNING']
pick = running[0] if running else (clusters[0] if clusters else None)
if pick:
    print(pick['cluster_id'])
" 2>/dev/null || true)
    if [ -n "$detected_id" ]; then
      cluster_id="$detected_id"
      echo "[AUTO] Found cluster: $cluster_id"
    fi
  fi
  prompt_if_missing cluster_id "Enter Cluster ID"
fi
prompt_if_missing catalog_managed_location "Enter Catalog Managed Location (external location name or URI)"

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
