#!/usr/bin/env python3
"""
UDF Power BI Reports Deployment Module

This module provides Power BI report deployment and configuration functionality 
for the Unified Data Foundation solution.
"""

import sys
import os
import glob
import requests
from typing import Optional, List, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from powerbi_api import PowerBIAPIClient, ImportConflictHandlerMode
from fabric_api import FabricWorkspaceApiClient, FabricApiError


def deploy_powerbi_reports(workspace_client: FabricWorkspaceApiClient,
                           powerbi_client: PowerBIAPIClient,
                           workspace_id: str,
                           reports_folder_path: str,
                           gold_lakehouse_id: str,
                           gold_lakehouse_name: str,
                           reports_fabric_folder_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Deploy Power BI reports from local folder to Fabric workspace and configure dataset connections.
    
    Args:
        workspace_client: Authenticated workspace API client
        powerbi_client: Authenticated Power BI API client
        workspace_id: ID of the target workspace
        reports_folder_path: Local folder path containing .pbix files
        gold_lakehouse_id: ID of the Gold lakehouse for dataset configuration
        gold_lakehouse_name: Name of the Gold lakehouse
        reports_fabric_folder_id: Optional folder ID where to deploy reports
        
    Returns:
        List[Dict]: List of deployed report dictionaries with 'name' and 'id' keys
        
    Raises:
        Exception: If report deployment or configuration fails
    """
    print(f"📊 Deploying Power BI reports")
    
    # Find all .pbix files in reports folder
    pbix_pattern = os.path.join(reports_folder_path, '**', '*.pbix')
    pbix_file_paths = glob.glob(pbix_pattern, recursive=True)
    deployed_reports = []
    
    if not pbix_file_paths:
        print("   ℹ️  No Power BI report files (.pbix) found in reports directory")
        return deployed_reports
    
    print(f"   📋 Found {len(pbix_file_paths)} Power BI report(s) to deploy")
    
    for pbix_file_path in pbix_file_paths:
        report_file_name = os.path.basename(pbix_file_path)
        report_name = report_file_name.replace('.pbix', '')
        print(f"\n   📊 Deploying report '{report_name}'")
        
        try:
            # Deploy the report
            new_report = powerbi_client.new_report(
                report_name=report_name,
                file_path=pbix_file_path,
                conflict_action=ImportConflictHandlerMode.CREATE_OR_OVERWRITE,
                workspace_id=workspace_id,
                subfolder_object_id=reports_fabric_folder_id,
                timeout=300  # 5 minutes
            )
            
            report_id = new_report.get('id', 'Unknown')
            report_name = new_report.get('name', report_name)
            deployed_reports.append({'name': report_name, 'id': report_id})
            print(f"      ✅ Successfully deployed report '{report_name}' (ID: {report_id})")
            
            # Configure dataset parameters
            print(f"      🔧 Configuring dataset parameters for '{report_name}'...")
            
            try:
                # Get dataset for the report
                dataset = powerbi_client.get_powerbi_dataset(
                    dataset_name=report_name,
                    workspace_id=workspace_id
                )
                
                # Get Gold lakehouse details and check SQL endpoint status
                gold_lakehouse = workspace_client.get_lakehouse(lakehouse_id=gold_lakehouse_id)
                sql_endpoint_status = gold_lakehouse.get('properties', {}).get(
                    'sqlEndpointProperties', {}).get('provisioningStatus', 'Unknown')
                
                print(f"         📋 SQL endpoint status: {sql_endpoint_status}")
                
                if sql_endpoint_status == 'Success':
                    # Get connection string from lakehouse properties
                    connection_string = gold_lakehouse.get('properties', {}).get(
                        'sqlEndpointProperties', {}).get('connectionString', '')
                    
                    if connection_string:
                        print(f"         🔗 SQL Endpoint: {connection_string}")
                        print(f"         🔗 Database: {gold_lakehouse_name}")
                        
                        # Update dataset parameters with lakehouse connection
                        # Note: This assumes the PBIX has parameters named 'sqlEndpoint' and 'database'
                        # If your PBIX uses different parameter names, update them accordingly
                        try:
                            # Take over the dataset to ensure we have ownership before updating parameters
                            powerbi_client.takeover_dataset(
                                workspace_id=workspace_id,
                                dataset_id=dataset.get('id')
                            )
                            print(f"         ✅ Dataset takeover completed")
                            
                            powerbi_client.update_powerbi_dataset_parameters(
                                dataset_id=dataset.get('id'),
                                parameters=[
                                    {
                                        "name": "sqlEndpoint", 
                                        "newValue": connection_string
                                    },
                                    {
                                        "name": "database", 
                                        "newValue": gold_lakehouse_name
                                    }
                                ],
                                workspace_id=workspace_id
                            )
                            print(f"         ✅ Dataset parameters configured successfully")
                        except requests.HTTPError as e:
                            error_msg = str(e)
                            # Handle specific HTTP errors
                            if "HTTP 404" in error_msg or "ItemNotFound" in error_msg:
                                print(f"         ℹ️  Info: Dataset parameters not found in report")
                                print(f"            The report does not use 'sqlEndpoint' and 'database' parameters")
                                print(f"            This is normal for reports with direct connections or different parameter names")
                            elif "HTTP 403" in error_msg:
                                print(f"         ⚠️  Warning: API access restricted for parameter updates")
                                print(f"            Service Principals cannot update Power BI dataset parameters")
                                print(f"            Manual configuration required in Power BI service")
                            else:
                                print(f"         ⚠️  Warning: Could not update dataset parameters: {error_msg}")
                                print(f"            You may need to configure the dataset connection manually")
                        except Exception as e:
                            print(f"         ⚠️  Warning: Could not update dataset parameters: {str(e)}")
                            print(f"            You may need to configure the dataset connection manually")
                    else:
                        print(f"         ⚠️  Warning: Connection string not available")
                        print(f"            Dataset will need manual configuration")
                else:
                    print(f"         ⚠️  Warning: SQL endpoint not ready (status: {sql_endpoint_status})")
                    print(f"            Dataset will need manual configuration once SQL endpoint is available")
                    
            except Exception as e:
                print(f"         ⚠️  Warning: Dataset configuration failed: {e}")
                print(f"            Report deployed but dataset may need manual configuration")
        
        except Exception as e:
            print(f"      ❌ Failed to deploy report '{report_name}': {e}")
            # Continue with other reports instead of failing completely
            continue
    
    # Print summary
    if deployed_reports:
        print(f"\n   ✅ Successfully deployed {len(deployed_reports)} Power BI report(s)")
    else:
        print(f"\n   ⚠️  No reports were successfully deployed")
    
    return deployed_reports


def main():
    """Main function for standalone testing of Power BI deployment"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy Power BI reports to Microsoft Fabric workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy reports to a workspace
  python udf_powerbi.py --workspace-id "12345678-1234-1234-1234-123456789012" --reports-folder "C:/reports" --gold-lakehouse-id "87654321-4321-4321-4321-210987654321" --gold-lakehouse-name "maag_gold"
        """
    )
    
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="ID of the workspace"
    )
    
    parser.add_argument(
        "--reports-folder",
        required=True,
        help="Path to folder containing .pbix files"
    )
    
    parser.add_argument(
        "--gold-lakehouse-id",
        required=True,
        help="ID of the Gold lakehouse"
    )
    
    parser.add_argument(
        "--gold-lakehouse-name",
        required=True,
        help="Name of the Gold lakehouse"
    )
    
    parser.add_argument(
        "--reports-fabric-folder-id",
        required=False,
        help="Optional folder ID where to deploy reports"
    )
    
    args = parser.parse_args()
    
    try:
        from powerbi_api import create_powerbi_client
        from fabric_api import create_workspace_fabric_client
        
        # Create clients
        workspace_client = create_workspace_fabric_client(args.workspace_id)
        powerbi_client = create_powerbi_client()
        
        # Deploy reports
        deployed_reports = deploy_powerbi_reports(
            workspace_client=workspace_client,
            powerbi_client=powerbi_client,
            workspace_id=args.workspace_id,
            reports_folder_path=args.reports_folder,
            gold_lakehouse_id=args.gold_lakehouse_id,
            gold_lakehouse_name=args.gold_lakehouse_name,
            reports_fabric_folder_id=args.reports_fabric_folder_id
        )
        
        print(f"\n🎉 Deployment complete!")
        print(f"   Deployed {len(deployed_reports)} report(s)")
        
        if deployed_reports:
            print(f"\n   Deployed reports:")
            for report in deployed_reports:
                print(f"      - {report['name']} (ID: {report['id']})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
