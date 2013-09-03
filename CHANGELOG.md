### 0.2.2 (unreleased)

CHANGES:

- Pkg recipe runs now print a report output similar to Munki recipes, and have version, identifier information available in the report.

### 0.2.1 (September 2, 2013)

CHANGES:

- Relative paths given for "infofile", "resources", "options", "scripts" in a PkgCreator's pkg_request dictionary should now work if this path is found at the current working directory (GH-20)

### 0.2.0 (September 1, 2013)

CHANGES:

- The recipe identifier is now named "Identifier" and is a top-level recipe key. 
- The "recipe" key formerly seen in overrides has been renamed "ParentRecipe". Its value is now a string -- the identifier of its parent recipes.
- There is now essentially no difference between an "override" and a child recipe; a recipe can refer to a parent recipe, which can in turn refer to its own parent recipe, and so on.
- Child recipes can override keys in the Input dictionary and/or add new key/value pairs to the Input dictionary. This is the same functionality that RecipeOverrides have.
- Child recipes can add additional steps to the end of the Process of their ParentRecipe(s).  This is new functionality.
- Searching for recipes has changed: the order of searching by name and by identifier have been swapped: identifier is preferred to simple name.
- Certain Processors (specifically PkgInfoCreator and PkgCreator) are typically given paths to templates or resources or scripts pointing to the directory of the recipe. If a recipe can now have one or more parents, the meaning of "RECIPE_DIR" is a little unclear. So for this sort of thing, we now search the current child recipe directory for the requested resource, followed by any parent recipe's directory, then any parent recipe of the parent recipe's directory, etc. To support this behavior, give PkgInfoCreator and PkgCreator relative paths to PackageInfoTemplates and Resources and Scripts directories.
- New verbs to help people learn about Processors:
    - `autopkg list-processors` returns a list of "core" Processors -- those available to all recipes (in autopkglib)
    - `autopkg processor-info PROCESSORNAME` prints basic documentation for PROCESSORNAME; use `autopkg processor-info <ProcessorName> --recipe RECIPE` to get basic docs on a recipe-specific Processor (like MozillaURLProvider).

### 0.1.1 (August 27, 2013)

CHANGES:

  - Addresses an issue where creating RecipeOverrides failed if the recipe overrides directory (default: ~/Library/AutoPkg/ReceipeOverrides) is missing

### 0.1.0 (August 23, 2013)

FEATURES:

  - Initial pkg release.
