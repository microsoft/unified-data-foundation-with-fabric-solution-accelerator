#!/bin/bash

# Post-create script for dev container setup
# This script runs after the dev container is created to install additional dependencies

set -e

echo "🚀 Setting up Unified Data Foundation with Fabric development environment..."

# Note: Core tools already provided by devcontainer.json:
# - Python 3.11 (base image)
# - Azure CLI + Bicep (azure-cli feature)
# - Git (git feature)  
# - GitHub CLI (github-cli feature)
# - PowerShell (powershell feature)
# - Azure Developer CLI (azd feature)
# - Common system tools: curl, wget, unzip, jq, tree, vim (base image)

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Upgrade pip
echo "🐍 Upgrading pip..."
python -m pip install --upgrade pip

# Verify Python version meets requirements (3.9+)
echo "🔍 Verifying Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
python_major=$(echo $python_version | cut -d'.' -f1)
python_minor=$(echo $python_version | cut -d'.' -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 9 ]); then
    echo "❌ Error: Python 3.9+ is required. Found Python $python_version"
    exit 1
fi
echo "✅ Python $python_version meets requirements (3.9+)"

# Verify venv module is available (should be included with Python 3.11)
echo "🔍 Verifying Python venv module..."
if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "❌ Error: Python venv module is not available"
    exit 1
fi
echo "✅ Python venv module is available"

# Install Python requirements for the project
echo "📋 Preparing Python environment..."

# Note: Project-specific requirements are installed by deployment scripts in isolated virtual environments
# This ensures consistency between development and deployment, avoiding version conflicts

# Verify that requirements files exist (deployment scripts will install them in venvs)
if [ -f "./infra/scripts/fabric/requirements.txt" ]; then
    echo "✅ Fabric script requirements.txt found"
else
    echo "⚠️ Warning: ./infra/scripts/fabric/requirements.txt not found"
fi

if [ -f "./src/requirements.txt" ]; then
    echo "✅ Source requirements.txt found"
else
    echo "⚠️ Warning: ./src/requirements.txt not found"
fi

if [ -f "./infra/scripts/databricks/requirements.txt" ]; then
    echo "✅ Databricks script requirements.txt found"
else
    echo "ℹ️ Info: ./infra/scripts/databricks/requirements.txt not found (optional)"
fi

# Install additional development tools
echo "🛠️ Installing development tools..."
if ! pip install \
    black \
    flake8 \
    pytest \
    mypy \
    bandit \
    jupyter \
    jupyterlab; then
    echo "❌ Failed to install development tools"
    exit 1
fi
echo "✅ Development tools installed successfully"

# Verify Azure CLI and azd installation (installed via devcontainer features)
echo "✅ Verifying tool installations..."
echo "Azure CLI version: $(az --version | head -n 1)"
echo "Azure Developer CLI version: $(azd version)"
echo "Python version: $(python --version)"
echo "Git version: $(git --version)"

# Verify that critical Python packages can be installed (but don't install globally)
echo "🔍 Verifying Python package availability..."
python3 -c "import importlib.util; print('✅ azure-identity importable' if importlib.util.find_spec('azure.identity') else 'ℹ️ azure-identity will be installed by deployment scripts')"
python3 -c "import importlib.util; print('✅ azure-storage-file-datalake importable' if importlib.util.find_spec('azure.storage.filedatalake') else 'ℹ️ azure-storage-file-datalake will be installed by deployment scripts')"
python3 -c "import importlib.util; print('✅ requests importable' if importlib.util.find_spec('requests') else 'ℹ️ requests will be installed by deployment scripts')"

# Test fabric script modules if they exist (won't have dependencies until deployment scripts run)
if [ -f "./infra/scripts/fabric/fabric_api.py" ]; then
    echo "🔍 Fabric API modules found (dependencies installed by deployment scripts)"
else
    echo "ℹ️ Info: Fabric API modules not found (will be available after checkout)"
fi

# Set up additional git configuration (base git config handled by devcontainer feature)
echo "📝 Setting up additional git configuration..."
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global core.autocrlf input

