**Prompts from Gaiye** 

## From Bronze to Silver 

### **Task 1: Load Customer Table to Silver** 

I have created new file named Load_Bronze_Data_to_Silver_Table_Customer.ipynb. Need to write code in this notebook. 

The code will load sample data stored in this file from source location to target lakehouse table: 

- **Source**: MAAG_LH_Bronze/Files/samples/fabric/shared/Customer_Samples.csv
- **Target**: MAAG_LH_Silver.shared.Customer
- **Customer Table Schema**: Is defined in File Model_Shared_Data.ipynb 

You can refer to this sample file that has already been tested to work for another table: Load_Bronze_Data_to_Table_CustomerRelationship.ipynb

**With a lot of back and fourth work, finally the code worked.** 

### Task 2: Load CustomerAccount to Silver 

Previous data loading was successful. 

We can use the same pattern for more tables. Here is next one. 

Table name: CustomerAccount

Source File Name: CustomerAccount_Samples.csv

Notebook Name: Load_Bronze_Data_to_Table_CustomerAccount.ipynb

### Task 3: Load Location to Silver 

Previous data loading was successful. A BIG Thank you! 

We can use the same pattern for more tables. Here is next one. 

Table name: Location

Source File Name: :Location_Samples.csv

Notebook Name: Load_Bronze_Data_to_Table_Location.ipynb



### Task 4: Load Product to Silver 

Previous data loading was successful. A big Thank you again! 

We can use the same pattern for more tables. Here is next one. 

Table name: Product

Source File Name: Product_Samples.csv

Notebook Name: Load_Bronze_Data_to_Table_Product.ipynb



### Task 5: Load ProductCategory to Silver (Get Back to it from other tasks)

Need to refresh the Github Copilot! 

I just opened one file Model_Shared_Data.jpynb. Do you see it? (YES)

I just shared a new file, do you see it? Can you tell me the file name?

Load_Silver_to_Gold_Table_Product.ipynb



Okay good. We are going to do something similar to this notebook but for a new table. Below are the info

Table name: ProductCategory

Source File Name: ProductCategory_Samples.csv

Notebook Name: Load_Bronze_Data_to_Table_ProductCategory.ipynb



**It did not produce the code I wanted.** 

Good enough for starter. I need to check to see if key columns have valid data, like the 2nd Code cell of previous `Load_Bronze_Data_to_Table_Product.ipynb` file. You can read the schema info the table ProductCategory in `Model_Shared_Data.ipynb` 

This code will not work in Fabric. Can you set up code cell 1 like `Load_Bronze_Data_to_Table_Product.ipynb` file.? 

**After a few good prompts I am finally there.** 

**Gaiye**: It took me a while to figure out the working path. Dont want to use something that will not work. Thanks for your understanding

**Copilot**: You're welcome! I understand how important it is to use the correct Fabric file paths for reliable execution. If you need further adjustments or want to adapt this pattern for other tables or files, just let me know—I'll make sure to use the right Fabric-compatible paths and code structure.

