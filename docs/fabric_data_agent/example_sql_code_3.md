```sql
-- Product Performance Analysis

-- Top 15 Products by Revenue
WITH product_sales AS (
    SELECT 
        p.ProductID,
        p.ProductName,
        p.CategoryName,
        p.StandardCost,
        p.ListPrice,
        ol.Quantity,
        ol.UnitPrice,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit,
        o.CustomerId
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    WHERE o.OrderStatus = 'Completed'
)

SELECT TOP 15
    ProductID,
    ProductName,
    CategoryName,
    ROUND(SUM(LineRevenue), 2) AS TotalRevenue,
    SUM(Quantity) AS TotalUnitsSold,
    COUNT(DISTINCT CustomerId) AS UniqueCustomers,
    COUNT(*) AS OrderLines,
    ROUND(SUM(LineRevenue) / COUNT(DISTINCT CustomerId), 2) AS AvgRevenuePerCustomer
FROM product_sales
GROUP BY ProductID, ProductName, CategoryName
ORDER BY TotalRevenue DESC;

-- Product Category Performance
WITH product_sales AS (
    SELECT 
        p.ProductID,
        p.CategoryName,
        ol.Quantity,
        ol.UnitPrice,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit,
        o.CustomerId
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    WHERE o.OrderStatus = 'Completed'
)

SELECT 
    CategoryName,
    COUNT(DISTINCT ProductID) AS ProductsInCategory,
    ROUND(SUM(LineRevenue), 2) AS CategoryRevenue,
    SUM(Quantity) AS CategoryUnitsSold,
    COUNT(DISTINCT CustomerId) AS CategoryCustomers,
    ROUND(AVG((LineProfit * 100.0) / LineRevenue), 2) AS AvgProfitMargin,
    ROUND(SUM(LineRevenue) / COUNT(DISTINCT ProductID), 2) AS RevenuePerProduct
FROM product_sales
GROUP BY CategoryName
ORDER BY CategoryRevenue DESC;

-- Top 12 Most Profitable Products (Revenue > $1,000)
WITH product_sales AS (
    SELECT 
        p.ProductID,
        p.ProductName,
        p.CategoryName,
        p.StandardCost,
        p.ListPrice,
        ol.Quantity,
        ol.UnitPrice,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        ((ol.Quantity * ol.UnitPrice) - (ol.Quantity * p.StandardCost)) AS LineProfit
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    WHERE o.OrderStatus = 'Completed'
),

product_profitability AS (
    SELECT 
        ProductID,
        ProductName,
        CategoryName,
        StandardCost,
        ListPrice,
        SUM(LineProfit) AS TotalProfit,
        SUM(LineRevenue) AS TotalRevenue,
        SUM(Quantity) AS TotalQuantity,
        AVG((LineProfit * 100.0) / LineRevenue) AS AvgMargin
    FROM product_sales
    GROUP BY ProductID, ProductName, CategoryName, StandardCost, ListPrice
    HAVING SUM(LineRevenue) > 1000
)

SELECT TOP 12
    ProductID,
    ProductName,
    CategoryName,
    ROUND(TotalProfit, 2) AS TotalProfit,
    ROUND(TotalRevenue, 2) AS TotalRevenue,
    TotalQuantity,
    ROUND(AvgMargin, 2) AS AvgMargin,
    ROUND(TotalProfit / TotalQuantity, 2) AS ProfitPerUnit
FROM product_profitability
ORDER BY TotalProfit DESC;

-- Product Category Preferences by Customer Segment
WITH product_sales AS (
    SELECT 
        p.CategoryName,
        c.CustomerRelationshipTypeId,
        ol.Quantity,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        p.ProductID,
        o.CustomerId
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    INNER JOIN shared.customer c ON o.CustomerId = c.CustomerId
    WHERE o.OrderStatus = 'Completed'
),

segment_category AS (
    SELECT 
        CustomerRelationshipTypeId,
        CategoryName,
        SUM(LineRevenue) AS SegmentCategoryRevenue,
        SUM(Quantity) AS SegmentCategoryQuantity,
        COUNT(DISTINCT ProductID) AS ProductVariety,
        COUNT(DISTINCT CustomerId) AS CustomersInSegment
    FROM product_sales
    GROUP BY CustomerRelationshipTypeId, CategoryName
),

segment_totals AS (
    SELECT 
        CustomerRelationshipTypeId,
        SUM(SegmentCategoryRevenue) AS SegmentTotal
    FROM segment_category
    GROUP BY CustomerRelationshipTypeId
)

SELECT 
    sc.CustomerRelationshipTypeId,
    sc.CategoryName,
    ROUND(sc.SegmentCategoryRevenue, 2) AS SegmentCategoryRevenue,
    ROUND((sc.SegmentCategoryRevenue * 100.0 / st.SegmentTotal), 1) AS CategoryShare,
    sc.ProductVariety,
    sc.CustomersInSegment
FROM segment_category sc
INNER JOIN segment_totals st ON sc.CustomerRelationshipTypeId = st.CustomerRelationshipTypeId
ORDER BY sc.CustomerRelationshipTypeId, sc.SegmentCategoryRevenue DESC;

-- Top 15 Products by Sales Velocity (Order Frequency)
WITH product_sales AS (
    SELECT 
        p.ProductID,
        p.ProductName,
        p.CategoryName,
        ol.Quantity,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        o.OrderDate
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    WHERE o.OrderStatus = 'Completed'
)

SELECT TOP 15
    ProductID,
    ProductName,
    CategoryName,
    COUNT(DISTINCT CAST(OrderDate AS DATE)) AS DaysWithSales,
    COUNT(*) AS TotalOrderLines,
    SUM(Quantity) AS TotalQuantity,
    ROUND(SUM(LineRevenue), 2) AS TotalRevenue,
    ROUND(CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT CAST(OrderDate AS DATE)), 2) AS OrderLinesPerDay,
    ROUND(CAST(SUM(Quantity) AS FLOAT) / COUNT(*), 2) AS UnitsPerOrderLine
FROM product_sales
GROUP BY ProductID, ProductName, CategoryName
ORDER BY TotalOrderLines DESC;

-- Quarterly Sales Trends by Category
WITH quarterly_sales AS (
    SELECT 
        CONCAT(YEAR(o.OrderDate), '-Q', DATEPART(QUARTER, o.OrderDate)) AS Quarter,
        p.CategoryName,
        (ol.Quantity * ol.UnitPrice) AS LineRevenue,
        ol.Quantity,
        p.ProductID
    FROM salesfabric.orderline ol
    INNER JOIN salesfabric.[order] o ON ol.OrderId = o.OrderId
    INNER JOIN shared.product p ON ol.ProductId = p.ProductID
    WHERE o.OrderStatus = 'Completed'
)

SELECT 
    Quarter,
    CategoryName,
    ROUND(SUM(LineRevenue), 2) AS QuarterlyRevenue,
    SUM(Quantity) AS QuarterlyQuantity,
    COUNT(DISTINCT ProductID) AS ProductsSold
FROM quarterly_sales
GROUP BY Quarter, CategoryName
ORDER BY Quarter, QuarterlyRevenue DESC;
```