# Create helpful aliases
echo "🔗 Setting up helpful aliases..."
echo 'alias ll="ls -la"' >> ~/.bashrc
echo 'alias tree="tree -I __pycache__"' >> ~/.bashrc
echo 'alias azd-env="azd env get-values"' >> ~/.bashrc
echo 'alias azd-up="azd up"' >> ~/.bashrc
echo 'alias azd-down="azd down"' >> ~/.bashrc

# Make scripts executable and fix line endings
echo "🔐 Making scripts executable and fixing line endings..."
find ./infra/scripts -name "*.sh" -type f -exec chmod +x {} \;
find ./infra/scripts -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;

# Add virtual environment directories to .gitignore if not already present
echo "📝 Updating .gitignore for virtual environments..."
if ! grep -q "\.venv/" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Python virtual environments" >> .gitignore
    echo ".venv/" >> .gitignore
    echo "*/.venv/" >> .gitignore
fi

# Create workspace info
echo "📄 Creating workspace information..."
cat > ~/WORKSPACE_INFO.md << 'EOF'
# Unified Data Foundation with Fabric - Dev Container

## Quick Start
1. Authenticate with Azure: `az login`
2. Login to azd: `azd auth login`
3. Set your admin email: `azd env set AZURE_FABRIC_ADMIN_USER_EMAIL "your-email@domain.com"`
4. Deploy: `azd up`

## Fabric Provisioning
You can also deploy Microsoft Fabric items directly:
1. Navigate to fabric scripts: `cd infra/scripts/fabric`
2. Run: `./provision_fabric_items.sh -c "YourCapacityName" -w "YourWorkspaceName"`
3. Or set environment variables and run without parameters:
   ```bash
   export AZURE_FABRIC_CAPACITY_NAME="YourCapacityName"
   export AZURE_FABRIC_WORKSPACE_NAME="YourWorkspaceName"
   ./provision_fabric_items.sh
   ```

## Databricks Provisioning
You can also deploy Databricks items directly:
1. Navigate to databricks scripts: `cd infra/scripts/databricks`
2. Run: `./provision_databricks_items.sh --workspaceUrl "https://adb-xxxx.azuredatabricks.net" --token "your-token"`

Note: Deployment scripts create isolated virtual environments and install their own dependencies automatically.

## Available Tools
- Azure CLI (`az`) + Bicep
- Azure Developer CLI (`azd`)
- Python 3.11 with pip and venv
- PowerShell
- Git & GitHub CLI
- Jupyter Lab
- Development tools (black, flake8, pytest, mypy)
- System utilities (curl, wget, jq, tree, vim)

## Project Structure
- `/infra` - Infrastructure as Code (Bicep templates)
- `/src` - Source code and notebooks
- `/docs` - Documentation
- `/reports` - Power BI reports

## Helpful Commands
- `azd-env` - Show current azd environment variables
- `azd-up` - Deploy the solution
- `azd-down` - Clean up resources
- `tree` - Show directory structure
- `jupyter lab` - Start Jupyter Lab server

## Port Forwarding
- 8000, 8080, 8888 are forwarded for web applications

Enjoy coding! 🎉
EOF

echo "✨ Dev container setup complete!"
echo "📖 Check ~/WORKSPACE_INFO.md for quick start instructions"
echo ""
echo "🎯 Next steps:"
echo "   1. Run 'az login' to authenticate with Azure"
echo "   2. Configure your Git user name and email using 'git config --global user.name \"Your Name\"' and 'git config --global user.email \"your-email@domain.com\"'"
echo "   3. Run 'azd auth login' to authenticate with Azure Developer CLI"
echo "   4. Deploy the solution: azd up"
echo ""
echo "🏗️ For direct Fabric deployment:"
echo "   1. cd infra/scripts/fabric"
echo "   2. ./provision_fabric_items.sh -c \"YourCapacityName\" -w \"YourWorkspaceName\""
echo ""
echo "🏗️ For direct Databricks deployment:"
echo "   1. cd infra/scripts/databricks"
echo "   2. ./provision_databricks_items.sh --workspaceUrl \"https://adb-xxxx.azuredatabricks.net\" --token \"your-token\""