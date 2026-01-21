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
7. schedule_notebook_jobs_sequential - Run data transformation pipelines
8. setup_environment - Create Fabric Environment with custom libraries
9. setup_data_agent - Create and configure Data Agent with Lakehouse data source

Usage:
    python deploy_udf_solution.py

Environment Variables:
    AZURE_FABRIC_CAPACITY_NAME - The name of the Fabric capacity resource
    AZURE_FABRIC_CAPACITY_ADMINISTRATORS - JSON array of capacity administrator identities (obtained in main.bicep)
    SOLUTION_SUFFIX - The solution name suffix used for resource naming
    FABRIC_WORKSPACE_NAME - Custom name for the Fabric workspace (optional)
    FABRIC_WORKSPACE_ADMINISTRATORS - Comma-separated list of workspace administrator identities (optional)
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(__file__))

# Import Fabric API clients
from fabric_api import create_fabric_client, create_workspace_fabric_client, FabricApiError
from graph_api import create_graph_client, GraphApiError
from powerbi_api import create_powerbi_client

# Import helper modules
from helpers.utils import get_required_env_var, print_step, print_steps_summary, build_notebook_spec
from helpers.udf_workspace import setup_workspace
from helpers.udf_workspace_admins import setup_workspace_administrators
from helpers.udf_folder import setup_folder_structure
from helpers.udf_lakehouse import setup_lakehouses, load_csv_data_to_lakehouse
from helpers.udf_notebook import deploy_notebooks
from helpers.udf_jobs import schedule_notebook_jobs_sequential
from helpers.udf_powerbi import deploy_powerbi_reports
from helpers.udf_environment import setup_environment
from helpers.udf_data_agent import setup_data_agent


