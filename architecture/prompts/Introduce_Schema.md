**Prompt to GitHub Copilot**

I have below files that defines the semantic model, schemas for three domains, all located in this folder

src/fabric/notebooks/schema/

 (1) **Shared Domain**: src/fabric/notebooks/schema/Model_Shared_Data.ipynb, which defines tables for Customer and Product.

**Customer (7 Tables)**

- Customer 
- CustomerRelationshipType 
- CustomerTradeName 
- Location 
- CustomerLocation
- CustomerAccount
- CustomerAccountLocation

**Product  (2 Tables)**

- Product,
- Category

(2) **Sales Domain**: src/fabric/notebooks/schema/Model_Sales_Domain.ipynb, defines 3 tables in Sales domain 

- Order
- OrderLine
- OrderPayment

(3) **Finance Domain**: src/fabric/notebooks/schema/Model_Finance_Domain.ipynb, which defines 4 tables in Finance Domain 

- Account
- Invoice
- Payment
- Transaction

