```sql
-- Sales Performance and Customer Value Analysis

-- Top 20 Customers by Total Revenue
WITH customer_value AS (
    SELECT 
        c.CustomerId,
        c.FirstName,
        c.LastName,
        c.CustomerRelationshipTypeId,
        COUNT(o.OrderId) AS TotalOrders,
        SUM(o.OrderTotal) AS TotalRevenue,
        ROUND(AVG(o.OrderTotal), 2) AS AvgOrderValue,
        MIN(o.OrderDate) AS FirstOrderDate,
        MAX(o.OrderDate) AS LastOrderDate,
        DATEDIFF(DAY, MIN(o.OrderDate), MAX(o.OrderDate)) AS CustomerLifespan_Days
    FROM shared.customer c
    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId
    WHERE o.OrderStatus = 'Completed'
    GROUP BY c.CustomerId, c.FirstName, c.LastName, c.CustomerRelationshipTypeId
)

SELECT TOP 20
    CustomerId,
    FirstName,
    LastName,
    CustomerRelationshipTypeId,
    ROUND(TotalRevenue, 2) AS TotalRevenue,
    TotalOrders,
    AvgOrderValue
FROM customer_value
ORDER BY TotalRevenue DESC;

-- Customer Segment Performance Analysis
WITH customer_value AS (
    SELECT 
        c.CustomerId,
        c.CustomerRelationshipTypeId,
        COUNT(o.OrderId) AS TotalOrders,
        SUM(o.OrderTotal) AS TotalRevenue,
        AVG(o.OrderTotal) AS AvgOrderValue
    FROM shared.customer c
    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId
    WHERE o.OrderStatus = 'Completed'
    GROUP BY c.CustomerId, c.CustomerRelationshipTypeId
),

total_revenue AS (
    SELECT SUM(OrderTotal) AS TotalRevenue
    FROM salesfabric.[order]
    WHERE OrderStatus = 'Completed'
)

SELECT 
    cv.CustomerRelationshipTypeId,
    COUNT(cv.CustomerId) AS CustomerCount,
    ROUND(SUM(cv.TotalRevenue), 2) AS SegmentRevenue,
    ROUND(AVG(cv.TotalRevenue), 2) AS AvgRevenuePerCustomer,
    SUM(cv.TotalOrders) AS SegmentOrders,
    ROUND(AVG(CAST(cv.TotalOrders AS FLOAT)), 1) AS AvgOrdersPerCustomer,
    ROUND(AVG(cv.AvgOrderValue), 2) AS SegmentAvgOrderValue,
    ROUND((SUM(cv.TotalRevenue) * 100.0 / tr.TotalRevenue), 2) AS RevenuePercentage
FROM customer_value cv
CROSS JOIN total_revenue tr
GROUP BY cv.CustomerRelationshipTypeId, tr.TotalRevenue
ORDER BY SegmentRevenue DESC;

-- Monthly Sales Trends
SELECT 
    YEAR(OrderDate) AS OrderYear,
    MONTH(OrderDate) AS OrderMonth,
    FORMAT(OrderDate, 'yyyy-MM') AS YearMonth,
    COUNT(OrderId) AS MonthlyOrders,
    ROUND(SUM(OrderTotal), 2) AS MonthlyRevenue,
    ROUND(AVG(OrderTotal), 2) AS MonthlyAvgOrderValue,
    COUNT(DISTINCT CustomerId) AS UniqueCustomers
FROM salesfabric.[order]
WHERE OrderStatus = 'Completed'
GROUP BY YEAR(OrderDate), MONTH(OrderDate), FORMAT(OrderDate, 'yyyy-MM')
ORDER BY OrderYear, OrderMonth;

-- Seasonal Sales Analysis
WITH seasonal_sales AS (
    SELECT 
        CASE 
            WHEN MONTH(OrderDate) IN (12, 1, 2) THEN 'Winter'
            WHEN MONTH(OrderDate) IN (3, 4, 5) THEN 'Spring'
            WHEN MONTH(OrderDate) IN (6, 7, 8) THEN 'Summer'
            ELSE 'Fall'
        END AS Season,
        OrderId,
        OrderTotal,
        CustomerId
    FROM salesfabric.[order]
    WHERE OrderStatus = 'Completed'
),

total_revenue AS (
    SELECT SUM(OrderTotal) AS TotalRevenue
    FROM salesfabric.[order]
    WHERE OrderStatus = 'Completed'
)

SELECT 
    ss.Season,
    COUNT(ss.OrderId) AS SeasonalOrders,
    ROUND(SUM(ss.OrderTotal), 2) AS SeasonalRevenue,
    ROUND(AVG(ss.OrderTotal), 2) AS SeasonalAvgOrderValue,
    COUNT(DISTINCT ss.CustomerId) AS UniqueSeasonalCustomers,
    ROUND((SUM(ss.OrderTotal) * 100.0 / tr.TotalRevenue), 2) AS RevenuePercentage
FROM seasonal_sales ss
CROSS JOIN total_revenue tr
GROUP BY ss.Season, tr.TotalRevenue
ORDER BY SeasonalRevenue DESC;

-- High-Value Customer Analysis (Top 10%)
WITH customer_value AS (
    SELECT 
        c.CustomerId,
        c.FirstName,
        c.LastName,
        c.CustomerRelationshipTypeId,
        SUM(o.OrderTotal) AS TotalRevenue,
        COUNT(o.OrderId) AS TotalOrders
    FROM shared.customer c
    INNER JOIN salesfabric.[order] o ON c.CustomerId = o.CustomerId
    WHERE o.OrderStatus = 'Completed'
    GROUP BY c.CustomerId, c.FirstName, c.LastName, c.CustomerRelationshipTypeId
),

customer_percentile AS (
    SELECT 
        *,
        NTILE(10) OVER (ORDER BY TotalRevenue DESC) AS RevenueDecile
    FROM customer_value
)

SELECT 
    COUNT(*) AS HighValueCustomerCount,
    ROUND(SUM(TotalRevenue), 2) AS HighValueRevenue,
    ROUND(AVG(TotalRevenue), 2) AS AvgHighValueRevenue,
    SUM(TotalOrders) AS HighValueOrders
FROM customer_percentile
WHERE RevenueDecile = 1;
```