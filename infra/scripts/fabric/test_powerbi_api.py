"""
Unit tests for powerbi_api.py

Tests for PowerBIAPIClient class and helper functions.
"""

import json
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open

import requests

from powerbi_api import PowerBIAPIClient, ImportConflictHandlerMode, create_powerbi_client


class TestImportConflictHandlerMode(unittest.TestCase):
    """Test cases for ImportConflictHandlerMode enum"""
    
    def test_ignore_value(self):
        """Test IGNORE mode value"""
        self.assertEqual(ImportConflictHandlerMode.IGNORE.value, "Ignore")
    
    def test_abort_value(self):
        """Test ABORT mode value"""
        self.assertEqual(ImportConflictHandlerMode.ABORT.value, "Abort")
    
    def test_overwrite_value(self):
        """Test OVERWRITE mode value"""
        self.assertEqual(ImportConflictHandlerMode.OVERWRITE.value, "Overwrite")
    
    def test_create_or_overwrite_value(self):
        """Test CREATE_OR_OVERWRITE mode value"""
        self.assertEqual(ImportConflictHandlerMode.CREATE_OR_OVERWRITE.value, "CreateOrOverwrite")


class TestPowerBIAPIClientInit(unittest.TestCase):
    """Test cases for PowerBIAPIClient initialization"""
    
    def test_default_initialization(self):
        """Test default initialization"""
        client = PowerBIAPIClient()
        self.assertEqual(client.api_url, "https://api.powerbi.com/v1.0/myorg")
        self.assertEqual(client.resource_url, "https://analysis.windows.net/powerbi/api")
        self.assertIsNone(client._powerbi_token)
        self.assertIsNone(client._credential)
    
    def test_custom_initialization(self):
        """Test custom initialization"""
        client = PowerBIAPIClient(
            api_url="https://custom.api.com/v2",
            resource_url="https://custom.resource.com"
        )
        self.assertEqual(client.api_url, "https://custom.api.com/v2")
        self.assertEqual(client.resource_url, "https://custom.resource.com")


