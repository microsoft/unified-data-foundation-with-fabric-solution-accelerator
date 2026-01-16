# Data Source Instructions

## Overview

This Fabric Data Agent has access to manufacturing operations data in an EventHouse database.

## Business Context

**Note:** Replace this content with your organization's actual business performance measurements. 

This sample dataset represents common manufacturing scenarios:

- Equipment monitoring and maintenance
- Product quality control
- Operational efficiency analysis
- Real-time alerting and diagnostics

### Database Tables and Relationships 

**Note:** Replace this content with your organization's actual data and update table schemas accordingly.

#### Core Tables

- **`events`** - Manufacturing telemetry and sensor data (real-time + historical)
- **`assets`** - Equipment and machinery information  
- **`products`** - Product catalog and specifications
- **`sites`** - Manufacturing facility locations
- **`locations`** - Geographic information

#### Data Relationships

```
events → assets → sites → locations
events → products
```

#### Real-Time Data

- **`events` table** receives continuous real-time data via EventStream
- Contains sensor readings: temperature, vibration, humidity, speed
- Includes quality metrics: defect probability
- Links to specific assets and products

#### Reference Data  

- **Static tables** (assets, products, sites, locations) contain stable reference information
- Used for context and enrichment of event data
- Updated infrequently

### Query Patterns

When analyzing manufacturing data, typically join events with reference tables:

```kql
// Asset performance analysis
events
| join assets on $left.AssetId == $right.Id
| summarize avg(Temperature), avg(Speed) by AssetId, assets.Name

// Product quality tracking  
events
| join products on $left.ProductId == $right.Id
| summarize avg(DefectProbability) by ProductId, products.Name
```