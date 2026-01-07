# Microsoft Fabric Data Agent

## Overview

An intelligent AI assistant for analyzing and exploring data in Microsoft Fabric Gold tier data lakes. Built on medallion architecture (Bronze → Silver → Gold), this agent provides natural language querying across sales, customer, and financial data domains. Can be deployed as an MCP server for VS Code integration.

## Core Capabilities

**Data Analysis**
- Natural language to SQL/PySpark code generation
- Cross-domain analysis (customer, sales, product, financial data)
- Automatic schema detection and intelligent column mapping
- Support for T-SQL endpoints and PySpark notebooks

**Business Intelligence**
- Customer segmentation and lifetime value analysis
- Sales performance tracking and trend identification
- Product profitability and cross-selling analysis
- Financial health monitoring and receivables management
- Statistical insights and optimization recommendations

## Data Sources

**Primary Tables**
- `shared.customer` - Demographics, relationship types, contact info
- `salesfabric.[order]` - Transaction records and order details  
- `salesfabric.orderline` - Line item details and quantities
- `shared.product` - Product catalog, categories, pricing
- `salesfabric.orderpayment` - Payment methods and amounts

**Architecture**: Bronze (raw) → Silver (cleaned) → Gold (business-ready)

## Example Use Cases

- "Show me top customers by lifetime value"
- "What are our best-performing products this quarter?"
- "Which customers have overdue payments and total amounts?"
- "Analyze purchase patterns by customer relationship type"
- "Identify cross-selling opportunities in product categories"

## Technical Details

**Platform**: Microsoft Fabric Gold tier lakehouse
**Languages**: T-SQL, PySpark (Python)
**Formats**: Parquet, Delta Lake, CSV
**Integration**: Power BI, MCP server for VS Code, Azure services
**Scale**: Optimized for millions of records with intelligent caching

## MCP Server Deployment

This agent can function as a Model Context Protocol server in VS Code:
1. Publish the agent in Microsoft Fabric
2. Configure MCP server URL in VS Code (.vscode/mcp.json)
3. Enable Agent Mode and select orchestrator (GPT-4, Claude, etc.)
4. Query organizational data directly from VS Code

## Documentation

Complete documentation suite includes:
- `agent_instructions.md` - Master prompt and capabilities
- `data_source_descriptions.md` - Detailed schema specifications
- Example PySpark and SQL code implementations
- 50+ validated test questions for quality assurance
- Setup and optimization guides

Transform your data analysis with conversational AI powered by Microsoft Fabric.