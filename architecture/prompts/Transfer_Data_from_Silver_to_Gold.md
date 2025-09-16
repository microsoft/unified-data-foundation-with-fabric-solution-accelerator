**Prompts from Gaiye** 

## From Silver to Gold 

We have completed data loading from Bronze Files to Silver Lakehouse for 6 tables. 

Now we need to load the data from Tables in Silver Lakehouse to Gold Lakehouse. 

The data model for the tables are stored in Model_Shared_Data.ipynb which I am sharing with you now. 

I have a notebook that has been tested that you can use as a reference: Load_Silver_to_Gold_Table_CustomerRelationshipType.ipynb. I am sharing this file with you now.

Let me know if you can see these two files I mentioned. 

**GitHub Copilot**: I can see the contents of `Model_Shared_Data.ipynb` that you have provided. However, I do not yet see the file `Load_Silver_to_Gold_Table_CustomerRelationshipType.ipynb`. Please provide or upload the contents of that notebook so I can use it as a reference for your next steps.

Gaiye opened the file and asked: Can you see it now? 

**GitHub Copilot**: Yes, I can now see both files:

- `Model_Shared_Data.ipynb` (data model/schema)
- `Load_Silver_to_Gold_Table_CustomerRelationshipType.ipynb` (reference notebook for Silver to Gold loading)

Let me know which table you want to process next or if you need a new notebook generated for another table.

#### Task 1: Load Table Customer 

Next table is: Customer

Notebook name (created for you): `Load_Silver_to_Gold_Table_Customer.ipynb`

Table Name in Silver: customer. Schema name in silver: shared.

Table Name in Gold: customer. Schema name in silver: shared.



#### Task 2: Load Table CustomerAccount 

It worked! I checked the data in Gold Tier and it looks good. Thank you! 

Next table is: CustomerAccount

Notebook name (created for you): `Load_Silver_to_Gold_Table_CustomerAccount.ipynb`

#### Task 3: Load Table CustomerTradeName

It worked! I checked the data in Gold Tier and it looks good. Thank you! 

Next table is: CustomerTradeName

Notebook name (created for you): `Load_Silver_to_Gold_Table_CustomerTradeName.ipynb`

#### Task 4: Load Table Location

It worked! I checked the data in Gold Tier and it looks good. Thank you! 

Next table is: Location

Notebook name (created for you): `Load_Silver_to_Gold_Table_Location.ipynb`

#### Task 5: Load Table Product

It worked! I checked the data in Gold Tier and it looks good. Thank you! 

Next table is: Product

Notebook name (created for you): `Load_Silver_to_Gold_Table_Product.ipynb`



#### Task 6: Load Table ProductCateory (Get back to this type of tasks. Need re-introduction)

The ProductCateory table is now created in the Lake House named MAAG_LH_Silver. I need to copy the data from MAAG_LH_Silver to MAAG_LH_Gold, same table name, same schema name. 

I am providing a working example for another table (please dont modify this notebook). You can use this as a reference pattern: `Load_Silver_to_Gold_Table_Product.ipynb.` This notebook sets up correct path. 

Table Name: ProductCategory

Table Schema is defined in `Model_Shared_Data.ipynb` 

Notebook name (created for you to create code): `Load_Silver_to_Gold_Table_ProductCategory.ipynb`

First do you see the three files I mentioned and opened in Visual Studio Code? 

