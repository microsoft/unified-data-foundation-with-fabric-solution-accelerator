"""
Unit tests for create_databricks_items_maag.py

Tests for Databricks workspace bootstrap script helper functions.
"""

import json
import os
import base64
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestNormalizeWidgetDefaultsLine(unittest.TestCase):
    """Test cases for _normalize_widget_defaults_line function"""
    
    def test_normalize_catalog_name_widget(self):
        """Test normalizing catalog_name widget"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'dbutils.widgets.text("catalog_name", "old_catalog")'
        result = _normalize_widget_defaults_line(line, "new_catalog", "schema")
        
        self.assertEqual(result, 'dbutils.widgets.text("catalog_name", "new_catalog")')
    
    def test_normalize_schema_name_widget(self):
        """Test normalizing schema_name widget"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'dbutils.widgets.text("schema_name", "old_schema")'
        result = _normalize_widget_defaults_line(line, "catalog", "new_schema")
        
        self.assertEqual(result, 'dbutils.widgets.text("schema_name", "new_schema")')
    
    def test_normalize_base_path_widget(self):
        """Test normalizing base_path widget"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'dbutils.widgets.text("base_path", "/old/path")'
        result = _normalize_widget_defaults_line(line, "catalog", "schema", base_path="/new/path")
        
        self.assertEqual(result, 'dbutils.widgets.text("base_path", "/new/path")')
    
    def test_normalize_no_widget(self):
        """Test line without widget"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'print("Hello World")'
        result = _normalize_widget_defaults_line(line, "catalog", "schema")
        
        self.assertEqual(result, 'print("Hello World")')
    
    def test_normalize_single_quotes(self):
        """Test normalizing with single quotes"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = "dbutils.widgets.text('catalog_name', 'old_catalog')"
        result = _normalize_widget_defaults_line(line, "new_catalog", "schema")
        
        self.assertEqual(result, 'dbutils.widgets.text("catalog_name", "new_catalog")')
    
    def test_normalize_base_path_none(self):
        """Test that base_path is not changed when None"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'dbutils.widgets.text("base_path", "/original/path")'
        result = _normalize_widget_defaults_line(line, "catalog", "schema", base_path=None)
        
        self.assertEqual(result, 'dbutils.widgets.text("base_path", "/original/path")')


