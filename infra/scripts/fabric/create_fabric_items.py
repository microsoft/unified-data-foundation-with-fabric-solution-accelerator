import os
import glob
import time
import argparse
import sys
import json
import base64
import re
import requests
from fabric_api import create_fabric_client, FabricApiError
from powerbi_api import *

solution_name = "Unified Data Foundation with Fabric"

####################
# Helper Functions #
####################

def build_folder_path_mapping(folders: list) -> dict:
    """Build a mapping of full folder paths to folder IDs."""
    folder_lookup = {f['id']: f for f in folders}
    path_map = {}
    
    def build_path(folder_id: str) -> str:
        if folder_id not in folder_lookup:
            return ""
        
        folder = folder_lookup[folder_id]
        name = folder['displayName']
        parent_id = folder.get('parentFolderId')
        
        if not parent_id:
            return name
        
        parent_path = build_path(parent_id)
        return f"{parent_path}/{name}"
    
    for folder in folders:
        full_path = build_path(folder['id'])
        path_map[full_path] = folder['id']
    
    return path_map


def create_fabric_directory_structure(fabric_client, workspace_id: str, folder_path: str, existing_folder_map: dict) -> str:
    """
    Create a complete folder hierarchy.
    
    Args:
        fabric_client: Fabric API client instance
        workspace_id: Target workspace ID
        folder_path: Full path separated by forward slashes
        existing_folder_map: Pre-built mapping of folder paths to IDs
        
    Returns:
        Final folder ID
    """
    # Check if folder already exists
    if folder_path in existing_folder_map:
        return existing_folder_map[folder_path]
    
    # Split path and create recursively
    path_parts = folder_path.split('/')
    
    if len(path_parts) == 1:
        # Root folder
        folder_id = fabric_client.create_folder(workspace_id, path_parts[0])
        existing_folder_map[folder_path] = folder_id
        return folder_id
    else:
        # Ensure parent exists
        parent_path = '/'.join(path_parts[:-1])
        parent_id = create_fabric_directory_structure(fabric_client, workspace_id, parent_path, existing_folder_map)
        
        # Create this folder
        folder_name = path_parts[-1]
        folder_id = fabric_client.create_folder(workspace_id, folder_name, parent_id)
        existing_folder_map[folder_path] = folder_id
        return folder_id


def create_lakehouse_directory_structure(file_system_client, lakehouse_root_path: str, folder_path: str) -> None:
    """Create directory structure in a lakehouse for UDFF data organization."""
    if not folder_path or folder_path == '.':
        return
    
    full_path = f"{lakehouse_root_path}/{folder_path}".replace('\\', '/')
    
    try:
        # Check if directory exists
        directory_client = file_system_client.get_directory_client(full_path)
        directory_client.get_directory_properties()
    except Exception:
        try:
            # Create parent directories first
            parent_path = os.path.dirname(folder_path)
            if parent_path and parent_path != '.':
                create_lakehouse_directory_structure(file_system_client, lakehouse_root_path, parent_path)
            
            # Create the directory
            directory_client = file_system_client.get_directory_client(full_path)
            directory_client.create_directory()
            print(f"  ✅ Created directory: {os.path.basename(folder_path)}")
        except Exception as e:
            print(f"❌ ERROR: Failed to create directory {full_path}: {str(e)}")
            print(f"   Solution: Check OneLake connectivity and permissions")
            sys.exit(1)


####################
# Variables set up #
####################

workspace_default_name = "Unified Data Foundation with Fabric"
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))  # Go up three levels from infra/scripts/fabric to repo root

##########################
# Command line arguments #
##########################

# Parse command line arguments
parser = argparse.ArgumentParser(description=f'Deploy {solution_name} to Microsoft Fabric')
parser.add_argument('--capacityName', required=True, help='Microsoft Fabric capacity name')
parser.add_argument('--workspaceName', required=False, help=f'Workspace name (if not provided, will use "{workspace_default_name}")')
args = parser.parse_args()

