"""
Unit tests for graph_api.py

Tests for GraphApiClient class and helper functions.
"""

import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import requests

from graph_api import GraphApiClient, GraphApiError, create_graph_client, detect_and_resolve_principal


class TestGraphApiError(unittest.TestCase):
    """Test cases for GraphApiError exception class"""
    
    def test_error_with_message_only(self):
        """Test error with message only"""
        error = GraphApiError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.response_data)
    
    def test_error_with_status_code(self):
        """Test error with status code"""
        error = GraphApiError("Test error", status_code=404)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertIsNone(error.response_data)
    
    def test_error_with_all_params(self):
        """Test error with all parameters"""
        response_data = {"error": {"code": "NotFound", "message": "Resource not found"}}
        error = GraphApiError("Test error", status_code=404, response_data=response_data)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.response_data, response_data)


class TestGraphApiClientInit(unittest.TestCase):
    """Test cases for GraphApiClient initialization"""
    
    @patch('graph_api.AzureCliCredential')
    def test_default_initialization(self, mock_credential):
        """Test default initialization"""
        client = GraphApiClient()
        self.assertEqual(client.api_url, "https://graph.microsoft.com/v1.0")
        self.assertEqual(client.resource_url, "https://graph.microsoft.com")
        self.assertEqual(client.timeout_sec, 60)
        mock_credential.assert_called_once()
    
    @patch('graph_api.AzureCliCredential')
    def test_custom_initialization(self, mock_credential):
        """Test custom initialization"""
        custom_credential = Mock()
        client = GraphApiClient(
            api_url="https://custom.graph.com/v2/",
            resource_url="https://custom.graph.com",
            credential=custom_credential,
            timeout_sec=30
        )
        self.assertEqual(client.api_url, "https://custom.graph.com/v2")
        self.assertEqual(client.resource_url, "https://custom.graph.com")
        self.assertEqual(client.timeout_sec, 30)
        self.assertEqual(client._credential, custom_credential)
        mock_credential.assert_not_called()


class TestGraphApiClientAuth(unittest.TestCase):
    """Test cases for GraphApiClient authentication"""
    
    def test_get_auth_token_success(self):
        """Test successful token retrieval"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        
        with patch('graph_api.AzureCliCredential', return_value=mock_credential):
            client = GraphApiClient()
            token = client._get_auth_token()
            
            self.assertEqual(token, "test_token")
            mock_credential.get_token.assert_called_once_with("https://graph.microsoft.com/.default")
    
    def test_get_auth_token_caches_token(self):
        """Test that token is cached on subsequent calls"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        
        with patch('graph_api.AzureCliCredential', return_value=mock_credential):
            client = GraphApiClient()
            token1 = client._get_auth_token()
            token2 = client._get_auth_token()
            
            self.assertEqual(token1, token2)
            # get_token should only be called once due to caching
            self.assertEqual(mock_credential.get_token.call_count, 1)
    
    def test_get_auth_token_failure(self):
        """Test token retrieval failure"""
        mock_credential = Mock()
        mock_credential.get_token.side_effect = Exception("Auth failed")
        
        with patch('graph_api.AzureCliCredential', return_value=mock_credential):
            client = GraphApiClient()
            with self.assertRaises(GraphApiError) as context:
                client._get_auth_token()
            
            self.assertIn("Failed to get authentication token", str(context.exception))