def main():
    """Main function to deploy the Unified Data Foundation solution."""
    
    # Constants
    SOLUTION_NAME = "Unified Data Foundation"
    ENVIRONMENT_NAME = "Data Agent Environment"
    
    LAKEHOUSE_BRONZE = 'maag_bronze'
    LAKEHOUSE_SILVER = 'maag_silver'
    LAKEHOUSE_GOLD = 'maag_gold'
    
    LAKEHOUSE_NAMES = {
        LAKEHOUSE_BRONZE,
        LAKEHOUSE_SILVER,
        LAKEHOUSE_GOLD
    }
    
    # Fabric folder names - root level
    FABRIC_FOLDER_LAKEHOUSES = 'lakehouses'
    FABRIC_FOLDER_NOTEBOOKS = 'notebooks'
    FABRIC_FOLDER_REPORTS = 'reports'
    FABRIC_FOLDER_ENVIRONMENT = 'environment'
    
    # Fabric folder names - notebook subfolders
    FABRIC_FOLDER_BRONZE_TO_SILVER = 'bronze_to_silver'
    FABRIC_FOLDER_DATA_MANAGEMENT = 'data_management'
    FABRIC_FOLDER_SCHEMA = 'schema'
    FABRIC_FOLDER_SILVER_TO_GOLD = 'silver_to_gold'
    FABRIC_FOLDER_DATA_AGENT = 'data_agent'
    
    DATA_AGENT_CONFIG_NOTEBOOK_NAME = "data_agent_setup.ipynb"
    DATA_AGENT_NAME = "Data Agent for UDF"
    DATA_AGENT_CONFIG_SELECTED_TABLES = [
        ['finance', 'account'],
        ['finance', 'invoice'],
        ['finance', 'payment'],
        ['shared', 'customer'],
        ['shared', 'productcategory'],
        ['salesfabric', 'order'],
        ['salesfabric', 'orderline'],
        ['salesfabric', 'orderpayment'],
        ['shared', 'customeraccount'],
        ['shared', 'customerrelationshiptype'],
        ['shared', 'customertradename'],
        ['shared', 'location'],
        ['shared', 'product']
    ]
    
    NOTEBOOKS_TO_RUN = [
        'run_bronze_to_silver',
        'run_silver_to_gold'
    ]
    
    # All deployment steps in order
    ALL_DEPLOYMENT_STEPS = [
        'setup_workspace',
        'setup_workspace_administrators',
        'setup_folder_structure',
        'setup_lakehouses',
        'load_csv_data_to_lakehouse',
        'deploy_notebooks',
        'schedule_notebook_jobs_sequential',
        'deploy_powerbi_reports',
        'setup_environment',
        'setup_data_agent'
    ]
    
    FABRIC_FOLDER_STRUCTURE = [
        FABRIC_FOLDER_LAKEHOUSES,
        f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_BRONZE_TO_SILVER}',
        f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_DATA_MANAGEMENT}',
        f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_SCHEMA}',
        f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_SILVER_TO_GOLD}',
        f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_DATA_AGENT}',
        FABRIC_FOLDER_REPORTS,
        FABRIC_FOLDER_ENVIRONMENT
    ]
    
    # Path initialization
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    notebooks_directory = os.path.join(repo_root, 'src', 'fabric', FABRIC_FOLDER_NOTEBOOKS)
    notebook_path_data_agent_config = os.path.join(notebooks_directory, FABRIC_FOLDER_DATA_AGENT, DATA_AGENT_CONFIG_NOTEBOOK_NAME)
    environment_yml_path = os.path.join(repo_root, "src", "fabric", "definitions", 
                                       "environment", "Libraries", "PublicLibraries", "environment.yml")
    
    # Load configuration from environment variables
    capacity_name = get_required_env_var("AZURE_FABRIC_CAPACITY_NAME")
    solution_suffix = get_required_env_var("SOLUTION_SUFFIX")
    workspace_name = os.getenv("FABRIC_WORKSPACE_NAME", f"{SOLUTION_NAME} - {solution_suffix}")
    
    # Parse capacity administrators from JSON array format
    capacity_administrators_json = os.getenv("AZURE_FABRIC_CAPACITY_ADMINISTRATORS")
    capacity_administrators_list = []
    if capacity_administrators_json:
        try:
            capacity_administrators_list = json.loads(capacity_administrators_json)
        except json.JSONDecodeError:
            print(f"⚠️  Warning: Failed to parse AZURE_FABRIC_CAPACITY_ADMINISTRATORS as JSON")
    
    # Get additional workspace administrators from environment
    fabric_workspace_admins = os.getenv("FABRIC_WORKSPACE_ADMINISTRATORS")
    
    # Combine capacity administrators and workspace administrators into single list
    workspace_administrators = []
    if capacity_administrators_list:
        workspace_administrators.extend(capacity_administrators_list)
    if fabric_workspace_admins:
        workspace_administrators.extend([admin.strip() for admin in fabric_workspace_admins.split(',') if admin.strip()])
    
    # Convert to None if empty for cleaner handling
    workspace_administrators = workspace_administrators if workspace_administrators else None
    
    # Show deployment summary
    print(f"🏭 {SOLUTION_NAME} Initialization")
    print("="*60)
    print(f"Capacity: {capacity_name}")
    print(f"Workspace: {workspace_name}")
    print(f"Solution Suffix: {solution_suffix}")
    if workspace_administrators:
        print(f"Workspace Administrators: {', '.join(workspace_administrators)}")
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
    
    try:
        powerbi_client = create_powerbi_client()
        print("✅ Power BI API client authenticated")
    except Exception as e:
        print(f"❌ Failed to authenticate Power BI API client: {e}")
        sys.exit(1)
    
    executed_steps = []
    failed_steps = []
    
    # Step 1: Setup workspace
    print_step(1, 10, "Setting up Fabric workspace and capacity assignment", 
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
        failed_steps.append({"step": "setup_workspace", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Create workspace-specific client for subsequent operations
    print("\n🔐 Creating workspace-specific Fabric API client...")
    try:
        workspace_client = create_workspace_fabric_client(workspace_id)
        print("✅ Workspace-specific authentication successful")
    except Exception as e:
        print(f"❌ Failed to create workspace-specific client: {e}")
        failed_steps.append({"step": "create_workspace_client", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 2: Setup workspace administrators
    print_step(2, 10, "Setting up Fabric workspace administrators", 
               workspace_id=workspace_id, admin_list=', '.join(workspace_administrators) if workspace_administrators else "None")
    try:
        admin_result = setup_workspace_administrators(
            workspace_client=workspace_client,
            fabric_admins=workspace_administrators,
            graph_client=graph_client
        )
        print(f"✅ Successfully completed: setup_workspace_administrators")
        executed_steps.append("setup_workspace_administrators")
    except Exception as e:
        print(f"❌ Exception while executing setup_workspace_administrators: {e}")
        failed_steps.append({"step": "setup_workspace_administrators", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 3: Setup folder structure
    print_step(3, 10, "Setting up folder structure", folder_count=len(FABRIC_FOLDER_STRUCTURE))
    try:
        fabric_folders = setup_folder_structure(
            workspace_client=workspace_client,
            folder_paths=FABRIC_FOLDER_STRUCTURE
        )
        print(f"✅ Successfully completed: setup_folder_structure")
        executed_steps.append("setup_folder_structure")
    except Exception as e:
        print(f"❌ Exception while executing setup_folder_structure: {e}")
        failed_steps.append({"step": "setup_folder_structure", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 4: Setup lakehouses
    lakehouse_folder_id = fabric_folders.get(FABRIC_FOLDER_LAKEHOUSES)
    
    print_step(4, 10, "Setting up lakehouses", lakehouse_count=len(LAKEHOUSE_NAMES))
    try:
        fabric_lakehouses = setup_lakehouses(
            workspace_client=workspace_client,
            lakehouse_names=LAKEHOUSE_NAMES,
            lakehouse_folder_id=lakehouse_folder_id
        )
        print(f"✅ Successfully completed: setup_lakehouses")
        executed_steps.append("setup_lakehouses")
    except Exception as e:
        print(f"❌ Exception while executing setup_lakehouses: {e}")
        failed_steps.append({"step": "setup_lakehouses", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 5: Load CSV data to bronze lakehouse
    csv_folder_path = os.path.join(repo_root, 'infra', 'data')
    bronze_lakehouse = fabric_lakehouses[LAKEHOUSE_BRONZE]
    
    print_step(5, 10, "Loading sample data to bronze lakehouse", 
               csv_folder=csv_folder_path)
    try:
        upload_result = load_csv_data_to_lakehouse(
            workspace_client=workspace_client,
            lakehouse=bronze_lakehouse,
            csv_folder_path=csv_folder_path
        )
        print(f"✅ Successfully completed: load_csv_data_to_lakehouse")
        executed_steps.append("load_csv_data_to_lakehouse")
    except Exception as e:
        print(f"❌ Exception while executing load_csv_data_to_lakehouse: {e}")
        failed_steps.append({"step": "load_csv_data_to_lakehouse", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 6: Deploy notebooks
    # Build notebook specifications directly as a list
    notebook_specs = [
        # Root level notebooks
        build_notebook_spec('run_bronze_to_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec('run_silver_to_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        
        # Bronze to Silver transformation notebooks
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_finance_account.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_finance_invoice.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_finance_payment.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesadb_order.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesadb_orderLine.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesadb_orderPayment.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesfabric_order.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesfabric_orderLine.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_salesfabric_orderPayment.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_customer.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_customeraccount.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_customerRelationshipType.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_customerTradeName.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_location.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_product.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_BRONZE_TO_SILVER}/bronze_to_silver_shared_productCategory.ipynb', LAKEHOUSE_BRONZE, LAKEHOUSE_SILVER, fabric_folders),
        
        # Data management notebooks
        build_notebook_spec(f'{FABRIC_FOLDER_DATA_MANAGEMENT}/drop_all_tables_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_DATA_MANAGEMENT}/drop_all_tables_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_DATA_MANAGEMENT}/trouble_shooting.ipynb', None, None, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_DATA_MANAGEMENT}/truncate_all_tables_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_DATA_MANAGEMENT}/truncate_all_tables_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        
        # Schema notebooks
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_finance_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_salesadb_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_salesfabric_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_shared_gold.ipynb', None, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_finance_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_salesadb_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_salesfabric_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SCHEMA}/model_shared_silver.ipynb', None, LAKEHOUSE_SILVER, fabric_folders),
        
        # Silver to Gold transformation notebooks
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_finance_account.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_finance_invoice.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_finance_payment.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_sales_order_line.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_sales_order_payment.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_sales_order.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesadb_order.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesadb_orderLine.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesadb_orderPayment.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesfabric_order.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesfabric_orderLine.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_salesfabric_orderPayment.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_customer.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_customeraccount.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_customerRelationshipType.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_customerTradeName.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_location.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_product.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
        build_notebook_spec(f'{FABRIC_FOLDER_SILVER_TO_GOLD}/silver_to_gold_shared_productCategory.ipynb', LAKEHOUSE_SILVER, LAKEHOUSE_GOLD, fabric_folders),
    ]
    
    print_step(6, 10, "Deploying notebooks", notebook_count=len(notebook_specs))
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
        failed_steps.append({"step": "deploy_notebooks", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 7: Execute notebooks
    print_step(7, 10, "Executing data transformation pipelines", 
               notebook_count=len(NOTEBOOKS_TO_RUN))
    try:
        # Prepare notebook specs with IDs
        notebook_specs_to_run = [
            {
                'name': notebook_name,
                'id': fabric_notebooks[notebook_name]
            }
            for notebook_name in NOTEBOOKS_TO_RUN
            if notebook_name in fabric_notebooks
        ]
        
        execution_results = schedule_notebook_jobs_sequential(
            workspace_client=workspace_client,
            notebook_specs=notebook_specs_to_run,
            monitor_interval=20
        )
        print(f"✅ Successfully completed: schedule_notebook_jobs_sequential")
        executed_steps.append("schedule_notebook_jobs_sequential")
    except Exception as e:
        print(f"❌ Exception while executing notebooks: {e}")
        failed_steps.append({"step": "schedule_notebook_jobs_sequential", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 8: Deploy Power BI reports
    reports_folder_path = os.path.join(repo_root, 'reports')
    reports_fabric_folder_id = fabric_folders.get(FABRIC_FOLDER_REPORTS)
    gold_lakehouse = fabric_lakehouses[LAKEHOUSE_GOLD]
    gold_lakehouse_id = gold_lakehouse.get('id')
    
    print_step(8, 10, "Deploying Power BI reports", 
               reports_folder=reports_folder_path)
    try:
        deployed_reports = deploy_powerbi_reports(
            workspace_client=workspace_client,
            powerbi_client=powerbi_client,
            workspace_id=workspace_id,
            reports_folder_path=reports_folder_path,
            gold_lakehouse_id=gold_lakehouse_id,
            gold_lakehouse_name=LAKEHOUSE_GOLD,
            reports_fabric_folder_id=reports_fabric_folder_id
        )
        print(f"✅ Successfully completed: deploy_powerbi_reports")
        executed_steps.append("deploy_powerbi_reports")
    except Exception as e:
        print(f"❌ Exception while executing deploy_powerbi_reports: {e}")
        failed_steps.append({"step": "deploy_powerbi_reports", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 9: Setup environment
    environment_folder_id = fabric_folders.get(FABRIC_FOLDER_ENVIRONMENT)
    
    print_step(9, 10, "Setting up Fabric environment", 
               environment_name=ENVIRONMENT_NAME)
    try:
        environment_info = setup_environment(
            workspace_client=workspace_client,
            environment_name=ENVIRONMENT_NAME,
            environment_yml_path=environment_yml_path if os.path.exists(environment_yml_path) else None,
            folder_id=environment_folder_id
        )
        environment_id = environment_info.get('id')
        print(f"✅ Successfully completed: setup_environment")
        executed_steps.append("setup_environment")
    except Exception as e:
        print(f"❌ Exception while executing setup_environment: {e}")
        failed_steps.append({"step": "setup_environment", "error": str(e)})
        # Calculate uncompleted steps
        completed_step_names = executed_steps + [step['step'] for step in failed_steps]
        uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
        sys.exit(1)
    
    # Step 10: Setup data agent
    if environment_info:
        gold_lakehouse = fabric_lakehouses[LAKEHOUSE_GOLD]
        gold_lakehouse_id = gold_lakehouse.get('id')
        
        print_step(10, 10, "Setting up Data Agent", 
                   data_agent_name=DATA_AGENT_NAME,
                   lakehouse_id=gold_lakehouse_id)
        try:
            data_agent_result = setup_data_agent(
                workspace_client=workspace_client,
                data_agent_name=DATA_AGENT_NAME,
                lakehouse_id=gold_lakehouse_id,
                lakehouse_workspace_id=workspace_id,
                environment_id=environment_id,
                selected_tables=DATA_AGENT_CONFIG_SELECTED_TABLES,
                notebook_path=notebook_path_data_agent_config,
                notebook_fabric_folder_id=fabric_folders.get(f'{FABRIC_FOLDER_NOTEBOOKS}/{FABRIC_FOLDER_DATA_AGENT}')
            )
            print(f"✅ Successfully completed: setup_data_agent")
            executed_steps.append("setup_data_agent")
        except Exception as e:
            print(f"⚠️  Warning: Data Agent setup failed: {e}")
            print(f"   Data Agent is a preview feature and may not be available in all regions")
            print(f"   You can set up the Data Agent manually following the documentation")
    else:
        print(f"ℹ️  Skipping Data Agent setup (environment not created)")
    
    # Success!
    print(f"\n🎉 {SOLUTION_NAME} deployment completed successfully!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate uncompleted steps (if any - e.g., data agent might be skipped)
    completed_step_names = executed_steps + [step['step'] for step in failed_steps]
    uncompleted_steps = [step for step in ALL_DEPLOYMENT_STEPS if step not in completed_step_names]
    
    print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted_steps)
    
    # Print resource URLs
    workspace_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}?experience=fabric-developer"
    
    print(f"\n" + "="*60)
    print(f"🎉 {SOLUTION_NAME.upper()} DEPLOYMENT COMPLETE!")
    print(f"="*60)
    print(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏷️  Solution: {solution_suffix}")
    
    print(f"\n✅ DEPLOYED RESOURCES:")
    print(f"   ☁️ Workspace:     {workspace_name}")
    print(f"   🏠 Lakehouses:    {', '.join(LAKEHOUSE_NAMES)}")
    print(f"   📓 Notebooks:     {len(fabric_notebooks)} deployed")
    if 'deploy_powerbi_reports' in executed_steps:
        print(f"   📊 Reports:       {len(deployed_reports)} Power BI reports")
    print(f"   🌍 Environment:   {ENVIRONMENT_NAME}")
    if 'setup_data_agent' in executed_steps:
        print(f"   🤖 Data Agent:    {DATA_AGENT_NAME} (✅ Configured)")
    
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
