import os
import glob
import time
import argparse
import sys
import json
import base64
import re
from typing import Dict, List, Optional, Any
from azure.identity import AzureCliCredential
from fabric_api import create_fabric_client, FabricApiError
from powerbi_api import *

solution_name = "Unified Data Foundation with Fabric"

####################
# Helper Functions #
####################

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
            print(f"  ❌ Error creating directory {full_path}: {str(e)}")

##########################
# Command line arguments #
##########################

# Parse command line arguments
parser = argparse.ArgumentParser(description=f'Deploy {solution_name} to Microsoft Fabric')
parser.add_argument('--workspaceId', required=True, help='Microsoft Fabric workspace ID')
args = parser.parse_args()

print(f"🚀 Starting {solution_name} deployment to Microsoft Fabric")
print(f"📋 Target workspace ID: {args.workspaceId}")
print("-" * 60)

####################
# Variables set up #
####################

workspace_id = args.workspaceId
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))  # Go up three levels from infra/deploy/fabric to repo root

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
    # Get workspace info using the new API client
    workspaces = fabric_client.get_workspaces()
    workspace = next((w for w in workspaces if w['id'] == workspace_id), None)
    
    if not workspace:
        print(f"❌ ERROR: Workspace '{workspace_id}' not found")
        print("   Solution: Verify the workspace ID and ensure you have access")
        sys.exit(1)
    
    workspace_name = workspace['displayName']
    print(f"✅ Connected to workspace: '{workspace_name}'")
    
except FabricApiError as e:
    if e.status_code == 404:
        print(f"❌ ERROR: Workspace '{workspace_id}' not found")
        print("   Solution: Verify the workspace ID and ensure you have access")
    elif e.status_code == 403:
        print(f"❌ ERROR: Access denied to workspace '{workspace_id}'")
        print("   Solution: Ensure you have Contributor or Admin permissions")
    else:
        print(f"❌ ERROR: Failed to access workspace: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error accessing workspace: {str(e)}")
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
    fabric_folders = {}
    
    # Get existing folders
    existing_folders = fabric_client.get_folders(workspace_id)
    fabric_folders = fabric_client._build_folder_path_mapping(existing_folders)
    
    # Create hierarchy of folders based on full path
    for udff_folder_path in udff_fabric_folders:
        if udff_folder_path in fabric_folders:
            print(f"  📁 Folder '{udff_folder_path}' already exists")
        else:
            try:
                folder_id = fabric_client.create_folder_hierarchy(workspace_id, udff_folder_path)
                fabric_folders[udff_folder_path] = folder_id
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
    # Get existing lakehouses
    lakehouses = fabric_client.get_items(workspace_id, item_type="Lakehouse")
    for lakehouse in lakehouses:
        fabric_lakehouses[lakehouse['displayName']] = lakehouse

    # Create UDFF lakehouses
    for lakehouse_name in udff_lakehouses:
        if lakehouse_name in fabric_lakehouses:
            print(f"  🏠 Lakehouse '{lakehouse_name}' already exists")
        else:
            print(f"  🏗️ Creating lakehouse '{lakehouse_name}'")
            lakehouse_data = {
                "displayName": lakehouse_name,
                "type": "Lakehouse",
                "creationPayload": {
                    "enableSchemas": True
                }
            }
            if lakehouse_folder_id:
                lakehouse_data["folderId"] = lakehouse_folder_id
            
            try:
                # Use the API client's internal _make_request method for lakehouse creation
                response = fabric_client._make_request(f"workspaces/{workspace_id}/lakehouses", method="POST", data=lakehouse_data)
                
                if response.status_code == 201:
                    print(f"  ✅ Lakehouse '{lakehouse_name}' created successfully")
                    fabric_lakehouses[lakehouse_name] = response.json()
                else:
                    print(f"❌ ERROR: Unexpected response creating lakehouse '{lakehouse_name}'")
                    sys.exit(1)
            except Exception as e:
                print(f"❌ ERROR: Failed to create lakehouse '{lakehouse_name}': {str(e)}")
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
        print(f"  ⚠️ Failed to get existing notebooks: {str(e)}")
        existing_notebooks = {}
    
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
            print(f"  ❌ Folder not found for path '{folder_path}', skipping '{notebook_name}'")
            continue
        
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
                print(f"  ❌ Failed to upload '{notebook_name}': {response.text}")
                
        except Exception as e:
            print(f"  ❌ Error uploading '{notebook_name}': {str(e)}")
    
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
                    # Other errors, continue monitoring unless timeout
                    if time.time() - job['start_time'] > max_wait_time:
                        print(f"    ⚠️ Upload job for '{job['notebook_name']}' failed: {str(e)}")
                        jobs_to_remove.append(job)
            
            for job in jobs_to_remove:
                pending_jobs.remove(job)

            if pending_jobs:
                time.sleep(check_interval)
                
    # Refresh notebooks list
    try:
        final_notebooks = fabric_client.get_notebooks(workspace_id)
        fabric_notebooks.update(final_notebooks)
    except Exception:
        pass
    
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
        time.sleep(2)

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
    except Exception as e:
        print(f"❌ ERROR: Failed to deploy report '{report_name}': {str(e)}")
        print(f"   Solution: Verify the .pbix file is valid and you have upload permissions")
        sys.exit(1)

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
