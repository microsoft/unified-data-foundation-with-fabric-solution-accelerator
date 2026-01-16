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
            - local_path: Path to the notebook file
            - source_lakehouse_name: Optional source lakehouse name
            - target_lakehouse_name: Optional target lakehouse name
            - folder_path: Folder path in workspace
        lakehouses: Dictionary mapping lakehouse names to lakehouse objects
        
    Returns:
        dict: Dictionary mapping notebook names to notebook objects
        
    Raises:
        FabricApiError: If notebook deployment fails
    """
    print(f"📓 Deploying notebooks to workspace")
    
    # Get existing notebooks
    print(f"   Retrieving existing notebooks...")
    existing_notebooks = workspace_client.list_notebooks()
    existing_notebook_map = {nb['displayName']: nb for nb in existing_notebooks}
    print(f"   Found {len(existing_notebook_map)} existing notebooks")
    
    notebooks = {}
    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Process each notebook
    total_notebooks = len(notebook_specs)
    for idx, spec in enumerate(notebook_specs, 1):
        local_path = spec['local_path']
        source_lakehouse_name = spec.get('source_lakehouse_name')
        target_lakehouse_name = spec.get('target_lakehouse_name')
        folder_path = spec['folder_path']
        folder_id = spec.get('folder_id')
        
        notebook_name = os.path.splitext(os.path.basename(local_path))[0]
        
        try:
            print(f"   [{idx}/{total_notebooks}] Processing: {notebook_name}")
            
            # Read notebook content
            notebook_content = read_file_content(local_path)
            notebook_json = json.loads(notebook_content)
            
            # Add lakehouse connections if specified
            if source_lakehouse_name or target_lakehouse_name:
                lakehouse_refs = []
                
                if source_lakehouse_name:
                    source_lh = lakehouses.get(source_lakehouse_name)
                    if source_lh:
                        lakehouse_refs.append({
                            "id": source_lh['id'],
                            "workspaceId": workspace_client.workspace_id
                        })
                
                if target_lakehouse_name and target_lakehouse_name != source_lakehouse_name:
                    target_lh = lakehouses.get(target_lakehouse_name)
                    if target_lh:
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
            
            # Check if notebook exists
            if notebook_name in existing_notebook_map:
                # Update existing notebook
                notebook_id = existing_notebook_map[notebook_name]['id']
                workspace_client.update_notebook(
                    notebook_id,
                    notebook_name,
                    notebook_base64,
                    folder_id
                )
                notebooks[notebook_name] = existing_notebook_map[notebook_name]
                print(f"      ✅ Updated: {notebook_name}")
                updated_count += 1
            else:
                # Create new notebook
                notebook = workspace_client.create_notebook(
                    notebook_name,
                    notebook_base64,
                    folder_id
                )
                notebooks[notebook_name] = notebook
                print(f"      ✅ Created: {notebook_name}")
                created_count += 1
                
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
