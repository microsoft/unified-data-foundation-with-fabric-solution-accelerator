"""
This script replaces the value of SOURCE_LAKEHOUSE_NAME in all .ipynb notebooks under the 'notebooks' folder.

Usage:
1. Place this script in the 'src/fabric' folder of your repo.
2. Run the script: python replace_lakhouse_name.py
3. When prompted, enter the old Lakehouse name (e.g., MAAG_LH_Bronze).
4. When prompted, enter the new Lakehouse name (e.g., maag_bronze).
5. The script will recursively update all matching notebook files under 'notebooks' and print the updated file paths.

Details:
- Handles all variations in whitespace and quotes, e.g.:
    SOURCE_LAKEHOUSE_NAME = "old_name"
    SOURCE_LAKEHOUSE_NAME= "old_name"
    SOURCE_LAKEHOUSE_NAME="old_name"
    SOURCE_LAKEHOUSE_NAME ='old_name'
    SOURCE_LAKEHOUSE_NAME= 'old_name'
    SOURCE_LAKEHOUSE_NAME ="old_name"
- Only code cells containing lines with SOURCE_LAKEHOUSE_NAME will be updated.
- The script uses relative paths, so it works in any cloned repo location.
- No changes are made if the old name is not found.

"""

import os
import json
import re

def replace_lakehouse_name_in_notebook(notebook_path, old_name, new_name):
    # Regex matches any line assigning SOURCE_LAKEHOUSE_NAME to old_name,
    # allowing any whitespace around '=', and both single or double quotes.
    pattern = re.compile(r'(SOURCE_LAKEHOUSE_NAME\s*=\s*["\'])' + re.escape(old_name) + r'(["\'])')
    changed = False
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'code':
            new_source = []
            for line in cell.get('source', []):
                # Replace all matches in the line
                new_line, count = pattern.subn(r'\1' + new_name + r'\2', line)
                if count > 0:
                    changed = True
                new_source.append(new_line)
            cell['source'] = new_source
    if changed:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        print(f"Updated: {notebook_path}")

def main():
    # Use relative path from the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    notebooks_dir = os.path.join(script_dir, "notebooks")
    old_name = input("Enter the old Lakehouse name (e.g., MAAG_LH_Bronze): ").strip()
    new_name = input("Enter the new Lakehouse name (e.g., maag_bronze): ").strip()
    for root, _, files in os.walk(notebooks_dir):
        for file in files:
            if file.endswith('.ipynb'):
                notebook_path = os.path.join(root, file)
                replace_lakehouse_name_in_notebook(notebook_path, old_name, new_name)

if __name__ == "__main__":
    main()
