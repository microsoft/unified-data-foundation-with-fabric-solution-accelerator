#!/usr/bin/env python3
"""
Unified Data Foundation Deployment Orchestrator

This script coordinates the execution of all deployment steps for the Unified Data Foundation
solution to Microsoft Fabric in the correct order, with proper error handling and logging.

Functions executed in order:
1. setup_workspace - Create and configure Fabric workspace
2. setup_workspace_administrators - Add workspace administrators
3. setup_folder_structure - Create folder structure in workspace
4. setup_lakehouses - Create Bronze, Silver, and Gold lakehouses
5. load_csv_data_to_lakehouse - Load sample data into Bronze lakehouse
6. deploy_notebooks - Deploy and configure notebooks with lakehouse connections
7. setup_environment - Create Fabric Environment with custom libraries
8. setup_data_agent_lakehouse - Create and configure Data Agent with Lakehouse data source
9. execute_notebooks_sequential - Run data transformation pipelines

Usage:
    python deploy_udf_solution.py

Environment Variables:
    AZURE_FABRIC_CAPACITY_NAME - The name of the Fabric capacity resource
    AZURE_SOLUTION_SUFFIX - The solution name suffix used for resource naming
    AZURE_FABRIC_WORKSPACE_NAME - Custom name for the Fabric workspace (optional)
    AZURE_FABRIC_ADMIN_MEMBERS - JSON array of workspace administrator identities (optional)
    AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID - JSON array of administrator object IDs (optional)
"""

import os
import sys
from datetime import datetime

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(__file__))

# Import Fabric API clients
from fabric_api import create_fabric_client, create_workspace_fabric_client, FabricApiError
from graph_api import create_graph_client, GraphApiError

# Import helper modules
from helpers.utils import get_required_env_var, print_step, print_steps_summary
from helpers.udf_workspace import setup_workspace
from helpers.udf_workspace_admins import setup_workspace_administrators
from helpers.udf_folder import setup_folder_structure
from helpers.udf_lakehouse import setup_lakehouses, load_csv_data_to_lakehouse
from helpers.udf_notebook import deploy_notebooks, execute_notebooks_sequential
from helpers.udf_environment import setup_environment
from helpers.udf_data_agent import setup_data_agent_lakehouse


