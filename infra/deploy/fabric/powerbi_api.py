"""
Microsoft Power BI API Python Module generated from https://github.com/microsoft/powerbi-powershell

This module provides Python functions for interacting with Microsoft Power BI APIs,
following the same patterns as the Fabric API module.

Dependencies:
    pip install requests azure-identity azure-core python-dateutil

Author: Python conversion of PowerShell Power BI module
"""

import os
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum
from azure.identity import DefaultAzureCredential, ClientSecretCredential


class ImportConflictHandlerMode(Enum):
    """Enumeration for import conflict handling modes"""
    IGNORE = "Ignore"
    ABORT = "Abort"
    OVERWRITE = "Overwrite"
    CREATE_OR_OVERWRITE = "CreateOrOverwrite"


class PowerBIAPIClient:
    """Microsoft Power BI API Client for Python"""
    
    def __init__(self, api_url: str = "https://api.powerbi.com/v1.0/myorg",
                 resource_url: str = "https://analysis.windows.net/powerbi/api"):
        self.api_url = api_url
        self.resource_url = resource_url
        self._powerbi_token = None
        self._credential = None
    
    def write_log(self, message: str, level: str = "INFO"):
        """Write log message with timestamp"""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {level}: {message}")
    
    def get_powerbi_auth_token(self) -> str:
        """Get the Power BI API authentication token"""
        if not self._powerbi_token:
            self.set_powerbi_auth_token()
        
        return self._powerbi_token.token
    
    def set_powerbi_auth_token(self, 
                              service_principal_id: Optional[str] = None,
                              service_principal_secret: Optional[str] = None,
                              tenant_id: Optional[str] = None,
                              credential=None,
                              reset: bool = False,
                              api_url: Optional[str] = None):
        """Set authentication token for the Power BI service"""
        
        if api_url:
            self.api_url = api_url
        
        if reset:
            self._powerbi_token = None
            self._credential = None
        
        self.write_log("Getting authentication token")
        
        if service_principal_id and service_principal_secret and tenant_id:
            self._credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=service_principal_id,
                client_secret=service_principal_secret
            )
        elif credential:
            self._credential = credential
        else:
            self._credential = DefaultAzureCredential()
        
        # Get token for Power BI API
        self._powerbi_token = self._credential.get_token(self.resource_url + "/.default")
        
        self.write_log("Connected successfully")
    
    def invoke_powerbi_api_request(self,
                                  uri: str,
                                  method: str = "GET",
                                  body: Optional[Union[str, dict]] = None,
                                  auth_token: Optional[str] = None,
                                  content_type: str = "application/json; charset=utf-8",
                                  timeout_sec: int = 240) -> Optional[Union[dict, list]]:
        """
        Sends an HTTP request to a Power BI API endpoint and retrieves the response.
        Takes care of: authentication, 429 throttling, Long-Running-Operation (LRO) response
        """
        
        if not auth_token:
            auth_token = self.get_powerbi_auth_token()
        
        headers = {
            'Content-Type': content_type,
            'Authorization': f'Bearer {auth_token}'
        }
        
        try:
            request_url = f"{self.api_url}/{uri}"
            self.write_log(f"Calling {request_url}")
            
            # Convert body to JSON string if it's a dict
            if isinstance(body, dict):
                body = json.dumps(body)
            
            response = requests.request(
                method=method.upper(),
                url=request_url,
                headers=headers,
                data=body,
                timeout=timeout_sec
            )
            
            request_id = response.headers.get('requestId', 'N/A')
            self.write_log(f"RAID: {request_id}")
            
            lro_fail_or_no_result_flag = False
            
            # Handle Long Running Operation (LRO)
            if response.status_code == 202:
                location_header = response.headers.get('Location')
                if location_header:
                    self.write_log("Long running operation detected, polling for completion...")
                    # Poll the location URL until completion
                    while True:
                        time.sleep(5)
                        lro_response = requests.get(location_header, headers={'Authorization': f'Bearer {auth_token}'})
                        if lro_response.status_code == 200:
                            response = lro_response
                            break
                        elif lro_response.status_code != 202:
                            lro_fail_or_no_result_flag = True
                            break
            
            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.write_log(error_msg, "ERROR")
                raise requests.HTTPError(error_msg)
            
            self.write_log("Request completed.")
            
            if not lro_fail_or_no_result_flag and response.content:
                try:
                    return response.json()
                except:
                    return response.text
            
            return None
            
        except requests.RequestException as e:
            self.write_log(f"Request failed: {str(e)}", "ERROR")
            raise
    
    def invoke_powerbi_file_upload(self,
                                  uri: str,
                                  file_path: str,
                                  auth_token: Optional[str] = None,
                                  timeout_sec: int = 300) -> Optional[Union[dict, list]]:
        """
        Uploads a file to Power BI API endpoint.
        """
        
        if not auth_token:
            auth_token = self.get_powerbi_auth_token()
        
        headers = {
            'Authorization': f'Bearer {auth_token}'
        }
        
        try:
            request_url = f"{self.api_url}/{uri}"
            self.write_log(f"Uploading file to {request_url}")
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, 'application/octet-stream')
                }
                
                response = requests.post(
                    url=request_url,
                    headers=headers,
                    files=files,
                    timeout=timeout_sec
                )
            
            request_id = response.headers.get('requestId', 'N/A')
            self.write_log(f"RAID: {request_id}")
            
            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.write_log(error_msg, "ERROR")
                raise requests.HTTPError(error_msg)
            
            self.write_log("File upload completed.")
            
            if response.content:
                try:
                    return response.json()
                except:
                    return response.text
            
            return None
            
        except requests.RequestException as e:
            self.write_log(f"File upload failed: {str(e)}", "ERROR")
            raise
    
    def get_import(self, import_id: str, workspace_id: Optional[str] = None) -> Optional[dict]:
        """Get a specific import by ID"""
        if workspace_id:
            uri = f"groups/{workspace_id}/imports/{import_id}"
        else:
            uri = f"imports/{import_id}"
        
        response = self.invoke_powerbi_api_request(uri=uri, method="GET")
        return response
    
    def post_import(self, dataset_display_name: str, file_path: str, 
                   name_conflict: ImportConflictHandlerMode = ImportConflictHandlerMode.CREATE_OR_OVERWRITE,
                   workspace_id: Optional[str] = None,
                   subfolder_object_id: Optional[str] = None) -> str:
        """Post a file import to Power BI"""
        
        if workspace_id:
            uri = f"groups/{workspace_id}/imports"
        else:
            uri = "imports"
        
        # Add query parameters
        params = {
            'datasetDisplayName': dataset_display_name,
            'nameConflict': name_conflict.value
        }
        
        if subfolder_object_id:
            params['subfolderObjectId'] = subfolder_object_id
        
        # Convert params to query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        uri = f"{uri}?{query_string}"
        
        # Upload file using the new method
        response = self.invoke_powerbi_file_upload(
            uri=uri,
            file_path=file_path,
            timeout_sec=300
        )
        
        if response and 'id' in response:
            return response['id']
        
        raise Exception("Failed to start import")
    
    def new_report(self, report_name: str, file_path: str, 
                  conflict_action: ImportConflictHandlerMode = ImportConflictHandlerMode.CREATE_OR_OVERWRITE,
                  workspace_id: Optional[str] = None, subfolder_object_id: Optional[str] = None,
                  timeout: int = 0) -> dict:
        """Create a new report by importing a PBIX file"""
        
        self.write_log(f"Starting import of report '{report_name}' from file '{file_path}'")
        
        # Start the import
        import_id = self.post_import(
            dataset_display_name=report_name,
            file_path=file_path,
            name_conflict=conflict_action,
            workspace_id=workspace_id,
            subfolder_object_id=subfolder_object_id
        )
        
        self.write_log(f"Import started with ID: {import_id}")
        
        # If timeout is 0, don't wait for completion
        if timeout == 0:
            # Just return a basic report object with the name
            return {"name": report_name, "id": None}
        
        # Wait for import to complete
        start_time = time.time()
        while True:
            import_obj = self.get_import(import_id, workspace_id)
            
            if not import_obj:
                raise Exception(f"Could not retrieve import status for ID: {import_id}")
            
            import_state = import_obj.get('importState', 'Unknown')
            self.write_log(f"Import state: {import_state}")
            
            if import_state == "Succeeded":
                reports = import_obj.get('reports', [])
                if reports:
                    return reports[0]
                else:
                    raise Exception("Import succeeded but no reports were created")
            
            elif import_state == "Failed":
                raise Exception(f"Import failed for report '{report_name}' (ID: {import_id}). State: {import_state}")
            
            # Check timeout
            if timeout > 0 and (time.time() - start_time) > timeout:
                raise Exception(f"Import timeout after {timeout} seconds")
            
            # Wait before checking again
            time.sleep(5)
    
    def get_powerbi_workspaces(self) -> List[dict]:
        """Get all Power BI workspaces"""
        response = self.invoke_powerbi_api_request(uri="groups", method="GET")
        return response.get('value', []) if response else []
    
    def get_powerbi_workspace(self, workspace_name: str) -> dict:
        """Get Power BI workspace by name"""
        workspaces = self.get_powerbi_workspaces()
        
        workspace = next((w for w in workspaces if w['name'].lower() == workspace_name.lower()), None)
        
        if not workspace:
            raise Exception(f"Cannot find workspace '{workspace_name}'")
        
        return workspace
    
    def get_powerbi_reports(self, workspace_id: Optional[str] = None) -> List[dict]:
        """Get all reports in a workspace or user's reports"""
        if workspace_id:
            uri = f"groups/{workspace_id}/reports"
        else:
            uri = "reports"
        
        response = self.invoke_powerbi_api_request(uri=uri, method="GET")
        return response.get('value', []) if response else []
    
    def delete_powerbi_report(self, report_id: str, workspace_id: Optional[str] = None):
        """Delete a Power BI report"""
        if workspace_id:
            uri = f"groups/{workspace_id}/reports/{report_id}"
        else:
            uri = f"reports/{report_id}"
        
        self.invoke_powerbi_api_request(uri=uri, method="DELETE")


# Factory function

def create_powerbi_client(api_url: str = "https://api.powerbi.com/v1.0/myorg",
                         resource_url: str = "https://analysis.windows.net/powerbi/api") -> PowerBIAPIClient:
    """Create a new Power BI API client instance"""
    return PowerBIAPIClient(api_url, resource_url)
