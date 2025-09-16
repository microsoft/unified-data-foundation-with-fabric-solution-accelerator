# Jupyter Kernel Setup Instructions

To run Jupyter notebooks, you need a working Python environment with Jupyter installed.

## If you see an error like `'jupyter' is not recognized`:

### 1. Install Jupyter (if not already installed)
- Open a terminal or command prompt.
- Run:
  ```
  python -m pip install jupyter
  ```
- Or, if you use Anaconda:
  ```
  conda install jupyter
  ```

### 2. List available kernels
- In your terminal, run:
  ```
  python -m jupyter kernelspec list
  ```
- This will show all available kernels and their locations.

### 3. Select the kernel in your notebook
- In JupyterLab or Jupyter Notebook, go to the top menu:  
  `Kernel` → `Change kernel` → select the desired Python environment.

### 4. (Optional) Add your current environment as a kernel
If you want to add your current Python environment as a Jupyter kernel, run:
```
python -m ipykernel install --user --name myenv --display-name "Python (myenv)"
```
Replace `myenv` with your environment name.