print(f"🚀 Starting {solution_name} deployment to Microsoft Fabric")
print(f"📋 Target capacity: {args.capacityName}")
if args.workspaceName:
    print(f"📋 Target workspace name: {args.workspaceName}")
else:
    print(f"📋 Will create new workspace with auto-generated name")
print("-" * 60)

capacity_name = args.capacityName
workspace_name = args.workspaceName

# Initialize Fabric API client
try:
    fabric_client = create_fabric_client()
    print("✅ Authentication successful")
except Exception as e:
    print(f"❌ ERROR: Failed to authenticate with Fabric APIs")
    print(f"   Details: {str(e)}")
    print("   Solution: Please ensure you are logged in with Azure CLI: az login")
    sys.exit(1)


#############
# Workspace #
#############
# Docs: https://learn.microsoft.com/en-us/rest/api/fabric/admin/workspaces

try:
    # Get capacity ID from capacity name
    print(f"🔍 Looking up capacity: '{capacity_name}'")
    capacities = fabric_client.get_capacities()
    capacity = next((c for c in capacities if c['displayName'].lower() == capacity_name.lower()), None)
    
    if not capacity:
        print(f"❌ ERROR: Capacity '{capacity_name}' not found")
        print("   Available capacities:")
        for cap in capacities:
            print(f"   - {cap['displayName']} (ID: {cap['id']})")
        sys.exit(1)
    
    capacity_id = capacity['id']
    print(f"✅ Found capacity: '{capacity['displayName']}' (ID: {capacity_id})")
    print(f"   SKU: {capacity.get('sku', 'N/A')}")
    print(f"   State: {capacity.get('state', 'N/A')}")
    print(f"   Region: {capacity.get('region', 'N/A')}")
    
    # Handle workspace creation or lookup
    # If no workspace name provided, use default name
    if not workspace_name:
        workspace_name = workspace_default_name
        print(f"📋 No workspace name provided, using default: '{workspace_name}'")
    
    # Check if workspace with the name already exists
    print(f"🔍 Looking for existing workspace: '{workspace_name}'")
    workspaces = fabric_client.get_workspaces()
    workspace = next((w for w in workspaces if w['displayName'].lower() == workspace_name.lower()), None)
    
    if workspace:
        workspace_id = workspace['id']
        print(f"✅ Found existing workspace: '{workspace_name}' (ID: {workspace_id})")
        
        # Assign the existing workspace to the specified capacity
        print(f"🔄 Assigning workspace to capacity: '{capacity_name}'")
        fabric_client.assign_workspace_to_capacity(workspace_id, capacity_id)
        print(f"✅ Workspace assigned to capacity: '{capacity_name}'")
    else:
        # Create new workspace with the specified name
        print(f"🏗️  Creating new workspace: '{workspace_name}'")
        workspace_id = fabric_client.create_workspace(workspace_name, capacity_id)
        print(f"✅ Created workspace: '{workspace_name}' (ID: {workspace_id})")
    
except FabricApiError as e:
    if e.status_code == 404:
        print(f"❌ ERROR: Resource not found")
    elif e.status_code == 403:
        print(f"❌ ERROR: Access denied")
        print("   Solution: Ensure you have appropriate permissions")
    else:
        print(f"❌ ERROR: Fabric API error")
    print(f"   Status Code: {e.status_code}")
    print(f"   Details: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error during workspace setup: {str(e)}")
    sys.exit(1)

####################
# Folder structure #
####################
# Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/folders