class TestPowerBIAPIClientLogging(unittest.TestCase):
    """Test cases for logging functionality"""
    
    def test_write_log_default_level(self):
        """Test write_log with default level"""
        client = PowerBIAPIClient()
        with patch('builtins.print') as mock_print:
            client.write_log("Test message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            self.assertIn("INFO", call_args)
            self.assertIn("Test message", call_args)
    
    def test_write_log_error_level(self):
        """Test write_log with ERROR level"""
        client = PowerBIAPIClient()
        with patch('builtins.print') as mock_print:
            client.write_log("Error message", level="ERROR")
            call_args = mock_print.call_args[0][0]
            self.assertIn("ERROR", call_args)
            self.assertIn("Error message", call_args)


class TestPowerBIAPIClientAuth(unittest.TestCase):
    """Test cases for authentication"""
    
    @patch('powerbi_api.DefaultAzureCredential')
    def test_set_powerbi_auth_token_default_credential(self, mock_default_cred):
        """Test setting auth token with default credential"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_credential.get_token.return_value = mock_token
        mock_default_cred.return_value = mock_credential
        
        client = PowerBIAPIClient()
        client.set_powerbi_auth_token()
        
        self.assertEqual(client._powerbi_token.token, "test_token")
        mock_credential.get_token.assert_called_once()
    
    @patch('powerbi_api.ClientSecretCredential')
    def test_set_powerbi_auth_token_service_principal(self, mock_client_cred):
        """Test setting auth token with service principal"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "sp_token"
        mock_credential.get_token.return_value = mock_token
        mock_client_cred.return_value = mock_credential
        
        client = PowerBIAPIClient()
        client.set_powerbi_auth_token(
            service_principal_id="sp-id",
            service_principal_secret="sp-secret",
            tenant_id="tenant-id"
        )
        
        mock_client_cred.assert_called_once_with(
            tenant_id="tenant-id",
            client_id="sp-id",
            client_secret="sp-secret"
        )
        self.assertEqual(client._powerbi_token.token, "sp_token")
    
    def test_set_powerbi_auth_token_custom_credential(self):
        """Test setting auth token with custom credential"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "custom_token"
        mock_credential.get_token.return_value = mock_token
        
        client = PowerBIAPIClient()
        client.set_powerbi_auth_token(credential=mock_credential)
        
        self.assertEqual(client._powerbi_token.token, "custom_token")
    
    @patch('powerbi_api.DefaultAzureCredential')
    def test_set_powerbi_auth_token_reset(self, mock_default_cred):
        """Test resetting auth token"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "new_token"
        mock_credential.get_token.return_value = mock_token
        mock_default_cred.return_value = mock_credential
        
        client = PowerBIAPIClient()
        client._powerbi_token = Mock(token="old_token")
        client._credential = Mock()
        
        client.set_powerbi_auth_token(reset=True)
        
        self.assertEqual(client._powerbi_token.token, "new_token")
    
    @patch('powerbi_api.DefaultAzureCredential')
    def test_get_powerbi_auth_token(self, mock_default_cred):
        """Test getting auth token"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_credential.get_token.return_value = mock_token
        mock_default_cred.return_value = mock_credential
        
        client = PowerBIAPIClient()
        token = client.get_powerbi_auth_token()
        
        self.assertEqual(token, "test_token")


class TestPowerBIAPIClientRequests(unittest.TestCase):
    """Test cases for API requests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.request')
    def test_invoke_powerbi_api_request_get(self, mock_request):
        """Test GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "1"}]}'
        mock_response.json.return_value = {"value": [{"id": "1"}]}
        mock_request.return_value = mock_response
        
        result = self.client.invoke_powerbi_api_request("groups", method="GET")
        
        self.assertEqual(result["value"][0]["id"], "1")
    
    @patch('powerbi_api.requests.request')
    def test_invoke_powerbi_api_request_post(self, mock_request):
        """Test POST request with body"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"id": "new-id"}'
        mock_response.json.return_value = {"id": "new-id"}
        mock_request.return_value = mock_response
        
        body = {"name": "Test"}
        result = self.client.invoke_powerbi_api_request("groups", method="POST", body=body)
        
        self.assertEqual(result["id"], "new-id")
    
    @patch('powerbi_api.requests.request')
    def test_invoke_powerbi_api_request_error(self, mock_request):
        """Test error handling"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'requestId': '12345'}
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response
        
        with self.assertRaises(requests.HTTPError):
            self.client.invoke_powerbi_api_request("groups", method="GET")
    
    @patch('powerbi_api.requests.request')
    @patch('powerbi_api.requests.get')
    @patch('powerbi_api.time.sleep')
    def test_invoke_powerbi_api_request_lro(self, mock_sleep, mock_get, mock_request):
        """Test Long Running Operation handling"""
        # Initial 202 response
        mock_lro_response = Mock()
        mock_lro_response.status_code = 202
        mock_lro_response.headers = {
            'requestId': '12345',
            'Location': 'https://api.powerbi.com/v1.0/myorg/imports/status'
        }
        mock_lro_response.content = b''
        mock_request.return_value = mock_lro_response
        
        # LRO completion response
        mock_complete_response = Mock()
        mock_complete_response.status_code = 200
        mock_complete_response.content = b'{"id": "completed-id"}'
        mock_complete_response.json.return_value = {"id": "completed-id"}
        mock_get.return_value = mock_complete_response
        
        result = self.client.invoke_powerbi_api_request("imports", method="POST")
        
        self.assertEqual(result["id"], "completed-id")


class TestPowerBIAPIClientFileUpload(unittest.TestCase):
    """Test cases for file upload"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.post')
    @patch('builtins.open', mock_open(read_data=b'file content'))
    def test_invoke_powerbi_file_upload_success(self, mock_post):
        """Test successful file upload"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"id": "upload-id"}'
        mock_response.json.return_value = {"id": "upload-id"}
        mock_post.return_value = mock_response
        
        result = self.client.invoke_powerbi_file_upload(
            uri="groups/ws-id/imports",
            file_path="/path/to/file.pbix"
        )
        
        self.assertEqual(result["id"], "upload-id")
    
    @patch('powerbi_api.requests.post')
    @patch('builtins.open', mock_open(read_data=b'file content'))
    def test_invoke_powerbi_file_upload_error(self, mock_post):
        """Test file upload error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'requestId': '12345'}
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        with self.assertRaises(requests.HTTPError):
            self.client.invoke_powerbi_file_upload(
                uri="groups/ws-id/imports",
                file_path="/path/to/file.pbix"
            )


