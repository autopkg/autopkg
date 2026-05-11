# `nuspec` Generator

This is module wraps Python code generated via the `generateDS` library.

It provides a simple interface for programmatically constructing and outputting
valid `.nuspec` files to construct nuget or chocolatey packages.

## Using the simple wrapper

```python
from nuget import NuspecGenerator

pkg = NuspecGenerator(
    id="test",
    title="Test Software (Don't use!)",
    version="0.0.1",
    authors="me",
    description="Test software generated with python!"
)
```

## Using the generated code directly

```python
import nuget.generated._nuspec as nuspec


test = nuspec.package(
    metadata=nuspec.metadataType(
        id="test", version="0.0.1", authors="me", description="generated with
python!"
    )
)
with open("./test.nuspec", "w") as f:
    test.export(outfile=f, level=0)

with open("./test.nuspec", 'r') as f:
    print(f.read())
```

## Regenerating the definitions
The definitions can be (re)created by running the `regenerate_nuspec_ds.py` script as
shown below. The script automates some particulars around getting the schema `.xsd` file,
and setting the appropriate XML namespace. The script has more details for the curious.

```powershell
python Scripts\regenerate_nuspec_ds.py --output-path .\Code\nuget\generated\_nuspec.py
```
