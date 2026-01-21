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
    Deploy notebooks to a Fabric workspace with lakehouse associations using batch processing.
    
    Args:
        workspace_client: Authenticated workspace API client
        notebook_specs: List of notebook specifications, each containing:
            - path or notebook_local_path: Path to the notebook file
            - source_lakehouse or source_lakehouse_name: Optional source lakehouse name
            - target_lakehouse or target_lakehouse_name: Optional target lakehouse name
            - fabric_folder_id: Optional folder ID where to create the notebook
        lakehouses: Dictionary mapping lakehouse names to lakehouse objects
        
    Returns:
        dict: Dictionary mapping notebook names (displayName) to notebook IDs
        
    Raises:
        FabricApiError: If notebook deployment fails
        ValueError: If notebook spec is invalid or notebook JSON is malformed
        FileNotFoundError: If notebook file is not found
        TimeoutError: If notebook operations timeout
    """
    print(f"📓 Deploying notebooks to workspace using batch processing")
    
    # Get existing notebooks and create a mapping of {name: id}
    print(f"   Retrieving existing notebooks...")
    existing_notebooks = workspace_client.list_notebooks()
    existing_notebook_ids = {nb['displayName']: nb['id'] for nb in existing_notebooks}
    print(f"   Found {len(existing_notebook_ids)} existing notebooks")
    
    notebooks = {}
    upload_jobs = []  # Track LRO jobs for batch monitoring
    created_count = 0
    updated_count = 0
    
    # Process each notebook and submit jobs without waiting
    total_notebooks = len(notebook_specs)
    for idx, spec in enumerate(notebook_specs, 1):
        notebook_local_path = spec.get('notebook_local_path') 
        source_lakehouse_name = spec.get('source_lakehouse_name')
        target_lakehouse_name = spec.get('target_lakehouse_name')
        fabric_folder_id = spec.get('fabric_folder_id')
        
        if not notebook_local_path:
            error_msg = f"Missing notebook path in spec at index {idx}"
            print(f"   [{idx}/{total_notebooks}] ❌ {error_msg}")
            raise ValueError(error_msg)
            
        notebook_name = os.path.splitext(os.path.basename(notebook_local_path))[0]
        
        try:
            # Read notebook content
            notebook_content = read_file_content(notebook_local_path)
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
            
            # Submit create or update operation without waiting for LRO completion
            if notebook_name in existing_notebook_ids:
                # Update existing notebook
                notebook_id = existing_notebook_ids[notebook_name]
                print(f"   [{idx}/{total_notebooks}] Updating: {notebook_name}")
                response = workspace_client.update_notebook(
                    notebook_id,
                    notebook_base64,
                    wait_for_lro=False  # Don't wait, batch process instead
                )
                operation_type = 'update'
            else:
                # Create new notebook
                print(f"   [{idx}/{total_notebooks}] Creating: {notebook_name}")
                response = workspace_client.create_notebook(
                    notebook_name,
                    notebook_base64,
                    folder_id=fabric_folder_id,
                    wait_for_lro=False  # Don't wait, batch process instead
                )
                operation_type = 'create'
            
            # Track job for batch monitoring if LRO (status 202)
            if response.status_code == 202:
                job_monitoring_url = response.headers.get('Location')
                if job_monitoring_url:
                    upload_jobs.append({
                        'notebook_name': notebook_name,
                        'job_url': job_monitoring_url,
                        'operation_type': operation_type,
                        'start_time': time.time()
                    })
            elif response.ok:
                # Immediate success (no LRO)
                notebooks[notebook_name] = operation_type
                if operation_type == 'create':
                    created_count += 1
                else:
                    updated_count += 1
            else:
                raise FabricApiError(f"Failed to {operation_type} notebook: {response.text}")
                
        except FileNotFoundError as e:
            error_msg = f"Notebook file not found: {notebook_name}"
            print(f"      ❌ {error_msg} - {e}")
            raise FileNotFoundError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Invalid notebook JSON format: {notebook_name}"
            print(f"      ❌ {error_msg} - {e}")
            raise ValueError(error_msg) from e
        except FabricApiError as e:
            error_msg = f"Fabric API error deploying {notebook_name}: {e}"
            print(f"      ❌ {error_msg}")
            raise
        except Exception as e:
            error_msg = f"Failed to deploy {notebook_name}: {e}"
            print(f"      ❌ {error_msg}")
            raise
    
    # Wait for all LRO jobs to complete
    if upload_jobs:
        print(f"\n   ⏳ Waiting for {len(upload_jobs)} notebook operations to complete...")
        pending_jobs = upload_jobs.copy()
        start_time = time.time()
        max_wait_time = 600  # 10 minutes max
        check_interval = 5  # Check every 5 seconds
        
        while pending_jobs and (time.time() - start_time) < max_wait_time:
            jobs_to_remove = []
            
            for job in pending_jobs:
                try:
                    # Check job status using the workspace client
                    job_result = workspace_client.check_lro_job_status(job['job_url'])
                    
                    if job_result:
                        # Job completed successfully
                        notebooks[job['notebook_name']] = job['operation_type']
                        
                        print(f"      ✅ {job['operation_type'].capitalize()}d: {job['notebook_name']}")
                        
                        if job['operation_type'] == 'create':
                            created_count += 1
                        else:
                            updated_count += 1
                            
                        jobs_to_remove.append(job)
                        
                except Exception as e:
                    # Check if job has timed out
                    if time.time() - job['start_time'] > max_wait_time:
                        error_msg = f"Operation timed out for '{job['notebook_name']}': {str(e)}"
                        print(f"      ❌ {error_msg}")
                        raise TimeoutError(error_msg) from e
                    # Otherwise continue monitoring
            
            # Remove completed/failed jobs
            for job in jobs_to_remove:
                pending_jobs.remove(job)
            
            # Sleep before next check if there are still pending jobs
            if pending_jobs:
                time.sleep(check_interval)
        
        # Handle any remaining pending jobs that timed out
        if pending_jobs:
            timeout_notebooks = [job['notebook_name'] for job in pending_jobs]
            error_msg = f"{len(pending_jobs)} operations did not complete within timeout: {', '.join(timeout_notebooks)}"
            print(f"      ❌ {error_msg}")
            raise TimeoutError(error_msg)
    
    
    print(f"\n   ✅ Notebook deployment complete:")
    print(f"      Created: {created_count}")
    print(f"      Updated: {updated_count}")
    
    # Retrieve all notebooks to get IDs and create name-to-id mapping
    print(f"\n   📋 Retrieving notebook IDs from workspace...")
    all_notebooks = workspace_client.list_notebooks()
    notebook_id_map = {nb['displayName']: nb['id'] for nb in all_notebooks}
    print(f"   Retrieved {len(notebook_id_map)} notebook IDs")
    
    return notebook_id_map





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
            'fabric_folder_id': args.folder_id
        }]
        
        # Deploy notebook
        notebooks = deploy_notebooks(
            workspace_client=workspace_client,
            notebook_specs=notebook_specs,
            lakehouses=lakehouses
        )
        
        print(f"\n🎉 Final Results:")
        print(f"   Notebook: {notebook_name}")
        print(f"   Workspace ID: {args.workspace_id}")
        print(f"   Deployment: Completed")
        
    except FabricApiError as e:
        print(f"❌ Fabric API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