# Prepare variables
fabric_folder_path_lakehouses = 'lakehouses'
fabric_folder_path_notebooks = 'notebooks'
fabric_folder_path_notebooks_bronze_to_silver = 'notebooks/bronze_to_silver'
fabric_folder_path_notebooks_data_management = 'notebooks/data_management'
fabric_folder_path_notebooks_schema = 'notebooks/schema'
fabric_folder_path_notebooks_silver_to_gold = 'notebooks/silver_to_gold'
fabric_folder_path_reports = 'reports'
udff_fabric_folders = [
    fabric_folder_path_lakehouses,
    fabric_folder_path_notebooks_bronze_to_silver,
    fabric_folder_path_notebooks_data_management,
    fabric_folder_path_notebooks_schema,
    fabric_folder_path_notebooks_silver_to_gold,
    fabric_folder_path_reports
]

# Create folder structure using the new API client
try:
    print(f"📁 Creating folder structure for '{solution_name}' solution")
    
    # Get existing folders and build path mapping
    fabric_folders = build_folder_path_mapping(fabric_client.get_folders(workspace_id))
    
    # Create hierarchy of folders based on full path
    for udff_folder_path in udff_fabric_folders:
        if udff_folder_path in fabric_folders:
            print(f"  📁 Folder '{udff_folder_path}' already exists")
        else:
            try:
                folder_id = create_fabric_directory_structure(fabric_client, workspace_id, udff_folder_path, fabric_folders)
                print(f"  ✅ Created folder '{udff_folder_path}'")
            except Exception as e:
                print(f"❌ ERROR: Failed to create folder '{udff_folder_path}': {str(e)}")
                sys.exit(1)
                
except FabricApiError as e:
    print(f"❌ ERROR: Failed to manage folders: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error managing folders: {str(e)}")
    sys.exit(1)

##############
# Lakehouses #
##############
# Docs: https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/items

# Variables
udff_lakehouse_bronze_name = 'maag_bronze'
udff_lakehouse_silver_name = 'maag_silver'
udff_lakehouse_gold_name = 'maag_gold'
udff_lakehouses = {
    udff_lakehouse_bronze_name,
    udff_lakehouse_silver_name,
    udff_lakehouse_gold_name
}
lakehouse_folder_id = fabric_folders.get(fabric_folder_path_lakehouses)
fabric_lakehouses = {}

# Get existing lakehouses and create new ones
print(f"🏠 Setting up lakehouses (Bronze, Silver, Gold)")
try:
    # Get existing lakehouses using the new API client methods
    print(f"  📋 Checking for existing lakehouses in workspace...")
    existing_lakehouses = fabric_client.get_lakehouses(workspace_id)
    
    # Build mapping of existing lakehouses by name
    for lakehouse in existing_lakehouses:
        fabric_lakehouses[lakehouse['displayName']] = lakehouse
    
    print(f"  📊 Found {len(existing_lakehouses)} existing lakehouse(s)")

    # Create UDFF lakehouses
    for lakehouse_name in udff_lakehouses:
        if lakehouse_name in fabric_lakehouses:
            print(f"  🏠 Lakehouse '{lakehouse_name}' already exists")
        else:
            print(f"  🏗️ Creating lakehouse '{lakehouse_name}'...")
            try:
                # Use the new create_lakehouse method
                lakehouse = fabric_client.create_lakehouse(
                    workspace_id=workspace_id,
                    display_name=lakehouse_name,
                    description=f"UDFF {lakehouse_name.split('_')[-1].title()} layer lakehouse for data processing",
                    folder_id=lakehouse_folder_id,
                    enable_schemas=True,
                    wait_for_lro=True
                )
                
                print(f"  ✅ Lakehouse '{lakehouse_name}' created successfully")
                fabric_lakehouses[lakehouse_name] = fabric_client.get_lakehouse(workspace_id=workspace_id, lakehouse_id=lakehouse['id'])
                
            except FabricApiError as e:
                print(f"❌ ERROR: Failed to create lakehouse '{lakehouse_name}': {e}")
                print(f"   Solution: Check workspace permissions and quotas")
                sys.exit(1)
            except Exception as e:
                print(f"❌ ERROR: Unexpected error creating lakehouse '{lakehouse_name}': {str(e)}")
                print(f"   Solution: Verify workspace configuration and try again")
                sys.exit(1)