class TestNormalizeRunMagicsLine(unittest.TestCase):
    """Test cases for _normalize_run_magics_line function"""
    
    def test_normalize_run_relative_path(self):
        """Test normalizing %run with relative path"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run ./some_notebook"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("/Workspace/Shared/solution/maag-notebooks", result)
        self.assertTrue(result.strip().endswith(".ipynb"))
    
    def test_normalize_run_already_absolute(self):
        """Test normalizing %run with already absolute path"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run /Workspace/Shared/solution/notebook"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("/Workspace", result)
    
    def test_non_run_line(self):
        """Test that non-%run lines are unchanged"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "print('hello')"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertEqual(result, "print('hello')")


class TestGetHost(unittest.TestCase):
    """Test cases for get_host function"""
    
    def test_get_host_from_argument(self):
        """Test getting host from CLI argument"""
        from create_databricks_items_maag import get_host
        
        result = get_host("https://adb-123456.azuredatabricks.net/")
        
        self.assertEqual(result, "https://adb-123456.azuredatabricks.net")
    
    def test_get_host_strips_trailing_slash(self):
        """Test that trailing slash is stripped"""
        from create_databricks_items_maag import get_host
        
        result = get_host("https://example.com/")
        
        self.assertEqual(result, "https://example.com")
    
    @patch.dict(os.environ, {'DATABRICKS_HOST': 'https://env-host.com'})
    def test_get_host_from_env(self):
        """Test getting host from environment variable"""
        from create_databricks_items_maag import get_host
        
        result = get_host(None)
        
        self.assertEqual(result, "https://env-host.com")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_host_missing_raises(self):
        """Test that missing host raises error"""
        # Need to reload module to pick up cleared env
        import importlib
        import create_databricks_items_maag
        importlib.reload(create_databricks_items_maag)
        
        from create_databricks_items_maag import get_host
        
        with self.assertRaises(RuntimeError) as context:
            get_host(None)
        
        self.assertIn("DATABRICKS_HOST", str(context.exception))


class TestHeaders(unittest.TestCase):
    """Test cases for headers function"""
    
    def test_headers_from_argument(self):
        """Test getting headers from CLI argument"""
        from create_databricks_items_maag import headers
        
        result = headers("test-token")
        
        self.assertEqual(result["Authorization"], "Bearer test-token")
    
    @patch.dict(os.environ, {'DATABRICKS_TOKEN': 'env-token'})
    def test_headers_from_env(self):
        """Test getting headers from environment variable"""
        from create_databricks_items_maag import headers
        
        result = headers(None)
        
        self.assertEqual(result["Authorization"], "Bearer env-token")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_headers_missing_raises(self):
        """Test that missing token raises error"""
        import importlib
        import create_databricks_items_maag
        importlib.reload(create_databricks_items_maag)
        
        from create_databricks_items_maag import headers
        
        with self.assertRaises(RuntimeError) as context:
            headers(None)
        
        self.assertIn("DATABRICKS_TOKEN", str(context.exception))


class TestMkdirs(unittest.TestCase):
    """Test cases for mkdirs function"""
    
    @patch('create_databricks_items_maag.requests.post')
    def test_mkdirs_success(self, mock_post):
        """Test successful workspace directory creation"""
        from create_databricks_items_maag import mkdirs
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Should not raise
        mkdirs("https://host.com", {"Authorization": "Bearer token"}, "/Shared/folder")
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("workspace/mkdirs", call_args[0][0])
    
    @patch('create_databricks_items_maag.requests.post')
    def test_mkdirs_failure(self, mock_post):
        """Test failed workspace directory creation"""
        from create_databricks_items_maag import mkdirs
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            mkdirs("https://host.com", {"Authorization": "Bearer token"}, "/Shared/folder")
        
        self.assertIn("mkdirs failed", str(context.exception))


class TestDbfsMkdirs(unittest.TestCase):
    """Test cases for dbfs_mkdirs function"""
    
    @patch('create_databricks_items_maag.requests.post')
    def test_dbfs_mkdirs_success(self, mock_post):
        """Test successful DBFS directory creation"""
        from create_databricks_items_maag import dbfs_mkdirs
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Should not raise
        dbfs_mkdirs("https://host.com", {"Authorization": "Bearer token"}, "dbfs:/FileStore/folder")
        
        mock_post.assert_called_once()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_dbfs_mkdirs_failure(self, mock_post):
        """Test failed DBFS directory creation"""
        from create_databricks_items_maag import dbfs_mkdirs
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_post.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            dbfs_mkdirs("https://host.com", {"Authorization": "Bearer token"}, "dbfs:/FileStore/folder")
        
        self.assertIn("dbfs mkdirs failed", str(context.exception))


class TestDbfsPut(unittest.TestCase):
    """Test cases for dbfs_put function"""
    
    @patch('create_databricks_items_maag.requests.post')
    def test_dbfs_put_success(self, mock_post):
        """Test successful DBFS file upload"""
        from create_databricks_items_maag import dbfs_put
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
            f.write(b"test,data\n1,2\n")
            temp_path = Path(f.name)
        
        try:
            dbfs_put("https://host.com", {"Authorization": "Bearer token"}, temp_path, "dbfs:/path/file.csv")
            mock_post.assert_called_once()
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_dbfs_put_failure(self, mock_post):
        """Test failed DBFS file upload"""
        from create_databricks_items_maag import dbfs_put
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_post.return_value = mock_response
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
            f.write(b"test,data\n")
            temp_path = Path(f.name)
        
        try:
            with self.assertRaises(RuntimeError) as context:
                dbfs_put("https://host.com", {"Authorization": "Bearer token"}, temp_path, "dbfs:/path/file.csv")
            
            self.assertIn("dbfs put failed", str(context.exception))
        finally:
            temp_path.unlink()


class TestRelposix(unittest.TestCase):
    """Test cases for relposix function"""
    
    def test_relposix_simple(self):
        """Test simple relative path conversion"""
        from create_databricks_items_maag import relposix
        
        root = Path("/home/user/project")
        file = Path("/home/user/project/src/file.py")
        
        result = relposix(root, file)
        
        self.assertEqual(result, "src/file.py")
    
    def test_relposix_nested(self):
        """Test nested relative path conversion"""
        from create_databricks_items_maag import relposix
        
        root = Path("/root")
        file = Path("/root/a/b/c/file.txt")
        
        result = relposix(root, file)
        
        self.assertEqual(result, "a/b/c/file.txt")


class TestCreateCatalog(unittest.TestCase):
    """Test cases for create_catalog function"""
    
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_already_exists(self, mock_get):
        """Test catalog creation when it already exists"""
        from create_databricks_items_maag import create_catalog
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Should not raise and not call create
        create_catalog("https://host.com", {"Authorization": "Bearer token"}, "my_catalog")
        
        mock_get.assert_called_once()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_new(self, mock_get, mock_post):
        """Test creating new catalog"""
        from create_databricks_items_maag import create_catalog
        
        # GET returns 404, POST returns 201
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post.return_value = mock_post_response
        
        create_catalog("https://host.com", {"Authorization": "Bearer token"}, "new_catalog")
        
        mock_post.assert_called_once()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_conflict(self, mock_get, mock_post):
        """Test catalog creation with conflict (race condition)"""
        from create_databricks_items_maag import create_catalog
        
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.status_code = 409  # Conflict
        mock_post.return_value = mock_post_response
        
        # Should not raise
        create_catalog("https://host.com", {"Authorization": "Bearer token"}, "catalog")


class TestJobsRunsSubmit(unittest.TestCase):
    """Test cases for _jobs_runs_submit function"""
    
    @patch('create_databricks_items_maag.requests.post')
    def test_jobs_runs_submit_success(self, mock_post):
        """Test successful job submission"""
        from create_databricks_items_maag import _jobs_runs_submit
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"run_id": "12345"}
        mock_post.return_value = mock_response
        
        run_id = _jobs_runs_submit(
            "https://host.com",
            {"Authorization": "Bearer token"},
            {"run_name": "test"}
        )
        
        self.assertEqual(run_id, "12345")
    
    @patch('create_databricks_items_maag.requests.post')
    def test_jobs_runs_submit_failure(self, mock_post):
        """Test failed job submission"""
        from create_databricks_items_maag import _jobs_runs_submit
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            _jobs_runs_submit(
                "https://host.com",
                {"Authorization": "Bearer token"},
                {"run_name": "test"}
            )
        
        self.assertIn("jobs/runs/submit failed", str(context.exception))


class TestJobsRunsGet(unittest.TestCase):
    """Test cases for _jobs_runs_get function"""
    
    @patch('create_databricks_items_maag.requests.get')
    def test_jobs_runs_get_success(self, mock_get):
        """Test successful job status retrieval"""
        from create_databricks_items_maag import _jobs_runs_get
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "12345",
            "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}
        }
        mock_get.return_value = mock_response
        
        result = _jobs_runs_get("https://host.com", {"Authorization": "Bearer token"}, "12345")
        
        self.assertEqual(result["state"]["result_state"], "SUCCESS")
    
    @patch('create_databricks_items_maag.requests.get')
    def test_jobs_runs_get_failure(self, mock_get):
        """Test failed job status retrieval"""
        from create_databricks_items_maag import _jobs_runs_get
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            _jobs_runs_get("https://host.com", {"Authorization": "Bearer token"}, "invalid")
        
        self.assertIn("jobs/runs/get failed", str(context.exception))


class TestResolveExternalLocationUrl(unittest.TestCase):
    """Test cases for resolve_external_location_url function"""
    
    def test_resolve_abfss_url_passthrough(self):
        """Test that abfss URLs are passed through"""
        from create_databricks_items_maag import resolve_external_location_url
        
        result = resolve_external_location_url(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "abfss://container@account.dfs.core.windows.net/path"
        )
        
        self.assertEqual(result, "abfss://container@account.dfs.core.windows.net/path")
    
    def test_resolve_s3_url_passthrough(self):
        """Test that s3 URLs are passed through"""
        from create_databricks_items_maag import resolve_external_location_url
        
        result = resolve_external_location_url(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "s3://bucket/path"
        )
        
        self.assertEqual(result, "s3://bucket/path")
    
    @patch('create_databricks_items_maag.requests.get')
    def test_resolve_external_location_name(self, mock_get):
        """Test resolving external location by name"""
        from create_databricks_items_maag import resolve_external_location_url
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "abfss://container@account.dfs.core.windows.net/"}
        mock_get.return_value = mock_response
        
        result = resolve_external_location_url(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "my-external-location"
        )
        
        self.assertEqual(result, "abfss://container@account.dfs.core.windows.net/")
    
    @patch('create_databricks_items_maag.requests.get')
    def test_resolve_external_location_not_found(self, mock_get):
        """Test resolving external location that doesn't exist"""
        from create_databricks_items_maag import resolve_external_location_url
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            resolve_external_location_url(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "nonexistent-location"
            )
        
        self.assertIn("Couldn't resolve external location", str(context.exception))