class TestGraphApiClientMakeRequest(unittest.TestCase):
    """Test cases for GraphApiClient._make_request method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('graph_api.requests.request')
    def test_make_request_get_success(self, mock_request):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            response = client._make_request("users")
            
            self.assertEqual(response.status_code, 200)
            mock_request.assert_called_once()
    
    @patch('graph_api.requests.request')
    def test_make_request_post_with_data(self, mock_request):
        """Test POST request with JSON data"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-id"}
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            data = {"displayName": "Test User"}
            response = client._make_request("users", method="POST", data=data)
            
            self.assertEqual(response.status_code, 201)
            call_args = mock_request.call_args
            self.assertEqual(call_args[1]['data'], json.dumps(data))
    
    @patch('graph_api.requests.request')
    def test_make_request_rate_limiting(self, mock_request):
        """Test rate limiting handling with retry"""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        rate_limit_response.content = b''
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [rate_limit_response, success_response]
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('graph_api.time.sleep'):  # Speed up test
                client = GraphApiClient()
                response = client._make_request("users")
                
                self.assertEqual(response.status_code, 200)
                self.assertEqual(mock_request.call_count, 2)
    
    @patch('graph_api.requests.request')
    def test_make_request_max_retries_exceeded(self, mock_request):
        """Test max retries exceeded"""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        rate_limit_response.content = b'{}'
        rate_limit_response.json.return_value = {}
        
        mock_request.return_value = rate_limit_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('graph_api.time.sleep'):  # Speed up test
                client = GraphApiClient()
                with self.assertRaises(GraphApiError) as context:
                    client._make_request("users", max_retries=2)
                
                self.assertIn("Rate limit exceeded", str(context.exception))
    
    @patch('graph_api.requests.request')
    def test_make_request_auth_error_retry(self, mock_request):
        """Test authentication error retry"""
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        auth_error_response.content = b''
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [auth_error_response, success_response]
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            response = client._make_request("users")
            
            self.assertEqual(response.status_code, 200)
    
    @patch('graph_api.requests.request')
    def test_make_request_client_error(self, mock_request):
        """Test client error handling"""
        error_response = Mock()
        error_response.status_code = 400
        error_response.content = b'{"error": {"message": "Bad request"}}'
        error_response.json.return_value = {"error": {"message": "Bad request"}}
        mock_request.return_value = error_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            with self.assertRaises(GraphApiError) as context:
                client._make_request("users")
            
            self.assertIn("Client error", str(context.exception))
            self.assertEqual(context.exception.status_code, 400)
    
    @patch('graph_api.requests.request')
    def test_make_request_server_error_retry(self, mock_request):
        """Test server error retry"""
        server_error_response = Mock()
        server_error_response.status_code = 500
        server_error_response.content = b''
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [server_error_response, success_response]
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('graph_api.time.sleep'):  # Speed up test
                client = GraphApiClient()
                response = client._make_request("users")
                
                self.assertEqual(response.status_code, 200)
    
    @patch('graph_api.requests.request')
    def test_make_request_timeout(self, mock_request):
        """Test timeout handling"""
        mock_request.side_effect = requests.Timeout("Request timed out")
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            with self.assertRaises(GraphApiError) as context:
                client._make_request("users")
            
            self.assertIn("timeout", str(context.exception).lower())
    
    @patch('graph_api.requests.request')
    def test_make_request_connection_error(self, mock_request):
        """Test connection error handling"""
        mock_request.side_effect = requests.ConnectionError("Connection failed")
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            with self.assertRaises(GraphApiError) as context:
                client._make_request("users")
            
            self.assertIn("Connection error", str(context.exception))


class TestGraphApiClientUserOperations(unittest.TestCase):
    """Test cases for user operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('graph_api.requests.request')
    def test_get_user_by_upn_found(self, mock_request):
        """Test getting user by UPN when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-id",
            "displayName": "Test User",
            "userPrincipalName": "user@contoso.com"
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            user = client.get_user_by_upn("user@contoso.com")
            
            self.assertIsNotNone(user)
            self.assertEqual(user["id"], "user-id")
            self.assertEqual(user["userPrincipalName"], "user@contoso.com")
    
    @patch('graph_api.requests.request')
    def test_get_user_by_upn_not_found(self, mock_request):
        """Test getting user by UPN when not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            user = client.get_user_by_upn("nonexistent@contoso.com")
            
            self.assertIsNone(user)
    
    @patch('graph_api.requests.request')
    def test_get_user_by_id_found(self, mock_request):
        """Test getting user by ID when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "displayName": "Test User",
            "userPrincipalName": "user@contoso.com"
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            user = client.get_user_by_id("12345678-1234-1234-1234-123456789abc")
            
            self.assertIsNotNone(user)
            self.assertEqual(user["displayName"], "Test User")
    
    @patch('graph_api.requests.request')
    def test_get_user_by_id_not_found(self, mock_request):
        """Test getting user by ID when not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            user = client.get_user_by_id("nonexistent-id")
            
            self.assertIsNone(user)


class TestGraphApiClientServicePrincipalOperations(unittest.TestCase):
    """Test cases for service principal operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('graph_api.requests.request')
    def test_get_service_principal_by_id_found(self, mock_request):
        """Test getting service principal by ID when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "sp-id",
            "displayName": "Test Service Principal",
            "appId": "app-id"
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            sp = client.get_service_principal_by_id("sp-id")
            
            self.assertIsNotNone(sp)
            self.assertEqual(sp["displayName"], "Test Service Principal")
    
    @patch('graph_api.requests.request')
    def test_get_service_principal_by_id_not_found(self, mock_request):
        """Test getting service principal by ID when not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            sp = client.get_service_principal_by_id("nonexistent-id")
            
            self.assertIsNone(sp)
    
    @patch('graph_api.requests.request')
    def test_get_service_principal_by_app_id_found(self, mock_request):
        """Test getting service principal by app ID when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{
                "id": "sp-id",
                "displayName": "Test Service Principal",
                "appId": "app-id"
            }]
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            sp = client.get_service_principal_by_app_id("app-id")
            
            self.assertIsNotNone(sp)
            self.assertEqual(sp["appId"], "app-id")
    
    @patch('graph_api.requests.request')
    def test_get_service_principal_by_app_id_not_found(self, mock_request):
        """Test getting service principal by app ID when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            sp = client.get_service_principal_by_app_id("nonexistent-app-id")
            
            self.assertIsNone(sp)


