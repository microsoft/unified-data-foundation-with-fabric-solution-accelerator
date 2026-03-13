"""
Unit tests for util_replace_lakhouse_name.py and util_replace_workspace_name.py
"""

import os
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_replace_lakhouse_name import replace_lakehouse_name_in_notebook, main as lakehouse_main
from util_replace_workspace_name import replace_workspace_name_in_notebook, main as workspace_main


class TestReplaceLakehouseNameInNotebook(unittest.TestCase):
    """Test cases for replace_lakehouse_name_in_notebook function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebook_path = os.path.join(self.test_dir, "test_notebook.ipynb")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, cells):
        """Helper to create a notebook file with given cells"""
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return self.notebook_path
    
    def read_notebook(self):
        """Helper to read notebook content"""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test_replace_double_quotes_no_spaces(self):
        """Test replacement with double quotes and no spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME="MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME="maag_bronze"')
    
    def test_replace_double_quotes_with_spaces(self):
        """Test replacement with double quotes and spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "maag_bronze"')
    
    def test_replace_single_quotes_no_spaces(self):
        """Test replacement with single quotes and no spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ["SOURCE_LAKEHOUSE_NAME='MAAG_LH_Bronze'"]
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], "SOURCE_LAKEHOUSE_NAME='maag_bronze'")
    
    def test_replace_single_quotes_with_spaces(self):
        """Test replacement with single quotes and spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ["SOURCE_LAKEHOUSE_NAME = 'MAAG_LH_Bronze'"]
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], "SOURCE_LAKEHOUSE_NAME = 'maag_bronze'")
    
    def test_replace_space_before_equals(self):
        """Test replacement with space only before ="""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME ="MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME ="maag_bronze"')
    
    def test_replace_space_after_equals(self):
        """Test replacement with space only after ="""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME= "MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME= "maag_bronze"')
    
    def test_no_change_when_name_not_found(self):
        """Test that no change is made when old name is not found"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME="other_name"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME="other_name"')
    
    def test_markdown_cells_not_modified(self):
        """Test that markdown cells are not modified"""
        cells = [{
            "cell_type": "markdown",
            "source": ['SOURCE_LAKEHOUSE_NAME="MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME="MAAG_LH_Bronze"')
    
    def test_multiple_lines_in_cell(self):
        """Test replacement in a cell with multiple lines"""
        cells = [{
            "cell_type": "code",
            "source": [
                '# Configuration\n',
                'SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"\n',
                'OTHER_VAR = "value"\n'
            ]
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][1], 'SOURCE_LAKEHOUSE_NAME = "maag_bronze"\n')
        self.assertEqual(notebook["cells"][0]["source"][0], '# Configuration\n')
        self.assertEqual(notebook["cells"][0]["source"][2], 'OTHER_VAR = "value"\n')
    
    def test_multiple_cells(self):
        """Test replacement across multiple cells"""
        cells = [
            {
                "cell_type": "code",
                "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
            },
            {
                "cell_type": "code",
                "source": ['OTHER_CODE = "test"']
            },
            {
                "cell_type": "code",
                "source": ['SOURCE_LAKEHOUSE_NAME="MAAG_LH_Bronze"']
            }
        ]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "maag_bronze"')
        self.assertEqual(notebook["cells"][1]["source"][0], 'OTHER_CODE = "test"')
        self.assertEqual(notebook["cells"][2]["source"][0], 'SOURCE_LAKEHOUSE_NAME="maag_bronze"')
    
    def test_empty_notebook(self):
        """Test handling of empty notebook"""
        cells = []
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"], [])
    
    def test_cell_without_source(self):
        """Test handling of cell without source key"""
        cells = [{
            "cell_type": "code"
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(len(notebook["cells"]), 1)
    
    def test_special_characters_in_name(self):
        """Test replacement with special regex characters in name"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME="name.with.dots"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "name.with.dots", "new_name")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME="new_name"')
    
    def test_multiple_tabs_as_whitespace(self):
        """Test replacement with tabs as whitespace"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME\t=\t"MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME\t=\t"maag_bronze"')


class TestReplaceWorkspaceNameInNotebook(unittest.TestCase):
    """Test cases for replace_workspace_name_in_notebook function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebook_path = os.path.join(self.test_dir, "test_notebook.ipynb")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, cells):
        """Helper to create a notebook file with given cells"""
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return self.notebook_path
    
    def read_notebook(self):
        """Helper to read notebook content"""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test_replace_double_quotes_no_spaces(self):
        """Test replacement with double quotes and no spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME="Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME="MAAG_Solution"')
    
    def test_replace_double_quotes_with_spaces(self):
        """Test replacement with double quotes and spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = "MAAG_Solution"')
    
    def test_replace_single_quotes_no_spaces(self):
        """Test replacement with single quotes and no spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ["WORKSPACE_NAME='Fabric_MAAG'"]
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], "WORKSPACE_NAME='MAAG_Solution'")
    
    def test_replace_single_quotes_with_spaces(self):
        """Test replacement with single quotes and spaces around ="""
        cells = [{
            "cell_type": "code",
            "source": ["WORKSPACE_NAME = 'Fabric_MAAG'"]
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], "WORKSPACE_NAME = 'MAAG_Solution'")
    
    def test_replace_space_before_equals(self):
        """Test replacement with space only before ="""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME ="Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME ="MAAG_Solution"')
    
    def test_replace_space_after_equals(self):
        """Test replacement with space only after ="""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME= "Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME= "MAAG_Solution"')
    
    def test_no_change_when_name_not_found(self):
        """Test that no change is made when old name is not found"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME="other_name"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME="other_name"')
    
    def test_markdown_cells_not_modified(self):
        """Test that markdown cells are not modified"""
        cells = [{
            "cell_type": "markdown",
            "source": ['WORKSPACE_NAME="Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME="Fabric_MAAG"')
    
    def test_multiple_lines_in_cell(self):
        """Test replacement in a cell with multiple lines"""
        cells = [{
            "cell_type": "code",
            "source": [
                '# Configuration\n',
                'WORKSPACE_NAME = "Fabric_MAAG"\n',
                'OTHER_VAR = "value"\n'
            ]
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][1], 'WORKSPACE_NAME = "MAAG_Solution"\n')
        self.assertEqual(notebook["cells"][0]["source"][0], '# Configuration\n')
        self.assertEqual(notebook["cells"][0]["source"][2], 'OTHER_VAR = "value"\n')
    
    def test_multiple_cells(self):
        """Test replacement across multiple cells"""
        cells = [
            {
                "cell_type": "code",
                "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
            },
            {
                "cell_type": "code",
                "source": ['OTHER_CODE = "test"']
            },
            {
                "cell_type": "code",
                "source": ['WORKSPACE_NAME="Fabric_MAAG"']
            }
        ]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = "MAAG_Solution"')
        self.assertEqual(notebook["cells"][1]["source"][0], 'OTHER_CODE = "test"')
        self.assertEqual(notebook["cells"][2]["source"][0], 'WORKSPACE_NAME="MAAG_Solution"')
    
    def test_empty_notebook(self):
        """Test handling of empty notebook"""
        cells = []
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"], [])
    
    def test_cell_without_source(self):
        """Test handling of cell without source key"""
        cells = [{
            "cell_type": "code"
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(len(notebook["cells"]), 1)
    
    def test_special_characters_in_name(self):
        """Test replacement with special regex characters in name"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME="name.with.dots"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "name.with.dots", "new_name")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME="new_name"')
    
    def test_workspace_name_with_spaces(self):
        """Test replacement with workspace name containing spaces"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME="My Workspace Name"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "My Workspace Name", "New Workspace")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME="New Workspace"')
    
    def test_multiple_tabs_as_whitespace(self):
        """Test replacement with tabs as whitespace"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME\t=\t"Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME\t=\t"MAAG_Solution"')


class TestLakehouseMain(unittest.TestCase):
    """Test cases for the lakehouse main function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebooks_dir = os.path.join(self.test_dir, "notebooks")
        os.makedirs(self.notebooks_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, filename, cells):
        """Helper to create a notebook file with given cells"""
        notebook_path = os.path.join(self.notebooks_dir, filename)
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return notebook_path
    
    @patch('util_replace_lakhouse_name.input')
    @patch('util_replace_lakhouse_name.os.path.dirname')
    def test_main_processes_all_notebooks(self, mock_dirname, mock_input):
        """Test that main processes all notebooks in the directory"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["MAAG_LH_Bronze", "maag_bronze"]
        
        # Create test notebooks
        self.create_notebook("test1.ipynb", [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
        }])
        self.create_notebook("test2.ipynb", [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME="MAAG_LH_Bronze"']
        }])
        
        lakehouse_main()
        
        # Verify notebooks were updated
        with open(os.path.join(self.notebooks_dir, "test1.ipynb"), 'r') as f:
            nb1 = json.load(f)
        with open(os.path.join(self.notebooks_dir, "test2.ipynb"), 'r') as f:
            nb2 = json.load(f)
        
        self.assertEqual(nb1["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "maag_bronze"')
        self.assertEqual(nb2["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME="maag_bronze"')
    
    @patch('util_replace_lakhouse_name.input')
    @patch('util_replace_lakhouse_name.os.path.dirname')
    def test_main_handles_nested_directories(self, mock_dirname, mock_input):
        """Test that main processes notebooks in nested directories"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["MAAG_LH_Bronze", "maag_bronze"]
        
        # Create nested directory
        nested_dir = os.path.join(self.notebooks_dir, "subfolder")
        os.makedirs(nested_dir)
        
        # Create notebook in nested directory
        notebook_path = os.path.join(nested_dir, "nested.ipynb")
        notebook = {
            "cells": [{
                "cell_type": "code",
                "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
            }],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        
        lakehouse_main()
        
        # Verify notebook was updated
        with open(notebook_path, 'r') as f:
            nb = json.load(f)
        
        self.assertEqual(nb["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "maag_bronze"')
    
    @patch('util_replace_lakhouse_name.input')
    @patch('util_replace_lakhouse_name.os.path.dirname')
    def test_main_ignores_non_ipynb_files(self, mock_dirname, mock_input):
        """Test that main ignores non-.ipynb files"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["MAAG_LH_Bronze", "maag_bronze"]
        
        # Create a non-notebook file
        other_file = os.path.join(self.notebooks_dir, "test.py")
        with open(other_file, 'w') as f:
            f.write('SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"')
        
        # Should not raise any errors
        lakehouse_main()
        
        # Verify file was not modified
        with open(other_file, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, 'SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"')


class TestWorkspaceMain(unittest.TestCase):
    """Test cases for the workspace main function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebooks_dir = os.path.join(self.test_dir, "notebooks")
        os.makedirs(self.notebooks_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, filename, cells):
        """Helper to create a notebook file with given cells"""
        notebook_path = os.path.join(self.notebooks_dir, filename)
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return notebook_path
    
    @patch('util_replace_workspace_name.input')
    @patch('util_replace_workspace_name.os.path.dirname')
    def test_main_processes_all_notebooks(self, mock_dirname, mock_input):
        """Test that main processes all notebooks in the directory"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["Fabric_MAAG", "MAAG_Solution"]
        
        # Create test notebooks
        self.create_notebook("test1.ipynb", [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
        }])
        self.create_notebook("test2.ipynb", [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME="Fabric_MAAG"']
        }])
        
        workspace_main()
        
        # Verify notebooks were updated
        with open(os.path.join(self.notebooks_dir, "test1.ipynb"), 'r') as f:
            nb1 = json.load(f)
        with open(os.path.join(self.notebooks_dir, "test2.ipynb"), 'r') as f:
            nb2 = json.load(f)
        
        self.assertEqual(nb1["cells"][0]["source"][0], 'WORKSPACE_NAME = "MAAG_Solution"')
        self.assertEqual(nb2["cells"][0]["source"][0], 'WORKSPACE_NAME="MAAG_Solution"')
    
    @patch('util_replace_workspace_name.input')
    @patch('util_replace_workspace_name.os.path.dirname')
    def test_main_handles_nested_directories(self, mock_dirname, mock_input):
        """Test that main processes notebooks in nested directories"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["Fabric_MAAG", "MAAG_Solution"]
        
        # Create nested directory
        nested_dir = os.path.join(self.notebooks_dir, "subfolder")
        os.makedirs(nested_dir)
        
        # Create notebook in nested directory
        notebook_path = os.path.join(nested_dir, "nested.ipynb")
        notebook = {
            "cells": [{
                "cell_type": "code",
                "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
            }],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        
        workspace_main()
        
        # Verify notebook was updated
        with open(notebook_path, 'r') as f:
            nb = json.load(f)
        
        self.assertEqual(nb["cells"][0]["source"][0], 'WORKSPACE_NAME = "MAAG_Solution"')
    
    @patch('util_replace_workspace_name.input')
    @patch('util_replace_workspace_name.os.path.dirname')
    def test_main_ignores_non_ipynb_files(self, mock_dirname, mock_input):
        """Test that main ignores non-.ipynb files"""
        mock_dirname.return_value = self.test_dir
        mock_input.side_effect = ["Fabric_MAAG", "MAAG_Solution"]
        
        # Create a non-notebook file
        other_file = os.path.join(self.notebooks_dir, "test.py")
        with open(other_file, 'w') as f:
            f.write('WORKSPACE_NAME = "Fabric_MAAG"')
        
        # Should not raise any errors
        workspace_main()
        
        # Verify file was not modified
        with open(other_file, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, 'WORKSPACE_NAME = "Fabric_MAAG"')


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for both utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebook_path = os.path.join(self.test_dir, "test_notebook.ipynb")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, cells):
        """Helper to create a notebook file with given cells"""
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return self.notebook_path
    
    def read_notebook(self):
        """Helper to read notebook content"""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test_lakehouse_unicode_characters(self):
        """Test lakehouse replacement with unicode characters"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "测试"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "测试", "新名称")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "新名称"')
    
    def test_workspace_unicode_characters(self):
        """Test workspace replacement with unicode characters"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "测试"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "测试", "新名称")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = "新名称"')
    
    def test_lakehouse_empty_string_replacement(self):
        """Test lakehouse replacement with empty string"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = ""')
    
    def test_workspace_empty_string_replacement(self):
        """Test workspace replacement with empty string"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = ""')
    
    def test_lakehouse_parentheses_in_name(self):
        """Test lakehouse replacement with parentheses in name"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "name(1)"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "name(1)", "new_name")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "new_name"')
    
    def test_workspace_brackets_in_name(self):
        """Test workspace replacement with brackets in name"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "name[1]"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "name[1]", "new_name")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = "new_name"')
    
    def test_lakehouse_multiple_occurrences_same_line(self):
        """Test lakehouse replacement with multiple occurrences on same line (edge case)"""
        cells = [{
            "cell_type": "code",
            "source": ['x = "old"; SOURCE_LAKEHOUSE_NAME = "old"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "old", "new")
        
        notebook = self.read_notebook()
        # Only SOURCE_LAKEHOUSE_NAME should be replaced
        self.assertEqual(notebook["cells"][0]["source"][0], 'x = "old"; SOURCE_LAKEHOUSE_NAME = "new"')
    
    def test_lakehouse_raw_cell_not_modified(self):
        """Test that raw cells are not modified"""
        cells = [{
            "cell_type": "raw",
            "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"')
    
    def test_workspace_raw_cell_not_modified(self):
        """Test that raw cells are not modified for workspace"""
        cells = [{
            "cell_type": "raw",
            "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        notebook = self.read_notebook()
        self.assertEqual(notebook["cells"][0]["source"][0], 'WORKSPACE_NAME = "Fabric_MAAG"')


class TestPrintOutput(unittest.TestCase):
    """Test print output for both utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.notebook_path = os.path.join(self.test_dir, "test_notebook.ipynb")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def create_notebook(self, cells):
        """Helper to create a notebook file with given cells"""
        notebook = {
            "cells": cells,
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        return self.notebook_path
    
    @patch('builtins.print')
    def test_lakehouse_prints_updated_message(self, mock_print):
        """Test that lakehouse prints updated message when changes made"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "MAAG_LH_Bronze"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("Updated:", call_args)
        self.assertIn(self.notebook_path, call_args)
    
    @patch('builtins.print')
    def test_lakehouse_no_print_when_no_changes(self, mock_print):
        """Test that lakehouse does not print when no changes made"""
        cells = [{
            "cell_type": "code",
            "source": ['SOURCE_LAKEHOUSE_NAME = "other"']
        }]
        self.create_notebook(cells)
        replace_lakehouse_name_in_notebook(self.notebook_path, "MAAG_LH_Bronze", "maag_bronze")
        
        mock_print.assert_not_called()
    
    @patch('builtins.print')
    def test_workspace_prints_updated_message(self, mock_print):
        """Test that workspace prints updated message when changes made"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "Fabric_MAAG"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("Updated:", call_args)
        self.assertIn(self.notebook_path, call_args)
    
    @patch('builtins.print')
    def test_workspace_no_print_when_no_changes(self, mock_print):
        """Test that workspace does not print when no changes made"""
        cells = [{
            "cell_type": "code",
            "source": ['WORKSPACE_NAME = "other"']
        }]
        self.create_notebook(cells)
        replace_workspace_name_in_notebook(self.notebook_path, "Fabric_MAAG", "MAAG_Solution")
        
        mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main()
