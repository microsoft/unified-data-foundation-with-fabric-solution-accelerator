#!/usr/bin/env python3
"""
UDF Jobs Execution Module

This module provides notebook execution functionality 
for the Unified Data Foundation solution.
"""
import os
import sys
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError


def schedule_notebook_jobs_sequential(workspace_client: FabricWorkspaceApiClient,
                                     notebook_specs: list,
                                     monitor_interval: int = 20) -> dict:
    """
    Execute notebooks sequentially with monitoring.
    
    Args:
        workspace_client: Authenticated workspace API client
        notebook_specs: List of dicts with 'name' and 'id' keys for notebooks to execute
        monitor_interval: Seconds to wait between status checks (default: 20)
        
    Returns:
        dict: Dictionary mapping notebook IDs to execution results
    """
    print(f"🚀 Executing data transformation pipelines sequentially")
    
    execution_results = {}
    successful_executions = []
    failed_executions = []
    
    for idx, spec in enumerate(notebook_specs, 1):
        notebook_name = spec.get('name', 'Unknown')
        notebook_id = spec.get('id')
        
        if not notebook_id:
            print(f"\n   [{idx}/{len(notebook_specs)}] Executing: {notebook_name}")
            print(f"      ⚠️  Warning: No notebook ID provided for '{notebook_name}', skipping")
            failed_executions.append(notebook_name)
            continue
        
        print(f"\n   [{idx}/{len(notebook_specs)}] Executing: {notebook_name}")
        
        try:
            # Schedule notebook job
            print(f"      ▶️  Scheduling job...")
            job_result = workspace_client.schedule_notebook_job(notebook_id, monitor_interval=monitor_interval)
            
            # Get execution status
            status = job_result.get('status', 'Unknown')
            duration = job_result.get('duration', 'N/A')
            
            print(f"      📊 Execution completed:")
            print(f"         Status: {status}")
            print(f"         Duration: {duration}")
            
            execution_results[notebook_id] = job_result
            
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
            execution_results[notebook_id] = {
                'status': 'Exception',
                'error': str(e)
            }
        except Exception as e:
            print(f"      ❌ Failed to execute {notebook_name}: {e}")
            failed_executions.append(notebook_name)
            execution_results[notebook_id] = {
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
    """Main function to execute notebooks."""
    
    parser = argparse.ArgumentParser(
        description="Execute notebooks in a Microsoft Fabric workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute a single notebook
  python udf_jobs.py --workspace-id "12345678-1234-1234-1234-123456789012" --notebook-specs '[{"notebook_id": "87654321-4321-4321-4321-210987654321", "notebook_name": "MyNotebook"}]'
  
  # Execute multiple notebooks
  python udf_jobs.py --workspace-id "12345678-1234-1234-1234-123456789012" --notebook-specs '[{"notebook_id": "id1", "notebook_name": "Notebook1"}, {"notebook_id": "id2", "notebook_name": "Notebook2"}]' --monitor-interval 30
        """
    )
    
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="ID of the workspace"
    )
    
    parser.add_argument(
        "--notebook-specs",
        required=True,
        help="JSON array of notebook specifications with 'name' and 'id' keys"
    )
    
    parser.add_argument(
        "--monitor-interval",
        type=int,
        default=20,
        help="Seconds to wait between status checks (default: 20)"
    )
    
    args = parser.parse_args()
    
    try:
        from fabric_api import FabricWorkspaceApiClient, FabricApiError
        import json
        
        workspace_client = FabricWorkspaceApiClient(workspace_id=args.workspace_id)
        
        # Parse notebook specs from JSON
        try:
            notebook_specs = json.loads(args.notebook_specs)
            if not isinstance(notebook_specs, list):
                raise ValueError("notebook_specs must be a JSON array")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format for notebook_specs: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        
        # Execute notebooks
        execution_results = schedule_notebook_jobs_sequential(
            workspace_client=workspace_client,
            notebook_specs=notebook_specs,
            monitor_interval=args.monitor_interval
        )
        
        print(f"\n🎉 Final Results:")
        print(f"   Notebooks: {len(notebook_specs)} executed")
        print(f"   Workspace ID: {args.workspace_id}")
        for spec in notebook_specs:
            notebook_name = spec.get('name', 'Unknown')
            notebook_id = spec.get('id')
            status = execution_results.get(notebook_id, {}).get('status', 'Unknown')
            print(f"   - {notebook_name}: {status}")
        
    except FabricApiError as e:
        print(f"❌ Fabric API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
