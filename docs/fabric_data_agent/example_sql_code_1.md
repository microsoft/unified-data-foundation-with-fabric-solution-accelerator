```sql
-- Customer Segmentation Analysis - Detailed View by Relationship Type and Gender
WITH customer_segmentation AS (
    SELECT 
        CustomerRelationshipTypeId,
        Gender,
        DATEDIFF(YEAR, DateOfBirth, GETDATE()) AS Age,
        IsActive
    FROM shared.customer
    WHERE DateOfBirth IS NOT NULL 
      AND Gender IS NOT NULL
),

segmentation_metrics AS (
    SELECT 
        CustomerRelationshipTypeId,
        Gender,
        COUNT(*) AS CustomerCount,
        ROUND(AVG(CAST(Age AS FLOAT)), 1) AS AvgAge,
        SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) AS ActiveCustomers,
        SUM(CASE WHEN IsActive = 'False' THEN 1 ELSE 0 END) AS InactiveCustomers,
        ROUND(
            (SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 
            1
        ) AS ActivePercentage
    FROM customer_segmentation
    GROUP BY CustomerRelationshipTypeId, Gender
),

total_customers AS (
    SELECT COUNT(*) AS TotalCount
    FROM customer_segmentation
)

SELECT 
    sm.CustomerRelationshipTypeId AS [Relationship Type],
    sm.Gender,
    sm.CustomerCount AS [Total Customers],
    CONCAT(sm.AvgAge, ' years') AS [Average Age],
    CONCAT(sm.ActiveCustomers, ' / ', sm.InactiveCustomers) AS [Active / Inactive],
    CONCAT(CAST(sm.ActivePercentage AS DECIMAL(5,1)), '%') AS [Activity Rate],
    CONCAT(CAST(ROUND((sm.CustomerCount * 100.0 / tc.TotalCount), 1) AS DECIMAL(5,1)), '%') AS [% of Total Base]
FROM segmentation_metrics sm
CROSS JOIN total_customers tc
ORDER BY 
    sm.CustomerCount DESC, 
    sm.CustomerRelationshipTypeId, 
    CASE WHEN sm.Gender = 'Male' THEN 1 ELSE 2 END;

-- Executive Summary by Relationship Type Only
WITH customer_segmentation AS (
    SELECT 
        CustomerRelationshipTypeId,
        Gender,
        DATEDIFF(YEAR, DateOfBirth, GETDATE()) AS Age,
        IsActive
    FROM shared.customer
    WHERE DateOfBirth IS NOT NULL 
      AND Gender IS NOT NULL
),

segmentation_metrics AS (
    SELECT 
        CustomerRelationshipTypeId,
        Gender,
        COUNT(*) AS CustomerCount,
        ROUND(AVG(CAST(Age AS FLOAT)), 1) AS AvgAge,
        SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) AS ActiveCustomers,
        ROUND(
            (SUM(CASE WHEN IsActive = 'True' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 
            1
        ) AS ActivePercentage
    FROM customer_segmentation
    GROUP BY CustomerRelationshipTypeId, Gender
),

total_customers AS (
    SELECT COUNT(*) AS TotalCount
    FROM customer_segmentation
)

SELECT 
    CustomerRelationshipTypeId AS [Relationship Type],
    SUM(CustomerCount) AS [Total Customers],
    CONCAT(ROUND(AVG(AvgAge), 1), ' years') AS [Average Age],
    SUM(ActiveCustomers) AS [Active Customers],
    CONCAT(CAST(ROUND(AVG(ActivePercentage), 1) AS DECIMAL(5,1)), '%') AS [Average Activity Rate],
    CONCAT(CAST(ROUND((SUM(CustomerCount) * 100.0 / MAX(tc.TotalCount)), 1) AS DECIMAL(5,1)), '%') AS [% of Customer Base]
FROM segmentation_metrics sm
CROSS JOIN total_customers tc
GROUP BY CustomerRelationshipTypeId, tc.TotalCount
ORDER BY SUM(CustomerCount) DESC;
```