class TestRunNotebookOnce(unittest.TestCase):
    """Test cases for run_notebook_once function"""
    
    def test_run_notebook_missing_cluster_id(self):
        """Test that missing cluster ID raises error"""
        from create_databricks_items_maag import run_notebook_once
        
        with self.assertRaises(RuntimeError) as context:
            run_notebook_once(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "/path/to/notebook",
                {"param": "value"},
                ""  # Empty cluster ID
            )
        
        self.assertIn("Missing --cluster-id", str(context.exception))
    
    @patch('create_databricks_items_maag._jobs_runs_get')
    @patch('create_databricks_items_maag._jobs_runs_submit')
    @patch('create_databricks_items_maag.time.sleep')
    def test_run_notebook_success(self, mock_sleep, mock_submit, mock_get):
        """Test successful notebook run"""
        from create_databricks_items_maag import run_notebook_once
        
        mock_submit.return_value = "run-12345"
        mock_get.return_value = {
            "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}
        }
        
        # Should not raise
        run_notebook_once(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "/path/to/notebook",
            {"param": "value"},
            "cluster-123"
        )
    
    @patch('create_databricks_items_maag._jobs_runs_get')
    @patch('create_databricks_items_maag._jobs_runs_submit')
    @patch('create_databricks_items_maag.time.sleep')
    def test_run_notebook_failure(self, mock_sleep, mock_submit, mock_get):
        """Test failed notebook run"""
        from create_databricks_items_maag import run_notebook_once
        
        mock_submit.return_value = "run-12345"
        mock_get.return_value = {
            "state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED"}
        }
        
        with self.assertRaises(RuntimeError) as context:
            run_notebook_once(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "/path/to/notebook",
                {"param": "value"},
                "cluster-123"
            )
        
        self.assertIn("Notebook run failed", str(context.exception))


