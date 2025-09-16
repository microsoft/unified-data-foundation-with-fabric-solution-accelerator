### Steps 



1.  Implement main.bicep etc like other GSA SAs (CKM, Code Mod, Multi-Agent)

2. Add azure pipeline azure-dev.ymal to **our GitHub Repo** like this: [Modernize-your-code-solution-accelerator/.azdo/pipelines/azure-dev.yml at main · microsoft/Modernize-your-code-solution-accelerator · GitHub](https://github.com/microsoft/Modernize-your-code-solution-accelerator/blob/main/.azdo/pipelines/azure-dev.yml)

   This only works in github but I have a draft here: [azure-dev-yaml](./github-piplines-azure-dev.yml)

3. Once we make the azure pipeline `azure-dev.ymal` work and we can submit for approval 
   (**Note**: Can we put a empty process like the code does nothing to make the process work?)

4. In parallel, work on code to deploy via main.bicep, .sh file, and python code and test the azd deployment process. 

   

   Note: Maintenance team is helping Agentic Data Asset and we can speak with Anish about this.  



### To-Dos

[AI Gallery Template submission](https://forms.office.com/pages/responsepage.aspx?id=v4j5cvGGr0GRqy180BHbR2lMW2bWVFdFjNIJRIvVmQZURDVOSUZGUkhBR1ZMUlVIM1A1U1NXUzE3VC4u&route=shorturl)

[azd-template-artifacts/publishing-guidelines.md at main · Azure-Samples/azd-template-artifacts · GitHub](https://github.com/Azure-Samples/azd-template-artifacts/blob/main/publishing-guidelines.md)



For additional docs, please review [AZD Template Resources](../Deployment/AZD Telemetry Resources.md)