class TestPowerBIAPIClientWorkspaceOperations(unittest.TestCase):
    """Test cases for workspace operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_workspaces(self, mock_request):
        """Test getting workspaces"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "ws1", "name": "Workspace 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "ws1", "name": "Workspace 1"}]}
        mock_request.return_value = mock_response
        
        workspaces = self.client.get_powerbi_workspaces()
        
        self.assertEqual(len(workspaces), 1)
        self.assertEqual(workspaces[0]["name"], "Workspace 1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_workspace_found(self, mock_request):
        """Test getting workspace by name when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "ws1", "name": "Workspace 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "ws1", "name": "Workspace 1"}]}
        mock_request.return_value = mock_response
        
        workspace = self.client.get_powerbi_workspace("Workspace 1")
        
        self.assertEqual(workspace["id"], "ws1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_workspace_case_insensitive(self, mock_request):
        """Test getting workspace is case insensitive"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "ws1", "name": "My Workspace"}]}'
        mock_response.json.return_value = {"value": [{"id": "ws1", "name": "My Workspace"}]}
        mock_request.return_value = mock_response
        
        workspace = self.client.get_powerbi_workspace("my workspace")
        
        self.assertEqual(workspace["id"], "ws1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_workspace_not_found(self, mock_request):
        """Test getting workspace when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": []}'
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            self.client.get_powerbi_workspace("NonExistent")
        
        self.assertIn("Cannot find workspace", str(context.exception))


class TestPowerBIAPIClientReportOperations(unittest.TestCase):
    """Test cases for report operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_reports_with_workspace(self, mock_request):
        """Test getting reports from workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "r1", "name": "Report 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "r1", "name": "Report 1"}]}
        mock_request.return_value = mock_response
        
        reports = self.client.get_powerbi_reports(workspace_id="ws-id")
        
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["name"], "Report 1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_reports_without_workspace(self, mock_request):
        """Test getting reports without workspace (My workspace)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "r1", "name": "Report 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "r1", "name": "Report 1"}]}
        mock_request.return_value = mock_response
        
        reports = self.client.get_powerbi_reports()
        
        self.assertEqual(len(reports), 1)
    
    @patch('powerbi_api.requests.request')
    def test_delete_powerbi_report(self, mock_request):
        """Test deleting a report"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b''
        mock_request.return_value = mock_response
        
        # Should not raise
        self.client.delete_powerbi_report("report-id", workspace_id="ws-id")
        
        mock_request.assert_called_once()


class TestPowerBIAPIClientDatasetOperations(unittest.TestCase):
    """Test cases for dataset operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_datasets(self, mock_request):
        """Test getting datasets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "ds1", "name": "Dataset 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "ds1", "name": "Dataset 1"}]}
        mock_request.return_value = mock_response
        
        datasets = self.client.get_powerbi_datasets(workspace_id="ws-id")
        
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]["name"], "Dataset 1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_dataset_found(self, mock_request):
        """Test getting dataset by name when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": [{"id": "ds1", "name": "Dataset 1"}]}'
        mock_response.json.return_value = {"value": [{"id": "ds1", "name": "Dataset 1"}]}
        mock_request.return_value = mock_response
        
        dataset = self.client.get_powerbi_dataset("Dataset 1", workspace_id="ws-id")
        
        self.assertEqual(dataset["id"], "ds1")
    
    @patch('powerbi_api.requests.request')
    def test_get_powerbi_dataset_not_found(self, mock_request):
        """Test getting dataset when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"value": []}'
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            self.client.get_powerbi_dataset("NonExistent", workspace_id="ws-id")
        
        self.assertIn("Cannot find dataset", str(context.exception))


class TestPowerBIAPIClientDatasetParameters(unittest.TestCase):
    """Test cases for dataset parameter operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    def test_update_powerbi_dataset_parameters_empty_list(self):
        """Test updating with empty parameter list"""
        with self.assertRaises(Exception) as context:
            self.client.update_powerbi_dataset_parameters("dataset-id", [])
        
        self.assertIn("cannot be empty", str(context.exception))
    
    def test_update_powerbi_dataset_parameters_too_many(self):
        """Test updating with too many parameters"""
        params = [{"name": f"param{i}", "newValue": "value"} for i in range(101)]
        
        with self.assertRaises(Exception) as context:
            self.client.update_powerbi_dataset_parameters("dataset-id", params)
        
        self.assertIn("Maximum of 100", str(context.exception))
    
    def test_update_powerbi_dataset_parameters_invalid_structure(self):
        """Test updating with invalid parameter structure"""
        params = [{"invalid_key": "value"}]
        
        with self.assertRaises(Exception) as context:
            self.client.update_powerbi_dataset_parameters("dataset-id", params)
        
        self.assertIn("must be a dictionary with 'name' and 'newValue'", str(context.exception))
    
    def test_update_powerbi_dataset_parameters_duplicate(self):
        """Test updating with duplicate parameters"""
        params = [
            {"name": "param1", "newValue": "value1"},
            {"name": "param1", "newValue": "value2"}
        ]
        
        with self.assertRaises(Exception) as context:
            self.client.update_powerbi_dataset_parameters("dataset-id", params)
        
        self.assertIn("duplicate", str(context.exception))
    
    @patch('powerbi_api.requests.request')
    def test_update_powerbi_dataset_parameters_success(self, mock_request):
        """Test successful parameter update"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b''
        mock_request.return_value = mock_response
        
        params = [{"name": "param1", "newValue": "value1"}]
        
        # Should not raise
        self.client.update_powerbi_dataset_parameters("dataset-id", params, workspace_id="ws-id")


class TestPowerBIAPIClientImportOperations(unittest.TestCase):
    """Test cases for import operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = PowerBIAPIClient()
        self.client._powerbi_token = Mock(token="test_token")
    
    @patch('powerbi_api.requests.request')
    def test_get_import(self, mock_request):
        """Test getting import status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"id": "import-id", "importState": "Succeeded"}'
        mock_response.json.return_value = {"id": "import-id", "importState": "Succeeded"}
        mock_request.return_value = mock_response
        
        result = self.client.get_import("import-id", workspace_id="ws-id")
        
        self.assertEqual(result["importState"], "Succeeded")


class TestCreatePowerBIClient(unittest.TestCase):
    """Test cases for create_powerbi_client function"""
    
    def test_create_powerbi_client_default(self):
        """Test creating client with defaults"""
        client = create_powerbi_client()
        
        self.assertIsInstance(client, PowerBIAPIClient)
        self.assertEqual(client.api_url, "https://api.powerbi.com/v1.0/myorg")
    
    def test_create_powerbi_client_custom(self):
        """Test creating client with custom URLs"""
        client = create_powerbi_client(
            api_url="https://custom.api.com",
            resource_url="https://custom.resource.com"
        )
        
        self.assertIsInstance(client, PowerBIAPIClient)
        self.assertEqual(client.api_url, "https://custom.api.com")
        self.assertEqual(client.resource_url, "https://custom.resource.com")


if __name__ == "__main__":
    unittest.main()
