I need to generate sample data for the Finance domain, integrating with the Sales domain. The requirements are:

# Input Data Sources:

- Customer data: Customer_Samples.csv
- Order data: All Order_Samples_*.csv files (for Fabric and ADB channels)
- Order payment data: All OrderPayment_*.csv files
# Invoice Table:

- Create an invoice for every order.
- Set InvoiceStatus based on OrderStatus:
    - "Completed", "Shipped", "Pending" → "Issued"
    - "Cancelled" → "Cancelled"
    - "Returned" → "Refunded"
- Include all relevant fields: InvoiceId, InvoiceNumber, CustomerId, OrderId, InvoiceDate, DueDate, SubTotal, TaxAmount, TotalAmount, InvoiceStatus.
# Payment Table:

- Create a payment record for every order.
- Use actual payment details from the OrderPayment table if available; otherwise, generate a default payment.
- Set PaymentStatus based on OrderStatus:
    - "Completed", "Shipped" → "Completed"
    - "Pending" → "Pending"
    - "Cancelled" → "Failed"
    - "Returned" → "Refunded"
- Only payments with status "Completed" should reduce the account balance.
# Account Table:

- For each customer, create an account record.
- Set CreatedDate as the earliest order date for each customer, or use a default if not available.
- Set AccountStatus to "Active" if the balance is zero, otherwise "Overdue".
- Include all relevant fields: AccountId, AccountNumber, CustomerId, AccountType, AccountStatus, CreatedDate, ClosedDate, Balance, Currency, Description.
# Output:

- Save Invoice, Payment, and Account tables as CSV files in the finance_generation_output directory, segregated by sales channel (Fabric, ADB).
## General Logic:

Consider all order statuses, not just "Completed".
Ignore OrderLine table for finance data generation.
Ensure all foreign keys and relationships are consistent.
# Goal:
Produce realistic, consistent, and comprehensive sample data for the Finance domain, reflecting all business scenarios and supporting downstream analytics and integration.