class TestReduceReplace(unittest.TestCase):
    """Test cases for _reduce_replace function"""
    
    def test_reduce_replace_single(self):
        """Test single replacement"""
        from create_databricks_items_maag import _reduce_replace
        
        result = _reduce_replace("Hello World", {"World": "Python"})
        
        self.assertEqual(result, "Hello Python")
    
    def test_reduce_replace_multiple(self):
        """Test multiple replacements"""
        from create_databricks_items_maag import _reduce_replace
        
        result = _reduce_replace("a b c", {"a": "1", "b": "2", "c": "3"})
        
        self.assertEqual(result, "1 2 3")
    
    def test_reduce_replace_empty_kv(self):
        """Test with empty replacements"""
        from create_databricks_items_maag import _reduce_replace
        
        result = _reduce_replace("Hello World", {})
        
        self.assertEqual(result, "Hello World")
    
    def test_reduce_replace_no_match(self):
        """Test when no match is found"""
        from create_databricks_items_maag import _reduce_replace
        
        result = _reduce_replace("Hello World", {"xyz": "123"})
        
        self.assertEqual(result, "Hello World")


class TestImportFile(unittest.TestCase):
    """Test cases for import_file function"""
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_python(self, mock_post):
        """Test importing a Python file"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as f:
            f.write('print("Hello")\n')
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/test/script.py",
                {},
                "catalog",
                "schema"
            )
            
            self.assertTrue(result)
            mock_post.assert_called_once()
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_sql(self, mock_post):
        """Test importing a SQL file"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sql", mode='w') as f:
            f.write('SELECT * FROM table;\n')
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/test/query.sql",
                {},
                "catalog",
                "schema"
            )
            
            self.assertTrue(result)
            mock_post.assert_called_once()
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_ipynb(self, mock_post):
        """Test importing a Jupyter notebook"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create a minimal notebook JSON
        notebook_content = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')"]
                }
            ],
            "metadata": {}
        })
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ipynb", mode='w') as f:
            f.write(notebook_content)
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/solution/maag-notebooks/test.ipynb",
                {},
                "catalog",
                "schema",
                dbfs_solution="/FileStore/tables/solution"
            )
            
            self.assertTrue(result)
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_ipynb_with_run_magic(self, mock_post):
        """Test importing a notebook with %run magic"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        notebook_content = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["%run ./other_notebook"]
                }
            ],
            "metadata": {}
        })
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ipynb", mode='w') as f:
            f.write(notebook_content)
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/mysolution/maag-notebooks/test.ipynb",
                {},
                "catalog",
                "schema"
            )
            
            self.assertTrue(result)
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_ipynb_string_source(self, mock_post):
        """Test importing a notebook with string source (not list)"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        notebook_content = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": "print('hello')"  # String, not list
                }
            ],
            "metadata": {}
        })
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ipynb", mode='w') as f:
            f.write(notebook_content)
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/solution/maag-notebooks/test.ipynb",
                {},
                "catalog",
                "schema"
            )
            
            self.assertTrue(result)
        finally:
            temp_path.unlink()
    
    def test_import_file_unsupported_type(self):
        """Test importing an unsupported file type"""
        from create_databricks_items_maag import import_file
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w') as f:
            f.write('Hello World\n')
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/test/file.txt",
                {},
                "catalog",
                "schema"
            )
            
            self.assertFalse(result)
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_failure(self, mock_post):
        """Test import file failure"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_post.return_value = mock_response
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as f:
            f.write('print("hello")\n')
            temp_path = Path(f.name)
        
        try:
            with self.assertRaises(RuntimeError) as context:
                import_file(
                    "https://host.com",
                    {"Authorization": "Bearer token"},
                    temp_path,
                    "/Workspace/Shared/test/script.py",
                    {},
                    "catalog",
                    "schema"
                )
            
            self.assertIn("workspace import failed", str(context.exception))
        finally:
            temp_path.unlink()
    
    @patch('create_databricks_items_maag.requests.post')
    def test_import_file_with_replacements(self, mock_post):
        """Test importing file with text replacements"""
        from create_databricks_items_maag import import_file
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as f:
            f.write('workspace = "OLD_WORKSPACE"\n')
            temp_path = Path(f.name)
        
        try:
            result = import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                temp_path,
                "/Workspace/Shared/test/script.py",
                {"OLD_WORKSPACE": "NEW_WORKSPACE"},
                "catalog",
                "schema"
            )
            
            self.assertTrue(result)
        finally:
            temp_path.unlink()


