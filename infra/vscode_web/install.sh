pip install --index-url "${PIP_INDEX_URL:-https://packagefeedproxy.microsoft.io/pypi/simple/}" -r requirements.txt --user -q

azd init -t microsoft/unified-data-foundation-with-fabric-solution-accelerator