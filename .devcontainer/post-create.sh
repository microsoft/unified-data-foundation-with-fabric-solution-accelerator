#!/bin/bash

# Post-create script for dev container setup
# This script runs after the dev container is created to install additional dependencies

set -e

echo "🚀 Setting up Unified Data Foundation with Fabric development environment..."

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Install additional system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    jq \
    tree \
    vim

# Upgrade pip
echo "🐍 Upgrading pip..."
python -m pip install --upgrade pip

# Install Python requirements for the project
echo "📋 Installing Python requirements..."

# Install fabric script requirements
if [ -f "./infra/scripts/fabric/requirements.txt" ]; then
    echo "Installing Fabric script requirements..."
    pip install -r ./infra/scripts/fabric/requirements.txt
fi

# Install source requirements (for notebooks)
if [ -f "./src/requirements.txt" ]; then
    echo "Installing source requirements..."
    pip install -r ./src/requirements.txt
fi

# Install databricks script requirements if they exist
if [ -f "./infra/scripts/databricks/requirements.txt" ]; then
    echo "Installing Databricks script requirements..."
    pip install -r ./infra/scripts/databricks/requirements.txt
fi

# Install additional development tools
echo "🛠️ Installing development tools..."
pip install \
    black \
    flake8 \
    pytest \
    mypy \
    bandit \
    jupyter \
    jupyterlab

# Verify Azure CLI and azd installation
echo "✅ Verifying tool installations..."
echo "Azure CLI version: $(az --version | head -n 1)"
echo "Azure Developer CLI version: $(azd version)"
echo "Python version: $(python --version)"
echo "Git version: $(git --version)"

# Set up git configuration template (user can override)
echo "📝 Setting up git configuration template..."
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

# Make scripts executable
echo "🔐 Making scripts executable..."
find ./infra/scripts -name "*.sh" -type f -exec chmod +x {} \;

# Create workspace info
echo "📄 Creating workspace information..."
cat > ~/WORKSPACE_INFO.md << 'EOF'
# Unified Data Foundation with Fabric - Dev Container

## Quick Start
1. Authenticate with Azure: `az login`
2. Login to azd: `azd auth login`
3. Set your admin email: `azd env set AZURE_FABRIC_ADMIN_USER_EMAIL "your-email@domain.com"`
4. Deploy: `azd up`

## Available Tools
- Azure CLI (`az`)
- Azure Developer CLI (`azd`)
- Python 3.11 with pip
- PowerShell
- Git & GitHub CLI
- Jupyter Lab
- Development tools (black, flake8, pytest, mypy)

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