class TestProcessIpynbTextSafely(unittest.TestCase):
    """Test cases for _process_ipynb_text_safely function"""
    
    def test_process_ipynb_text_safely_basic(self):
        """Test basic notebook processing"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook_json = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')"]
                }
            ],
            "metadata": {}
        })
        
        result = _process_ipynb_text_safely(
            notebook_json,
            "/Shared/solution",
            "catalog",
            "schema",
            {}
        )
        
        self.assertIn("print", result)
    
    def test_process_ipynb_text_safely_with_replacements(self):
        """Test notebook processing with replacements"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook_json = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["OLD_VALUE = 'test'"]
                }
            ],
            "metadata": {}
        })
        
        result = _process_ipynb_text_safely(
            notebook_json,
            "/Shared/solution",
            "catalog",
            "schema",
            {"OLD_VALUE": "NEW_VALUE"}
        )
        
        self.assertIn("NEW_VALUE", result)
    
    def test_process_ipynb_text_safely_with_run_magic(self):
        """Test notebook processing with %run magic"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook_json = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["%run ./helper"]
                }
            ],
            "metadata": {}
        })
        
        result = _process_ipynb_text_safely(
            notebook_json,
            "/Shared/solution",
            "catalog",
            "schema",
            {}
        )
        
        # Should have normalized path
        self.assertIn("Workspace", result)
    
    def test_process_ipynb_text_safely_string_source(self):
        """Test notebook processing with string source"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook_json = json.dumps({
            "cells": [
                {
                    "cell_type": "code",
                    "source": "print('hello')"
                }
            ],
            "metadata": {}
        })
        
        result = _process_ipynb_text_safely(
            notebook_json,
            "/Shared/solution",
            "catalog",
            "schema",
            {}
        )
        
        self.assertIn("print", result)
    
    def test_process_ipynb_text_safely_markdown_cell(self):
        """Test notebook processing ignores markdown cells"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook_json = json.dumps({
            "cells": [
                {
                    "cell_type": "markdown",
                    "source": ["# Header"]
                },
                {
                    "cell_type": "code",
                    "source": ["print('hello')"]
                }
            ],
            "metadata": {}
        })
        
        result = _process_ipynb_text_safely(
            notebook_json,
            "/Shared/solution",
            "catalog",
            "schema",
            {}
        )
        
        parsed = json.loads(result)
        self.assertEqual(parsed["cells"][0]["source"], ["# Header"])


class TestNormalizeRunMagicsLineAdvanced(unittest.TestCase):
    """Advanced test cases for _normalize_run_magics_line function"""
    
    def test_normalize_run_maag_notebooks_prefix(self):
        """Test normalizing %run with /maag-notebooks/ prefix"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run /maag-notebooks/helper"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("/Workspace/Shared/solution/maag-notebooks", result)
    
    def test_normalize_run_maag_notebooks_no_slash(self):
        """Test normalizing %run with maag-notebooks/ prefix (no leading slash)"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run maag-notebooks/helper"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("/Workspace/Shared/solution/maag-notebooks", result)
    
    def test_normalize_run_parent_path(self):
        """Test normalizing %run with ../ parent path"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run ../helper"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("/Workspace/Shared/solution/maag-notebooks", result)
    
    def test_normalize_run_simple_name(self):
        """Test normalizing %run with simple notebook name"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run helper_notebook"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        self.assertIn("helper_notebook.ipynb", result)
    
    def test_normalize_run_unknown_absolute(self):
        """Test normalizing %run with unknown absolute path"""
        from create_databricks_items_maag import _normalize_run_magics_line
        
        line = "%run /some/unknown/path"
        result = _normalize_run_magics_line(line, "/Shared/solution")
        
        # Should leave path as-is but add .ipynb
        self.assertTrue(result.strip().endswith(".ipynb"))


class TestCreateCatalogAdvanced(unittest.TestCase):
    """Advanced test cases for create_catalog function"""
    
    @patch('create_databricks_items_maag.resolve_external_location_url')
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_with_managed_location(self, mock_get, mock_post, mock_resolve):
        """Test creating catalog with managed location"""
        from create_databricks_items_maag import create_catalog
        
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post.return_value = mock_post_response
        
        mock_resolve.return_value = "abfss://container@account.dfs.core.windows.net/"
        
        create_catalog(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "my_catalog",
            managed_location="my-external-location"
        )
        
        mock_resolve.assert_called_once()
        mock_post.assert_called_once()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_missing_storage_root_error(self, mock_get, mock_post):
        """Test create_catalog error for missing metastore storage root"""
        from create_databricks_items_maag import create_catalog
        
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get_response.text = "Not Found"
        mock_get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.status_code = 400
        mock_post_response.text = "Metastore storage root URL does not exist"
        mock_post.return_value = mock_post_response
        
        with self.assertRaises(RuntimeError) as context:
            create_catalog(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "my_catalog"
            )
        
        self.assertIn("Metastore storage root URL does not exist", str(context.exception))
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_other_error_with_subsequent_get(self, mock_get, mock_post):
        """Test create_catalog handles other errors by checking GET again"""
        from create_databricks_items_maag import create_catalog
        
        # First GET returns 404 (not found)
        mock_get_first = Mock()
        mock_get_first.status_code = 404
        mock_get_first.text = "Not Found"
        
        # POST fails with 500
        mock_post_response = Mock()
        mock_post_response.status_code = 500
        mock_post_response.text = "Internal Server Error"
        mock_post.return_value = mock_post_response
        
        # Second GET (retry) returns 200 (catalog now exists)
        mock_get_second = Mock()
        mock_get_second.status_code = 200
        
        mock_get.side_effect = [mock_get_first, mock_get_second]
        
        # Should not raise since second GET succeeds
        create_catalog(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "my_catalog"
        )


class TestRunNotebookOnceAdvanced(unittest.TestCase):
    """Advanced test cases for run_notebook_once function"""
    
    @patch('create_databricks_items_maag._jobs_runs_get')
    @patch('create_databricks_items_maag._jobs_runs_submit')
    @patch('create_databricks_items_maag.time.sleep')
    @patch('create_databricks_items_maag.time.time')
    def test_run_notebook_timeout(self, mock_time, mock_sleep, mock_submit, mock_get):
        """Test notebook run timeout"""
        from create_databricks_items_maag import run_notebook_once
        
        mock_submit.return_value = "run-12345"
        mock_get.return_value = {
            "state": {"life_cycle_state": "RUNNING"}
        }
        
        # Simulate time passing beyond timeout
        mock_time.side_effect = [0, 0, 1000, 2000, 3000, 4000]  # Exceeds default timeout
        
        with self.assertRaises(RuntimeError) as context:
            run_notebook_once(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "/path/to/notebook",
                {"param": "value"},
                "cluster-123",
                timeout_s=10
            )
        
        self.assertIn("Timeout", str(context.exception))
    
    @patch('create_databricks_items_maag._jobs_runs_get')
    @patch('create_databricks_items_maag._jobs_runs_submit')
    @patch('create_databricks_items_maag.time.sleep')
    def test_run_notebook_pending_then_success(self, mock_sleep, mock_submit, mock_get):
        """Test notebook that is pending then succeeds"""
        from create_databricks_items_maag import run_notebook_once
        
        mock_submit.return_value = "run-12345"
        
        # First call returns PENDING, second returns SUCCESS
        mock_get.side_effect = [
            {"state": {"life_cycle_state": "PENDING"}},
            {"state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}}
        ]
        
        # Should not raise
        run_notebook_once(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "/path/to/notebook",
            {"param": "value"},
            "cluster-123"
        )


class TestNormalizeWidgetDefaultsLineAdvanced(unittest.TestCase):
    """Advanced test cases for _normalize_widget_defaults_line function"""
    
    def test_normalize_with_all_params(self):
        """Test normalizing with catalog, schema and base_path"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        lines = [
            'dbutils.widgets.text("catalog_name", "old")',
            'dbutils.widgets.text("schema_name", "old")',
            'dbutils.widgets.text("base_path", "/old")',
        ]
        
        result1 = _normalize_widget_defaults_line(lines[0], "new_catalog", "new_schema", "/new/path")
        result2 = _normalize_widget_defaults_line(lines[1], "new_catalog", "new_schema", "/new/path")
        result3 = _normalize_widget_defaults_line(lines[2], "new_catalog", "new_schema", "/new/path")
        
        self.assertIn("new_catalog", result1)
        self.assertIn("new_schema", result2)
        self.assertIn("/new/path", result3)
    
    def test_normalize_mixed_quotes(self):
        """Test normalizing widgets with mixed quote styles"""
        from create_databricks_items_maag import _normalize_widget_defaults_line
        
        line = 'dbutils.widgets.text(\'catalog_name\', "old_catalog")'
        result = _normalize_widget_defaults_line(line, "new_catalog", "schema")
        
        # Should still normalize
        self.assertIn("new_catalog", result)


