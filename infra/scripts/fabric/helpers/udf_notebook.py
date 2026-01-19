#!/usr/bin/env python3
"""
UDF Notebook Setup Module

This module provides notebook deployment and execution functionality 
for the Unified Data Foundation solution.
"""

import sys
import os
import json
import base64
import time
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError
from helpers.utils import read_file_content


def deploy_notebooks(workspace_client: FabricWorkspaceApiClient,
                    notebook_specs: list,
                    lakehouses: dict) -> dict:
    """
    Deploy notebooks to a Fabric workspace with lakehouse associations.
    
    Args:
        workspace_client: Authenticated workspace API client
        notebook_specs: List of notebook specifications, each containing:
            - path: Path to the notebook file
            - source_lakehouse: Optional source lakehouse name
            - target_lakehouse: Optional target lakehouse name
            - folder_path: Folder path in workspace
        lakehouses: Dictionary mapping lakehouse names to lakehouse objects
        
    Returns:
        dict: Dictionary mapping notebook names to notebook objects
        
    Raises:
        FabricApiError: If notebook deployment fails
    """
    print(f"📓 Deploying notebooks to workspace")
    
    # Get existing notebooks (returns dict of {name: id})
    print(f"   Retrieving existing notebooks...")
    existing_notebook_ids = workspace_client.list_notebooks()
    print(f"   Found {len(existing_notebook_ids)} existing notebooks")
    
    notebooks = {}
    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Process each notebook
    total_notebooks = len(notebook_specs)
    for idx, spec in enumerate(notebook_specs, 1):
        local_path = spec.get('path') or spec.get('local_path')  # Support both key names
        source_lakehouse_name = spec.get('source_lakehouse') or spec.get('source_lakehouse_name')
        target_lakehouse_name = spec.get('target_lakehouse') or spec.get('target_lakehouse_name')
        folder_path = spec.get('folder_path', '')
        folder_id = spec.get('folder_id')
        
        if not local_path:
            print(f"   [{idx}/{total_notebooks}] ❌ Skipping: Missing notebook path in spec")
            failed_count += 1
            continue
            
        notebook_name = os.path.splitext(os.path.basename(local_path))[0]
        
        try:
            print(f"   [{idx}/{total_notebooks}] Processing: {notebook_name}")
            
            # Read notebook content
            notebook_content = read_file_content(local_path)
            notebook_json = json.loads(notebook_content)
            
            # Add lakehouse connections if specified
            if source_lakehouse_name or target_lakehouse_name:
                lakehouse_refs = []
                
                if source_lakehouse_name and lakehouses:
                    source_lh = lakehouses.get(source_lakehouse_name)
                    if source_lh and isinstance(source_lh, dict) and 'id' in source_lh:
                        lakehouse_refs.append({
                            "id": source_lh['id'],
                            "workspaceId": workspace_client.workspace_id
                        })
                
                if target_lakehouse_name and target_lakehouse_name != source_lakehouse_name and lakehouses:
                    target_lh = lakehouses.get(target_lakehouse_name)
                    if target_lh and isinstance(target_lh, dict) and 'id' in target_lh:
                        lakehouse_refs.append({
                            "id": target_lh['id'],
                            "workspaceId": workspace_client.workspace_id
                        })
                
                if lakehouse_refs:
                    if 'metadata' not in notebook_json:
                        notebook_json['metadata'] = {}
                    
                    notebook_json['metadata']['dependencies'] = {
                        "lakehouse": {
                            "default_lakehouse": lakehouse_refs[0]['id'] if lakehouse_refs else None,
                            "default_lakehouse_name": target_lakehouse_name or source_lakehouse_name,
                            "default_lakehouse_workspace_id": workspace_client.workspace_id,
                            "known_lakehouses": lakehouse_refs
                        }
                    }
            
            # Encode notebook as base64
            notebook_base64 = base64.b64encode(
                json.dumps(notebook_json).encode('utf-8')
            ).decode('utf-8')
            
            # Prepare notebook data for API
            notebook_data = {
                "displayName": notebook_name,
                "definition": {
                    "format": "ipynb",
                    "parts": [{
                        "path": "notebook-content.ipynb",
                        "payload": notebook_base64,
                        "payloadType": "InlineBase64"
                    }]
                }
            }
            
            # Add folder ID if specified
            if folder_id:
                notebook_data["folderId"] = folder_id
            
            # Check if notebook exists
            if notebook_name in existing_notebook_ids:
                # Update existing notebook
                notebook_id = existing_notebook_ids[notebook_name]
                response = workspace_client.update_notebook(
                    notebook_id,
                    notebook_data,
                    wait_for_lro=True
                )
                # Store notebook object with ID
                notebooks[notebook_name] = {'id': notebook_id, 'displayName': notebook_name}
                print(f"      ✅ Updated: {notebook_name}")
                updated_count += 1
            else:
                # Create new notebook
                response = workspace_client.create_notebook(
                    notebook_data,
                    wait_for_lro=True
                )
                # Extract notebook ID from response
                if response.ok:
                    response_data = response.json()
                    notebook_id = response_data.get('id', 'unknown')
                    notebooks[notebook_name] = {'id': notebook_id, 'displayName': notebook_name}
                    print(f"      ✅ Created: {notebook_name}")
                    created_count += 1
                else:
                    raise FabricApiError(f"Failed to create notebook: {response.text}")
                
        except FileNotFoundError as e:
            print(f"      ❌ Notebook file not found: {notebook_name} - {e}")
            failed_count += 1
        except json.JSONDecodeError as e:
            print(f"      ❌ Invalid notebook JSON format: {notebook_name} - {e}")
            failed_count += 1
        except FabricApiError as e:
            print(f"      ❌ Fabric API error deploying {notebook_name}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"      ❌ Failed to deploy {notebook_name}: {e}")
            failed_count += 1
    
    print(f"   ✅ Notebook deployment complete:")
    print(f"      Created: {created_count}")
    print(f"      Updated: {updated_count}")
    if failed_count > 0:
        print(f"      Failed: {failed_count}")
    
    return notebooks


def execute_notebooks_sequential(workspace_client: FabricWorkspaceApiClient,
                                notebook_names: list,
                                notebooks: dict,
                                monitor_interval: int = 20) -> dict:
    """
    Execute notebooks sequentially with monitoring.
    
    Args:
        workspace_client: Authenticated workspace API client
        notebook_names: List of notebook names to execute in order
        notebooks: Dictionary mapping notebook names to notebook objects
        monitor_interval: Seconds to wait between status checks (default: 20)
        
    Returns:
        dict: Dictionary mapping notebook names to execution results
    """
    print(f"🚀 Executing data transformation pipelines sequentially")
    
    execution_results = {}
    successful_executions = []
    failed_executions = []
    
    for idx, notebook_name in enumerate(notebook_names, 1):
        print(f"\n   [{idx}/{len(notebook_names)}] Executing: {notebook_name}")
        
        # Get notebook ID
        notebook = notebooks.get(notebook_name)
        if not notebook:
            print(f"      ❌ Notebook not found: {notebook_name}")
            failed_executions.append(notebook_name)
            execution_results[notebook_name] = {
                'status': 'NotFound',
                'error': 'Notebook not found in deployed notebooks'
            }
            continue
        
        notebook_id = notebook.get('id')
        if not notebook_id:
            print(f"      ❌ Could not get notebook ID for: {notebook_name}")
            failed_executions.append(notebook_name)
            execution_results[notebook_name] = {
                'status': 'Error',
                'error': 'Could not retrieve notebook ID'
            }
            continue
        
        try:
            # Schedule notebook job
            print(f"      ▶️  Scheduling job...")
            job_result = workspace_client.schedule_notebook_job(notebook_id)
            
            # Get execution status
            status = job_result.get('status', 'Unknown')
            duration = job_result.get('duration', 'N/A')
            
            print(f"      📊 Execution completed:")
            print(f"         Status: {status}")
            print(f"         Duration: {duration}")
            
            execution_results[notebook_name] = job_result
            
            if status == 'Completed':
                print(f"      ✅ Successfully executed: {notebook_name}")
                successful_executions.append(notebook_name)
            else:
                print(f"      ❌ Execution failed: {notebook_name}")
                if 'error' in job_result:
                    print(f"         Error: {job_result.get('error')}")
                failed_executions.append(notebook_name)
                
        except FabricApiError as e:
            print(f"      ❌ Fabric API error executing {notebook_name}: {e}")
            failed_executions.append(notebook_name)
            execution_results[notebook_name] = {
                'status': 'Exception',
                'error': str(e)
            }
        except Exception as e:
            print(f"      ❌ Failed to execute {notebook_name}: {e}")
            failed_executions.append(notebook_name)
            execution_results[notebook_name] = {
                'status': 'Exception',
                'error': str(e)
            }
    
    # Print summary
    print(f"\n   ✅ Notebook execution complete:")
    print(f"      Successful: {len(successful_executions)}")
    print(f"      Failed: {len(failed_executions)}")
    
    if failed_executions:
        print(f"\n   ⚠️  Failed notebooks:")
        for notebook_name in failed_executions:
            print(f"      - {notebook_name}")
    
    return execution_results


def main():
    """Main function to deploy and execute notebooks."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy notebooks to a Microsoft Fabric workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy a single notebook
  python udf_notebook.py --workspace-id "12345678-1234-1234-1234-123456789012" --notebook-path "path/to/notebook.ipynb" --notebook-name "MyNotebook"
  
  # Deploy notebook with lakehouse
  python udf_notebook.py --workspace-id "12345678-1234-1234-1234-123456789012" --notebook-path "path/to/notebook.ipynb" --notebook-name "MyNotebook" --lakehouse-name "MyLakehouse" --lakehouse-id "87654321-4321-4321-4321-210987654321"
        """
    )
    
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="ID of the workspace"
    )
    
    parser.add_argument(
        "--notebook-path",
        required=True,
        help="Local path to the notebook file"
    )
    
    parser.add_argument(
        "--notebook-name",
        help="Name for the notebook in Fabric (defaults to filename)"
    )
    
    parser.add_argument(
        "--lakehouse-name",
        help="Optional lakehouse name to associate with notebook"
    )
    
    parser.add_argument(
        "--lakehouse-id",
        help="Optional lakehouse ID (required if lakehouse-name is specified)"
    )
    
    parser.add_argument(
        "--folder-id",
        help="Optional folder ID where to create the notebook"
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the notebook after deployment"
    )
    
    args = parser.parse_args()
    
    try:
        from fabric_api import FabricWorkspaceApiClient, FabricApiError
        
        workspace_client = FabricWorkspaceApiClient(workspace_id=args.workspace_id)
        
        # Determine notebook name
        notebook_name = args.notebook_name or os.path.splitext(os.path.basename(args.notebook_path))[0]
        
        # Prepare lakehouse dictionary
        lakehouses = {}
        if args.lakehouse_name and args.lakehouse_id:
            lakehouses[args.lakehouse_name] = {
                'id': args.lakehouse_id,
                'displayName': args.lakehouse_name
            }
        
        # Prepare notebook spec (use 'path' to match create_fabric_items.py)
        notebook_specs = [{
            'path': args.notebook_path,
            'source_lakehouse': args.lakehouse_name,
            'target_lakehouse': args.lakehouse_name,
            'folder_path': '',
            'folder_id': args.folder_id
        }]
        
        # Deploy notebook
        notebooks = deploy_notebooks(
            workspace_client=workspace_client,
            notebook_specs=notebook_specs,
            lakehouses=lakehouses
        )
        
        # Execute if requested
        if args.execute:
            execute_notebooks_sequential(
                workspace_client=workspace_client,
                notebook_names=[notebook_name],
                notebooks=notebooks
            )
        
        print(f"\n🎉 Final Results:")
        print(f"   Notebook: {notebook_name}")
        print(f"   Workspace ID: {args.workspace_id}")
        if args.execute:
            print(f"   Execution: Completed")
        
    except FabricApiError as e:
        print(f"❌ Fabric API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
