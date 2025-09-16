------------------------------------------------------
-- shared

SELECT COUNT(*) FROM shared.customer;

SELECT COUNT(*) FROM shared.customeraccount;

SELECT COUNT(*) FROM shared.customerrelationshiptype;

SELECT COUNT(*) FROM shared.customertradename;

SELECT COUNT(*) FROM shared.location;

SELECT COUNT(*) FROM shared.product;

SELECT COUNT(*) FROM shared.productcategory;

------------------------------------------------------
-- salesadb

SELECT COUNT(*) FROM salesadb.[order];

SELECT COUNT(*) FROM salesadb.orderline;

SELECT COUNT(*) FROM salesadb.orderpayment


------------------------------------------------------
-- salesfabric

SELECT COUNT(*) FROM salesfabric.[order];

SELECT COUNT(*) FROM salesfabric.orderline;

SELECT COUNT(*) FROM salesfabric.orderpayment

------------------------------------------------------
-- finance

SELECT COUNT(*) FROM finance.account;

SELECT COUNT(*) FROM finance.invoice;

SELECT COUNT(*) FROM finance.payment;