except FabricApiError as e:
    print(f"❌ ERROR: Failed to manage lakehouses: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error managing lakehouses: {str(e)}")
    sys.exit(1)

#######################
# Lakehouse CSV files #
#######################
# Docs: https://learn.microsoft.com/en-us/fabric/onelake/onelake-access-python

# Prepare variables
samples_local_folder_path = os.path.join(repo_root, 'infra', 'data')
bronze_lakehouse = fabric_lakehouses[udff_lakehouse_bronze_name]
bronze_lakehouse_onelake_root_path = f"{bronze_lakehouse['displayName']}.Lakehouse/Files"

# Get all CSV files in 'infra/data/samples_fabric'
csv_pattern = os.path.join(samples_local_folder_path, '**', '*.csv')
csv_file_paths = glob.glob(csv_pattern, recursive=True)

# Connect to bronze lakehouse using the new API client
print(f"📊 Uploading sample data to bronze lakehouse")
try:
    udff_wfs_client = fabric_client.get_workspace_file_system_client(workspace_name)
except Exception as e:
    print(f"❌ ERROR: Failed to connect to OneLake: {str(e)}")
    print("   Solution: Ensure you have proper permissions and the workspace is accessible")
    sys.exit(1)

# Create folder structure for CSV files
created_folders = set()

for local_file_path in csv_file_paths:
    # Get relative path from samples folder
    relative_file_path = os.path.relpath(local_file_path, samples_local_folder_path)
    bronze_datalake_file_path = os.path.join(bronze_lakehouse_onelake_root_path, relative_file_path)
    relative_folder_path = os.path.dirname(relative_file_path)
    bronze_datalake_folder_path = os.path.join(bronze_lakehouse_onelake_root_path, relative_folder_path)
    # Create folders in lakehouse
    if relative_folder_path and relative_folder_path != '.' and relative_folder_path not in created_folders:
        try:
            create_lakehouse_directory_structure(udff_wfs_client, bronze_lakehouse_onelake_root_path, relative_folder_path)
            created_folders.add(relative_folder_path)
        except Exception as e:
            print(f"❌ ERROR: Failed to create folder structure '{relative_folder_path}': {str(e)}")
            sys.exit(1)

    # Upload file
    file_name = os.path.basename(local_file_path)
    try:
        bronze_datalake_file_client = udff_wfs_client.get_file_client(bronze_datalake_file_path)
        with open(local_file_path, "rb") as data:
            bronze_datalake_file_client.upload_data(data, overwrite=True)
        print(f"  ✅ Uploaded '{file_name}' to '{relative_file_path}'")
    except Exception as e:
        print(f"❌ ERROR: Failed to upload file '{file_name}': {str(e)}")
        sys.exit(1)

#############
# Notebooks #
#############
# Docs: https://learn.microsoft.com/en-us/rest/api/fabric/notebook/items

#Prepare variables
fabric_notebooks = {}
notebooks_directory = os.path.join(repo_root, 'src', 'fabric', 'notebooks')