def main():
    """Main function to deploy the Unified Data Foundation solution."""
    
    # Variables set up
    solution_name = "Unified Data Foundation"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # Load configuration from environment variables
    capacity_name = get_required_env_var("AZURE_FABRIC_CAPACITY_NAME")
    solution_suffix = get_required_env_var("AZURE_SOLUTION_SUFFIX")
    
    # Optional environment variables with defaults
    workspace_name = os.getenv("AZURE_FABRIC_WORKSPACE_NAME", f"{solution_name} - {solution_suffix}")
    fabric_admins_str = os.getenv("AZURE_FABRIC_ADMIN_MEMBERS")
    fabric_admins_by_object_id_str = os.getenv("AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID")
    
    # Process admin lists from environment variables
    fabric_admins = []
    fabric_admins_by_object_id = []
    
    if fabric_admins_str:
        try:
            import json
            fabric_admins = json.loads(fabric_admins_str)
        except json.JSONDecodeError:
            print(f"⚠️  Warning: Failed to parse AZURE_FABRIC_ADMIN_MEMBERS as JSON")
    
    if fabric_admins_by_object_id_str:
        try:
            import json
            fabric_admins_by_object_id = json.loads(fabric_admins_by_object_id_str)
        except json.JSONDecodeError:
            print(f"⚠️  Warning: Failed to parse AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID as JSON")
    
    # Show deployment summary
    print(f"🏭 {solution_name} Initialization")
    print("="*60)
    print(f"Capacity: {capacity_name}")
    print(f"Workspace: {workspace_name}")
    print(f"Solution Suffix: {solution_suffix}")
    if fabric_admins:
        print(f"Fabric Admins: {', '.join(fabric_admins)}")
    if fabric_admins_by_object_id:
        print(f"Fabric Admins (by Object ID): {', '.join(fabric_admins_by_object_id)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Authenticate clients
    print("\n🔐 Authenticating clients...")
    try:
        fabric_client = create_fabric_client()
        print("✅ Fabric API client authenticated")
    except Exception as e:
        print(f"❌ Failed to authenticate Fabric API client: {e}")
        sys.exit(1)
    
    try:
        graph_client = create_graph_client()
        print("✅ Graph API client authenticated")
    except Exception as e:
        print(f"❌ Failed to authenticate Graph API client: {e}")
        sys.exit(1)
    
    executed_steps = []
    
    # Step 1: Setup workspace
    print_step(1, 9, "Setting up Fabric workspace and capacity assignment", 
               capacity_name=capacity_name, workspace_name=workspace_name)
    try:
        workspace_id = setup_workspace(
            fabric_client=fabric_client,
            capacity_name=capacity_name,
            workspace_name=workspace_name
        )
        print(f"✅ Successfully completed: setup_workspace")
        executed_steps.append("setup_workspace")
    except Exception as e:
        print(f"❌ Exception while executing setup_workspace: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Create workspace-specific client for subsequent operations
    print("\n🔐 Creating workspace-specific Fabric API client...")
    try:
        workspace_client = create_workspace_fabric_client(workspace_id)
        print("✅ Workspace-specific authentication successful")
    except Exception as e:
        print(f"❌ Failed to create workspace-specific client: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 2: Setup workspace administrators
    print_step(2, 9, "Setting up Fabric workspace administrators", 
               workspace_id=workspace_id)
    try:
        admin_result = setup_workspace_administrators(
            workspace_client=workspace_client,
            fabric_admins=fabric_admins,
            fabric_admins_by_object_id=fabric_admins_by_object_id,
            fabric_client=fabric_client,
            graph_client=graph_client
        )
        print(f"✅ Successfully completed: setup_workspace_administrators")
        executed_steps.append("setup_workspace_administrators")
    except Exception as e:
        print(f"❌ Exception while executing setup_workspace_administrators: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 3: Setup folder structure
    folder_paths = [
        'lakehouses',
        'notebooks/bronze_to_silver',
        'notebooks/data_management',
        'notebooks/schema',
        'notebooks/silver_to_gold',
        'reports',
        'environment'
    ]
    
    print_step(3, 9, "Setting up folder structure", folder_count=len(folder_paths))
    try:
        fabric_folders = setup_folder_structure(
            workspace_client=workspace_client,
            folder_paths=folder_paths
        )
        print(f"✅ Successfully completed: setup_folder_structure")
        executed_steps.append("setup_folder_structure")
    except Exception as e:
        print(f"❌ Exception while executing setup_folder_structure: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 4: Setup lakehouses
    lakehouse_names = {
        'maag_bronze',
        'maag_silver',
        'maag_gold'
    }
    lakehouse_folder_id = fabric_folders.get('lakehouses')
    
    print_step(4, 9, "Setting up lakehouses", lakehouse_count=len(lakehouse_names))
    try:
        fabric_lakehouses = setup_lakehouses(
            workspace_client=workspace_client,
            lakehouse_names=lakehouse_names,
            lakehouse_folder_id=lakehouse_folder_id
        )
        print(f"✅ Successfully completed: setup_lakehouses")
        executed_steps.append("setup_lakehouses")
    except Exception as e:
        print(f"❌ Exception while executing setup_lakehouses: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 5: Load CSV data to bronze lakehouse
    csv_folder_path = os.path.join(repo_root, 'infra', 'data')
    bronze_lakehouse = fabric_lakehouses['maag_bronze']
    
    print_step(5, 9, "Loading sample data to bronze lakehouse", 
               csv_folder=csv_folder_path)
    try:
        upload_result = load_csv_data_to_lakehouse(
            workspace_client=workspace_client,
            bronze_lakehouse=bronze_lakehouse,
            csv_folder_path=csv_folder_path
        )
        print(f"✅ Successfully completed: load_csv_data_to_lakehouse")
        executed_steps.append("load_csv_data_to_lakehouse")
    except Exception as e:
        print(f"❌ Exception while executing load_csv_data_to_lakehouse: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 6: Deploy notebooks
    notebooks_directory = os.path.join(repo_root, 'src', 'fabric', 'notebooks')
    
    # Build notebook specifications
    notebook_specs = [
        {
            'local_path': os.path.join(notebooks_directory, 'run_bronze_to_silver.ipynb'),
            'source_lakehouse_name': None,
            'target_lakehouse_name': 'maag_silver',
            'folder_path': 'notebooks',
            'folder_id': fabric_folders.get('notebooks/bronze_to_silver')
        },
        {
            'local_path': os.path.join(notebooks_directory, 'run_silver_to_gold.ipynb'),
            'source_lakehouse_name': None,
            'target_lakehouse_name': 'maag_gold',
            'folder_path': 'notebooks',
            'folder_id': fabric_folders.get('notebooks/silver_to_gold')
        },
        # Add more notebook specifications here...
        # (Bronze to Silver notebooks)
        {
            'local_path': os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_account.ipynb'),
            'source_lakehouse_name': 'maag_bronze',
            'target_lakehouse_name': 'maag_silver',
            'folder_path': 'notebooks/bronze_to_silver',
            'folder_id': fabric_folders.get('notebooks/bronze_to_silver')
        },
        # ... (add all other notebooks)
    ]
    
    print_step(6, 9, "Deploying notebooks", notebook_count=len(notebook_specs))
    try:
        fabric_notebooks = deploy_notebooks(
            workspace_client=workspace_client,
            notebook_specs=notebook_specs,
            lakehouses=fabric_lakehouses
        )
        print(f"✅ Successfully completed: deploy_notebooks")
        executed_steps.append("deploy_notebooks")
    except Exception as e:
        print(f"❌ Exception while executing deploy_notebooks: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 7: Setup environment
    environment_name = "Data Agent Environment"
    environment_yml_path = os.path.join(repo_root, "src", "fabric", "definitions", 
                                       "environment", "Libraries", "PublicLibraries", "environment.yml")
    environment_folder_id = fabric_folders.get('environment')
    
    print_step(7, 9, "Setting up Fabric environment", 
               environment_name=environment_name)
    try:
        environment_info = setup_environment(
            workspace_client=workspace_client,
            environment_name=environment_name,
            environment_yml_path=environment_yml_path if os.path.exists(environment_yml_path) else None,
            folder_id=environment_folder_id
        )
        environment_id = environment_info.get('id')
        print(f"✅ Successfully completed: setup_environment")
        executed_steps.append("setup_environment")
    except Exception as e:
        print(f"❌ Exception while executing setup_environment: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Step 8: Setup data agent
    if environment_info:
        data_agent_name = "Unified Data Agent"
        gold_lakehouse = fabric_lakehouses['maag_gold']
        gold_lakehouse_id = gold_lakehouse.get('id')
        
        # Get list of tables to include in data agent
        selected_tables = [
            'shared_customer',
            'shared_product',
            'sales_order',
            'sales_order_line',
            'finance_account',
            'finance_invoice'
        ]
        
        notebook_name = f"Configure Data Agent - {data_agent_name}"
        
        print_step(8, 9, "Setting up Data Agent", 
                   data_agent_name=data_agent_name,
                   lakehouse_id=gold_lakehouse_id)
        try:
            data_agent_result = setup_data_agent_lakehouse(
                workspace_client=workspace_client,
                data_agent_name=data_agent_name,
                lakehouse_id=gold_lakehouse_id,
                lakehouse_workspace_id=workspace_id,
                environment_id=environment_id,
                selected_tables=selected_tables,
                notebook_name=notebook_name,
                notebook_folder_id=environment_folder_id,
                data_agent_folder_id=environment_folder_id
            )
            print(f"✅ Successfully completed: setup_data_agent_lakehouse")
            executed_steps.append("setup_data_agent_lakehouse")
        except Exception as e:
            print(f"⚠️  Warning: Data Agent setup failed: {e}")
            print(f"   Data Agent is a preview feature and may not be available in all regions")
            print(f"   You can set up the Data Agent manually following the documentation")
    else:
        print(f"ℹ️  Skipping Data Agent setup (environment not created)")
    
    # Step 9: Execute notebooks
    notebooks_to_run = [
        'run_bronze_to_silver',
        'run_silver_to_gold'
    ]
    
    print_step(9, 9, "Executing data transformation pipelines", 
               notebook_count=len(notebooks_to_run))
    try:
        execution_results = execute_notebooks_sequential(
            workspace_client=workspace_client,
            notebook_names=notebooks_to_run,
            notebooks=fabric_notebooks,
            monitor_interval=20
        )
        print(f"✅ Successfully completed: execute_notebooks_sequential")
        executed_steps.append("execute_notebooks_sequential")
    except Exception as e:
        print(f"❌ Exception while executing notebooks: {e}")
        print_steps_summary(solution_name, solution_suffix, executed_steps, [])
        sys.exit(1)
    
    # Success!
    print(f"\n🎉 {solution_name} deployment completed successfully!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_steps_summary(solution_name, solution_suffix, executed_steps)
    
    # Print resource URLs
    workspace_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}?experience=fabric-developer"
    
    print(f"\n" + "="*60)
    print(f"🎉 {solution_name.upper()} DEPLOYMENT COMPLETE!")
    print(f"="*60)
    print(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏷️  Solution: {solution_suffix}")
    
    print(f"\n✅ DEPLOYED RESOURCES:")
    print(f"   🏠 Workspace:     {workspace_name}")
    print(f"   🏛️  Lakehouses:    {', '.join(lakehouse_names)}")
    print(f"   📓 Notebooks:     {len(fabric_notebooks)} deployed")
    print(f"   🌍 Environment:   {environment_name}")
    if 'setup_data_agent_lakehouse' in executed_steps:
        print(f"   🤖 Data Agent:    {data_agent_name} (✅ Configured)")
    
    print(f"\n📦 FABRIC URLS:")
    print(f"   🏠 Workspace:     {workspace_url}")
    
    print(f"\n✨ Your unified data foundation is ready!")
    print(f"="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
