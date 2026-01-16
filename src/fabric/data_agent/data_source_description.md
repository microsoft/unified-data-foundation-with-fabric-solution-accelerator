# Data Source Descriptions for Fabric Data Agent 

## Overview
The KQL database contains manufacturing operations data from Contoso Outdoors' Ho Chi Minh facility, which produces outdoor camping equipment. The data includes real-time telemetry, asset information, and product details.

## Data Tables

### Table `events`
Large telemetry dataset with 259,000+ sensor readings from manufacturing equipment. Contains timestamps, asset IDs, product IDs, sensor measurements (vibration, temperature, humidity, speed), and defect probability calculations.

### Table `assets`  
Equipment information for 2 manufacturing assets:
- A_1000: Robotic Arm 1 (Assembly line)
- A_1001: Packaging Line 1 (Packaging operations)

Includes asset names, types, serial numbers, and maintenance status.

### Table `products`
Product catalog with 21 outdoor camping products including camping stoves and tables. Contains product details, pricing (list price and unit cost), categories, colors, and brand information (Contoso Outdoors).

### Table `locations`
Geographic data showing the facility location in Ho Chi Minh City, Vietnam.