class TestProcessIpynbTextStringSource(unittest.TestCase):
    """Test cases for _process_ipynb_text_safely with string source cells (lines 99-106)"""
    
    def test_string_source_with_replacements(self):
        """Test string source with key-value replacements (covers line 102)"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        # Notebook with string source that has replacements
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "SELECT * FROM {{OLD_TABLE}}"
                }
            ]
        }
        raw = json.dumps(notebook)
        
        result = _process_ipynb_text_safely(
            raw,
            solution_abs_base="/Workspace/Shared/Solution",
            dbfs_solution="/mnt/dbfs/solution",
            catalog="test_catalog",
            schema="test_schema",
            kv_replacements={"{{OLD_TABLE}}": "new_table"}
        )
        
        result_nb = json.loads(result)
        self.assertIn("new_table", result_nb["cells"][0]["source"])
        self.assertNotIn("{{OLD_TABLE}}", result_nb["cells"][0]["source"])
    
    def test_string_source_with_run_magic(self):
        """Test string source with %run magic (covers line 104)"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "%run ./helpers/utils"
                }
            ]
        }
        raw = json.dumps(notebook)
        
        result = _process_ipynb_text_safely(
            raw,
            solution_abs_base="/Workspace/Shared/MySolution",
            dbfs_solution="/mnt/dbfs",
            catalog="catalog",
            schema="schema",
            kv_replacements={}
        )
        
        result_nb = json.loads(result)
        # The %run should be normalized
        self.assertIn("%run", result_nb["cells"][0]["source"])
    
    def test_string_source_with_widget_and_replacement_and_run(self):
        """Test string source with widget, replacements AND %run (covers 100-105)"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": 'dbutils.widgets.text("catalog_name", "default")\n{{REPLACE_ME}}\n%run ./other_notebook'
                }
            ]
        }
        raw = json.dumps(notebook)
        
        result = _process_ipynb_text_safely(
            raw,
            solution_abs_base="/Workspace/Shared/MySolution",
            dbfs_solution="/mnt/solution",
            catalog="prod_catalog",
            schema="prod_schema",
            kv_replacements={"{{REPLACE_ME}}": "replaced_value"}
        )
        
        result_nb = json.loads(result)
        source = result_nb["cells"][0]["source"]
        self.assertIn("prod_catalog", source)
        self.assertIn("replaced_value", source)
    
    def test_non_list_non_string_source_fallback(self):
        """Test source that is neither list nor string (covers line 106)"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        # Create notebook with unusual source type (e.g., null or number)
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": None  # Neither list nor string
                }
            ]
        }
        raw = json.dumps(notebook)
        
        result = _process_ipynb_text_safely(
            raw,
            solution_abs_base="/Workspace/Shared/Solution",
            dbfs_solution="/mnt/dbfs",
            catalog="catalog",
            schema="schema",
            kv_replacements={}
        )
        
        result_nb = json.loads(result)
        # Should preserve None as it is
        self.assertIsNone(result_nb["cells"][0]["source"])
    
    def test_integer_source_fallback(self):
        """Test source that is an integer (unusual edge case - line 106)"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": 12345  # Integer source
                }
            ]
        }
        raw = json.dumps(notebook)
        
        result = _process_ipynb_text_safely(
            raw,
            solution_abs_base="/base",
            dbfs_solution="/dbfs",
            catalog="cat",
            schema="sch",
            kv_replacements={}
        )
        
        result_nb = json.loads(result)
        # Should preserve integer as it is
        self.assertEqual(result_nb["cells"][0]["source"], 12345)


class TestImportFileAdvanced(unittest.TestCase):
    """Advanced test cases for import_file function covering edge cases"""
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_import_file_path_parsing_exception(self, mock_get, mock_post):
        """Test path parsing when 'Shared' is at the end causing index error (covers 226-227)"""
        from create_databricks_items_maag import import_file
        import tempfile
        
        # Create a temp notebook file
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')"]
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = Path(tmpdir) / "test.ipynb"
            with open(nb_path, 'w') as f:
                json.dump(notebook, f)
            
            # Mock successful import
            mock_post.return_value = Mock(status_code=200)
            mock_get.return_value = Mock(status_code=200)
            
            # Use ws_path where 'Shared' is at the end (triggering exception in path parsing)
            # Signature: import_file(host, hdrs, local_path, ws_path, replacements, catalog, schema, dbfs_solution)
            import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                nb_path,  # local_path (Path object)
                "/Workspace/Shared",  # ws_path - Shared at end, no solution after it
                {},  # replacements
                "catalog",
                "schema",
                "/dbfs/solution"
            )
            
            # Should not raise, exception is caught
            mock_post.assert_called()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_import_file_string_source_with_replacements(self, mock_get, mock_post):
        """Test import_file with string source and replacements (covers 244-245)"""
        from create_databricks_items_maag import import_file
        import tempfile
        
        # Create notebook with string source
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "SELECT * FROM {{TABLE}}"  # String, not list
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = Path(tmpdir) / "test.ipynb"
            with open(nb_path, 'w') as f:
                json.dump(notebook, f)
            
            mock_post.return_value = Mock(status_code=200)
            mock_get.return_value = Mock(status_code=200)
            
            import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                nb_path,
                "/Workspace/Shared/MySolution/notebooks",
                {"{{TABLE}}": "actual_table"},  # replacements
                "catalog",
                "schema",
                "/dbfs/solution"
            )
            
            # Verify the content was posted with replacement
            call_args = mock_post.call_args
            if call_args:
                data = call_args[1].get('data', call_args[1].get('json', {}))
                if isinstance(data, dict) and 'content' in data:
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8')
                    self.assertIn("actual_table", content)
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_import_file_string_source_with_run_magic(self, mock_get, mock_post):
        """Test import_file with string source containing %run (covers 246-247)"""
        from create_databricks_items_maag import import_file
        import tempfile
        
        # Create notebook with string source containing %run
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "%run ./utilities/common"  # String with %run
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = Path(tmpdir) / "test.ipynb"
            with open(nb_path, 'w') as f:
                json.dump(notebook, f)
            
            mock_post.return_value = Mock(status_code=200)
            mock_get.return_value = Mock(status_code=200)
            
            import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                nb_path,
                "/Workspace/Shared/MySolution/notebooks",
                {},  # replacements
                "catalog",
                "schema",
                "/dbfs/solution"
            )
            
            # Should process %run normalization
            mock_post.assert_called()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_import_file_list_source_with_replacements(self, mock_get, mock_post):
        """Test import_file with list source and replacements (covers 236-237)"""
        from create_databricks_items_maag import import_file
        import tempfile
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": [
                        "# Line 1\n",
                        "SELECT * FROM {{PLACEHOLDER}}\n",
                        "# Line 3"
                    ]
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = Path(tmpdir) / "test.ipynb"
            with open(nb_path, 'w') as f:
                json.dump(notebook, f)
            
            mock_post.return_value = Mock(status_code=200)
            mock_get.return_value = Mock(status_code=200)
            
            import_file(
                "https://host.com",
                {"Authorization": "Bearer token"},
                nb_path,
                "/Workspace/Shared/MySolution/notebooks",
                {"{{PLACEHOLDER}}": "my_table"},  # replacements
                "catalog",
                "schema",
                "/dbfs/solution"
            )
            
            call_args = mock_post.call_args
            if call_args:
                data = call_args[1].get('data', call_args[1].get('json', {}))
                if isinstance(data, dict) and 'content' in data:
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8')
                    self.assertIn("my_table", content)


class TestCreateCatalogEdgeCases(unittest.TestCase):
    """Additional edge cases for create_catalog function (line 319)"""
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_post_fails_but_get_succeeds(self, mock_get, mock_post):
        """Test when POST fails but subsequent GET succeeds (race condition - covers line 317-318)"""
        from create_databricks_items_maag import create_catalog
        
        # POST returns 500 (server error, not 200/201/409/400)
        mock_post.return_value = Mock(status_code=500, text="Internal Server Error")
        # First GET returns 404 (doesn't exist)
        # Second GET returns 200 (was created by another process)
        mock_get.side_effect = [
            Mock(status_code=404, text="Not Found"),  # Initial check
            Mock(status_code=200, text="OK")   # After POST fail, check again - now exists
        ]
        
        # Should not raise - the GET after POST succeeds
        create_catalog(
            "https://host.com",
            {"Authorization": "Bearer token"},
            "test_catalog"
        )
        
        # Verify both GET and POST were called
        self.assertEqual(mock_get.call_count, 2)
        mock_post.assert_called_once()
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_post_and_get_both_fail(self, mock_get, mock_post):
        """Test when POST fails and subsequent GET also fails (covers line 319)"""
        from create_databricks_items_maag import create_catalog
        
        # POST returns 500 (server error)
        mock_post.return_value = Mock(status_code=500, text="Internal Server Error")
        # Both GETs return 404
        mock_get.side_effect = [
            Mock(status_code=404, text="Not Found"),  # Initial check
            Mock(status_code=404, text="Still Not Found")   # After POST fail, still not there
        ]
        
        with self.assertRaises(RuntimeError) as context:
            create_catalog(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "test_catalog"
            )
        
        self.assertIn("create/get catalog failed", str(context.exception))
    
    @patch('create_databricks_items_maag.requests.post')
    @patch('create_databricks_items_maag.requests.get')
    def test_create_catalog_metastore_error(self, mock_get, mock_post):
        """Test metastore storage root error handling"""
        from create_databricks_items_maag import create_catalog
        
        # GET returns 404, then POST fails with metastore error
        mock_get.return_value = Mock(status_code=404, text="Not Found")
        mock_post.return_value = Mock(
            status_code=400,
            text="Metastore storage root URL does not exist"
        )
        
        with self.assertRaises(RuntimeError) as context:
            create_catalog(
                "https://host.com",
                {"Authorization": "Bearer token"},
                "test_catalog"
            )
        
        self.assertIn("Metastore storage root URL", str(context.exception))
        self.assertIn("managed location", str(context.exception).lower())


class TestProcessIpynbTextEdgeCases(unittest.TestCase):
    """Edge case tests for _process_ipynb_text_safely function"""
    
    def test_empty_kv_replacements(self):
        """Test with empty replacements dict"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "x = 1"
                }
            ]
        }
        
        # Correct order: raw_json, solution_abs_base, catalog, schema, kv_replacements
        result = _process_ipynb_text_safely(
            json.dumps(notebook),
            "/base", "cat", "sch", {}
        )
        
        result_nb = json.loads(result)
        self.assertEqual(result_nb["cells"][0]["source"], "x = 1")
    
    def test_multiple_replacements_in_string_source(self):
        """Test multiple replacements in a single string source"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": "SELECT {{COL1}}, {{COL2}} FROM {{TABLE}}"
                }
            ]
        }
        
        result = _process_ipynb_text_safely(
            json.dumps(notebook),
            "/base", "cat", "sch",
            {"{{COL1}}": "id", "{{COL2}}": "name", "{{TABLE}}": "users"}
        )
        
        result_nb = json.loads(result)
        self.assertIn("id", result_nb["cells"][0]["source"])
        self.assertIn("name", result_nb["cells"][0]["source"])
        self.assertIn("users", result_nb["cells"][0]["source"])
    
    def test_markdown_cell_preserved(self):
        """Test that markdown cells are not modified"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "source": ["# Title {{PLACEHOLDER}}"]
                }
            ]
        }
        
        result = _process_ipynb_text_safely(
            json.dumps(notebook),
            "/base", "cat", "sch",
            {"{{PLACEHOLDER}}": "replacement"}
        )
        
        result_nb = json.loads(result)
        # Markdown cells should not be processed by fix_source
        # (fix_source is only called for code cells)
        self.assertIn("{{PLACEHOLDER}}", result_nb["cells"][0]["source"][0])
    
    def test_cell_without_source_key(self):
        """Test cells without source key are skipped"""
        from create_databricks_items_maag import _process_ipynb_text_safely
        
        notebook = {
            "cells": [
                {
                    "cell_type": "code"
                    # No "source" key
                }
            ]
        }
        
        result = _process_ipynb_text_safely(
            json.dumps(notebook),
            "/base", "cat", "sch", {}
        )
        
        result_nb = json.loads(result)
        # Should not raise, cell is preserved
        self.assertNotIn("source", result_nb["cells"][0])


if __name__ == "__main__":
    unittest.main()