class TestGraphApiClientResolvePrincipal(unittest.TestCase):
    """Test cases for resolve_principal method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('graph_api.requests.request')
    def test_resolve_principal_service_principal_by_id(self, mock_request):
        """Test resolving service principal by object ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "displayName": "Test SP",
            "appId": "app-id"
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            principal_type, object_id, data = client.resolve_principal("12345678-1234-1234-1234-123456789abc")
            
            self.assertEqual(principal_type, "ServicePrincipal")
            self.assertEqual(object_id, "12345678-1234-1234-1234-123456789abc")
    
    @patch('graph_api.requests.request')
    def test_resolve_principal_user_by_upn(self, mock_request):
        """Test resolving user by UPN"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-id",
            "displayName": "Test User",
            "userPrincipalName": "user@contoso.com"
        }
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            principal_type, object_id, data = client.resolve_principal("user@contoso.com")
            
            self.assertEqual(principal_type, "User")
            self.assertEqual(object_id, "user-id")
    
    @patch('graph_api.requests.request')
    def test_resolve_principal_not_found(self, mock_request):
        """Test resolving principal that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with patch('graph_api.AzureCliCredential', return_value=self.mock_credential):
            client = GraphApiClient()
            with self.assertRaises(GraphApiError) as context:
                client.resolve_principal("nonexistent@contoso.com")
            
            self.assertIn("Unable to resolve principal identifier", str(context.exception))


class TestGraphApiHelperFunctions(unittest.TestCase):
    """Test cases for helper functions"""
    
    @patch('graph_api.AzureCliCredential')
    def test_create_graph_client(self, mock_credential):
        """Test creating a graph client"""
        client = create_graph_client()
        self.assertIsInstance(client, GraphApiClient)
    
    @patch('graph_api.AzureCliCredential')
    def test_create_graph_client_with_custom_credential(self, mock_azure_cred):
        """Test creating a graph client with custom credential"""
        custom_credential = Mock()
        client = create_graph_client(credential=custom_credential)
        self.assertIsInstance(client, GraphApiClient)
        self.assertEqual(client._credential, custom_credential)
    
    @patch('graph_api.requests.request')
    @patch('graph_api.AzureCliCredential')
    def test_detect_and_resolve_principal(self, mock_credential_class, mock_request):
        """Test detect_and_resolve_principal function"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-id",
            "displayName": "Test User",
            "userPrincipalName": "user@contoso.com"
        }
        mock_request.return_value = mock_response
        
        principal_type, object_id, data = detect_and_resolve_principal("user@contoso.com")
        
        self.assertEqual(principal_type, "User")
        self.assertEqual(object_id, "user-id")


class TestGraphApiClientGetHeaders(unittest.TestCase):
    """Test cases for get_headers method"""
    
    def test_get_headers(self):
        """Test getting headers with authorization"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token_123"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        
        with patch('graph_api.AzureCliCredential', return_value=mock_credential):
            client = GraphApiClient()
            headers = client.get_headers()
            
            self.assertIn("Authorization", headers)
            self.assertEqual(headers["Authorization"], "Bearer test_token_123")


if __name__ == "__main__":
    unittest.main()