#Item structure: {local notebook path: [source lakehouse name, destination lakehouse name, fabric folder path]}
udff_notebooks_path_lakehouse_folder = {
    # src\fabric\notebooks
    os.path.join(notebooks_directory, 'run_bronze_to_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks],
    os.path.join(notebooks_directory, 'run_silver_to_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks],

    # src\fabric\notebooks\bronze_to_silver notebooks
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_account.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_invoice.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_payment.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_order.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_orderLine.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_orderPayment.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_order.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_orderLine.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_orderPayment.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customer.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customeraccount.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customerRelationshipType.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customerTradeName.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_location.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_product.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_productCategory.ipynb'): [udff_lakehouse_bronze_name, udff_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    
    # src\fabric\notebooks\data_management notebooks
    os.path.join(notebooks_directory, 'data_management', 'drop_all_tables_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'drop_all_tables_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'trouble_shooting.ipynb'): [None, None, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'truncate_all_tables_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'truncate_all_tables_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_data_management],

    # src\fabric\notebooks\schema notebooks
    os.path.join(notebooks_directory, 'schema', 'model_finance_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesadb_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesfabric_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_shared_gold.ipynb'): [None, udff_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_finance_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesadb_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesfabric_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_shared_silver.ipynb'): [None, udff_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    
    # src\fabric\notebooks\silver_to_gold notebooks
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_account.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_invoice.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_payment.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order_line.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order_payment.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_order.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_orderLine.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_orderPayment.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_order.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_orderLine.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_orderPayment.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customer.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customeraccount.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customerRelationshipType.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customerTradeName.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_location.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_product.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_productCategory.ipynb'): [udff_lakehouse_silver_name, udff_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold]
}

# Obtain existing notebooks
print(f"📓 Deploying notebooks to workspace")

# Prepare notebook specifications for batch upload
notebook_specs = []
for notebook_path, (source_lakehouse_name, targeted_lakehouse_name, folder_path) in udff_notebooks_path_lakehouse_folder.items():
    notebook_specs.append({
        'path': notebook_path,
        'source_lakehouse': source_lakehouse_name,
        'target_lakehouse': targeted_lakehouse_name,
        'folder_path': folder_path
    })

# Deploy notebooks using optimized batch processing
try:
    # Inline batch_upload_notebooks logic
    # Get existing notebooks
    try:
        existing_notebooks = fabric_client.get_notebooks(workspace_id)
    except Exception as e:
        print(f"❌ ERROR: Failed to get existing notebooks: {str(e)}")
        print("   Solution: Check workspace permissions and connectivity")
        sys.exit(1)
    
    fabric_notebooks = {}
    upload_jobs = []  # Track LRO jobs for batch monitoring
    
    for i, spec in enumerate(notebook_specs, 1):
        notebook_path = spec['path']
        source_lakehouse_name = spec.get('source_lakehouse')
        target_lakehouse_name = spec.get('target_lakehouse')
        folder_path = spec['folder_path']
        
        notebook_name = os.path.basename(notebook_path).replace('.ipynb', '')
        folder_id = fabric_folders.get(folder_path)
        
        if not folder_id:
            print(f"❌ ERROR: Folder not found for path '{folder_path}', cannot deploy '{notebook_name}'")
            print(f"   Solution: Ensure folder structure was created successfully")
            sys.exit(1)
        
        # Get lakehouse objects
        target_lakehouse = fabric_lakehouses.get(target_lakehouse_name) if target_lakehouse_name else None
        source_lakehouse = fabric_lakehouses.get(source_lakehouse_name) if source_lakehouse_name else None
        existing_notebook_id = existing_notebooks.get(notebook_name)
        
        try:
            # Inline upload_notebook logic
            # Read and transform notebook content
            with open(notebook_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Transform notebook content by replacing UDFF-specific placeholders
            # Replace workspace placeholders
            pattern = r'WORKSPACE_NAME\s*=\s*\\"([^\\"]+)\\"'
            content = re.sub(pattern, f'WORKSPACE_ID = \\"{workspace_id}\\"', content)
            content = content.replace('{WORKSPACE_NAME}', '{WORKSPACE_ID}')
            
            # Replace lakehouse placeholders
            if source_lakehouse:
                pattern = r'SOURCE_LAKEHOUSE_NAME\s*=\s*\\"([^\\"]+)\\"'
                content = re.sub(pattern, f'SOURCE_LAKEHOUSE_ID = \\"{source_lakehouse["id"]}\\"', content)
                content = content.replace('{SOURCE_LAKEHOUSE_NAME}', '{SOURCE_LAKEHOUSE_ID}')
            
            # Fix ABFSS paths for UDFF project structure
            content = content.replace(
                'abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}.Lakehouse/',
                'abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/'
            )
            
            notebook_json = json.loads(content)
            
            # Update notebook metadata with UDFF lakehouse configuration
            if target_lakehouse:
                # Ensure metadata structure exists
                if 'metadata' not in notebook_json:
                    notebook_json['metadata'] = {}
                
                if 'dependencies' not in notebook_json['metadata']:
                    notebook_json['metadata']['dependencies'] = {}
                
                # Set lakehouse configuration
                notebook_json['metadata']['dependencies']['lakehouse'] = {
                    'default_lakehouse': target_lakehouse['id'],
                    'default_lakehouse_name': target_lakehouse['displayName'],
                    'default_lakehouse_workspace_id': target_lakehouse['workspaceId']
                }
            
            # Prepare API data
            notebook_base64 = base64.b64encode(json.dumps(notebook_json).encode('utf-8'))
            notebook_data = {
                "displayName": os.path.basename(notebook_path).replace('.ipynb', ''),
                "definition": {
                    "format": "ipynb",
                    "parts": [{
                        "path": "notebook-content.ipynb",
                        "payload": notebook_base64.decode('utf-8'),
                        "payloadType": "InlineBase64"
                    }]
                },
                "folderId": folder_id
            }
            
            # Upload or update
            if existing_notebook_id:
                print(f"  ✅ Updating notebook '{notebook_name}'")
                response = fabric_client.update_notebook(workspace_id, existing_notebook_id, notebook_data, wait_for_lro=False)
            else:
                print(f"  ✅ Creating notebook '{notebook_name}'")
                response = fabric_client.create_notebook(workspace_id, notebook_data, wait_for_lro=False)
            
            if response.status_code == 202:
                # Track LRO for batch monitoring
                job_monitoring_url = response.headers.get('Location')
                if job_monitoring_url:
                    upload_jobs.append({
                        'notebook_name': notebook_name,
                        'job_url': job_monitoring_url,
                        'start_time': time.time()
                    })
            elif response.ok:
                fabric_notebooks[notebook_name] = response.json().get('id', 'unknown')
            else:
                print(f"❌ ERROR: Failed to upload '{notebook_name}': {response.text}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ ERROR: Error uploading '{notebook_name}': {str(e)}")
            print(f"   Solution: Check notebook file integrity and workspace permissions")
            sys.exit(1)
    
    # Check jobs completion
    if upload_jobs:
        print(f"  ⏳ Waiting for {len(upload_jobs)} notebook upload jobs...")
        # Inline wait_for_upload_completion logic
        pending_jobs = upload_jobs.copy()
        start_time = time.time()
        max_wait_time = 600
        check_interval = 5
        
        while pending_jobs and (time.time() - start_time) < max_wait_time:
            
            jobs_to_remove = []
            for job in pending_jobs:
                try:
                    # Use the full job URL directly with proper headers
                    response = requests.get(job['job_url'], headers=fabric_client.get_headers())
                    
                    if response.ok:
                        job_result = response.json()
                        notebook_id = job_result.get('id', 'unknown')
                        fabric_notebooks[job['notebook_name']] = notebook_id
                        
                        print(f"    ✅ '{job['notebook_name']}' completed")
                        jobs_to_remove.append(job)
                        
                except Exception as e:
                    # Critical errors during job monitoring should fail the deployment
                    if time.time() - job['start_time'] > max_wait_time:
                        print(f"❌ ERROR: Upload job for '{job['notebook_name']}' failed: {str(e)}")
                        print(f"   Solution: Check workspace performance and retry deployment")
                        sys.exit(1)
                    else:
                        print(f"    ⚠️ Monitoring error for '{job['notebook_name']}': {str(e)}")
                        jobs_to_remove.append(job)
            
            for job in jobs_to_remove:
                pending_jobs.remove(job)

            if pending_jobs:
                time.sleep(check_interval)
                
    # Refresh notebooks list
    try:
        final_notebooks = fabric_client.get_notebooks(workspace_id)
        fabric_notebooks.update(final_notebooks)
    except Exception as e:
        print(f"❌ ERROR: Failed to refresh notebooks list: {str(e)}")
        print(f"   Solution: Check workspace connectivity and permissions")
        sys.exit(1)
    
    uploaded_count = len([spec for spec in notebook_specs if os.path.basename(spec['path']).replace('.ipynb', '') in fabric_notebooks])
    print(f"✅ Successfully deployed {uploaded_count}/{len(notebook_specs)} notebooks")
    
except Exception as e:
    print(f"❌ ERROR: Failed to deploy notebooks: {str(e)}")
    sys.exit(1)

#################
# Notebook Jobs #
#################
# Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler

# Prepare variables
notebooks_to_run = [
    'run_bronze_to_silver',
    'run_silver_to_gold'
]

# Execute notebooks using sequential execution with 20-second monitoring
print(f"🚀 Executing data transformation pipelines sequentially")

execution_results = {}
successful_executions = []
failed_executions = []

# Execute notebooks one by one in sequence
for notebook_name in notebooks_to_run:
    # Check if notebook exists
    if notebook_name not in fabric_notebooks:
        print(f"  ❌ Notebook '{notebook_name}' not found")
        execution_results[notebook_name] = {'status': 'NotFound', 'error': 'Notebook not found'}
        failed_executions.append(notebook_name)
        continue
    
    notebook_id = fabric_notebooks[notebook_name]
    
    try:
        # Execute the notebook job using fabric API client
        result = fabric_client.schedule_notebook_job(workspace_id, notebook_id)
        execution_results[notebook_name] = result
        
        # Track success/failure
        if result.get('status') == 'Completed':
            successful_executions.append(notebook_name)
        else:
            failed_executions.append(notebook_name)
            
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        execution_results[notebook_name] = {'status': 'Failed', 'error': error_msg}
        failed_executions.append(notebook_name)
        print(f"  ❌ Error executing '{notebook_name}': {error_msg}")
    
    # Add delay between notebook executions (except for last one)
    if notebook_name != notebooks_to_run[-1]:
        print(f"    📋 Completed '{notebook_name}', proceeding to next notebook...")

# Final results summary
print(f"\n📊 Execution Summary:")
for notebook_name, result in execution_results.items():
    if result.get('status') == 'Completed':
        duration = result.get('duration', 'unknown')
        print(f"  ✅ '{notebook_name}' completed in {duration}")
    else:
        error = result.get('error', 'Unknown error')
        print(f"  ❌ '{notebook_name}' failed: {result.get('status', 'Unknown')} - {error}")

# Exit with error if any notebooks failed (consistent with rest of script)
if failed_executions:
    print(f"\n❌ ERROR: {len(failed_executions)} notebook(s) failed to execute successfully")
    print(f"   Failed notebooks: {', '.join(failed_executions)}")
    sys.exit(1)
else:
    print(f"✅ All {len(successful_executions)} pipelines executed successfully in sequence")

###################
# PowerBI Reports #
###################
# Docs: https://learn.microsoft.com/en-us/rest/api/power-bi/imports

print(f"📊 Deploying Power BI reports")
try:
    powerbi_client = create_powerbi_client()
    powerbi_client.set_powerbi_auth_token()
    print("✅ Power BI client authenticated successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to authenticate Power BI client")
    print(f"   Details: {str(e)}")
    print("   Solution: Ensure you have proper Power BI permissions and are logged in")
    sys.exit(1)

reports_local_folder_path = os.path.join(repo_root, 'reports')
pbix_pattern = os.path.join(reports_local_folder_path, '**', '*.pbix')
pbix_file_paths = glob.glob(pbix_pattern, recursive=True)
deployed_reports = []  # Track deployed reports for final summary

if not pbix_file_paths:
    print("  ℹ️ No Power BI report files (.pbix) found in reports directory")
else:
    print(f"  📋 Found {len(pbix_file_paths)} Power BI report(s) to deploy")

for pbix_file_path in pbix_file_paths:
    report_file_name = os.path.basename(pbix_file_path)
    report_name = report_file_name.replace('.pbix','')
    print(f"  📊 Deploying report '{report_name}'")
    
    try:
        new_report = powerbi_client.new_report(
            report_name=report_name,
            file_path=pbix_file_path,
            conflict_action=ImportConflictHandlerMode.CREATE_OR_OVERWRITE,
            workspace_id=workspace_id,
            subfolder_object_id=fabric_folders[fabric_folder_path_reports],
            timeout=300  # 5 minutes
        )
        report_name = new_report.get('name', 'Unknown')
        report_id = new_report.get('id', 'Unknown')
        deployed_reports.append({'name': report_name, 'id': report_id})  # Track deployed report
        print(f"  ✅ Successfully deployed report '{report_name}' (ID: {report_id})")
        
        # Get connection details from Gold lakehouse and configure dataset parameters
        print(f"  🔧 Configuring dataset parameters for '{report_name}'...")
        dataset = powerbi_client.get_powerbi_dataset(workspace_id=workspace_id, dataset_name=report_name)
        
        # Get Gold lakehouse details and check SQL endpoint status
        try:
            gold_lakehouse = fabric_client.get_lakehouse(workspace_id=workspace_id, lakehouse_id=fabric_lakehouses[udff_lakehouse_gold_name]['id'])
            sql_endpoint_provisioning_status = gold_lakehouse['properties']['sqlEndpointProperties']['provisioningStatus']
            print(f"    📋 SQL endpoint status: {sql_endpoint_provisioning_status}")
            
            if sql_endpoint_provisioning_status == 'Success':
                # SQL endpoint is ready - proceed with dataset parameter updates
                sql_endpoint = gold_lakehouse['properties']['sqlEndpointProperties']['connectionString']
                database_name = udff_lakehouse_gold_name
                
                print(f"    📋 Updating dataset parameters:")
                print(f"      • SQL Endpoint: {sql_endpoint}")
                print(f"      • Database: {database_name}")
                
                powerbi_client.update_powerbi_dataset_parameters(dataset_id=dataset['id'], parameters=[
                    {"name": "sqlEndpoint", "newValue": sql_endpoint},
                    {"name": "database", "newValue": database_name}
                ])
                print(f"  ✅ Dataset parameters updated successfully for '{report_name}'")
            else:
                # Handle non-success status
                print(f"  ❌ ERROR: SQL endpoint not ready (status: {sql_endpoint_provisioning_status})")
                print(f"     Manual intervention required: Wait for SQL endpoint provisioning to complete and re-run script")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ ERROR: Failed to configure dataset parameters for '{report_name}': {str(e)}")
            print(f"   Solution: Check lakehouse availability and Power BI permissions")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to deploy report '{report_name}': {str(e)}")
        print(f"   Solution: Verify the .pbix file is valid and you have upload permissions")
        sys.exit(1)


##################
# End of program #
##################

print("-" * 60)
print(f"🎉 {solution_name} deployment completed successfully!")
print(f"✅ Workspace: {workspace_name}")
print(f"✅ Lakehouses: {len(udff_lakehouses)} created (Bronze, Silver, Gold)")
print(f"✅ Notebooks: {uploaded_count}/{len(notebook_specs)} deployed with batch processing")
print(f"✅ Sample data: {len(csv_file_paths)} files uploaded")
print(f"✅ Pipelines: {len(successful_executions)} executed successfully with optimized monitoring")
print(f"✅ Power BI Reports: {len(deployed_reports)} deployed")
if deployed_reports:
    for report in deployed_reports:
        print(f"   📊 {report['name']} (ID: {report['id']})")
print("-" * 60)
