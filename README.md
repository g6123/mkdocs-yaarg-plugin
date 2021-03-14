# mkdocs-yaarg-plugin

**Y**et **A**nother **A**PI **R**eference **G**enerator plugin for [MKDocs](https://www.mkdocs.org/).

## Installation

Install package from PyPI,

```
pip install mkdocs-yaarg-plugin[parso]
```

then add it to `mkdocs.yml`:

```yaml
plugins:
  - yaarg
```

## Usage

```markdown
# API Reference

::: some/filepath/to/module.py
```

~See [documentation]() for other options and details.~ WIP

## Why

As a Python docstring documentation generator:

- Fast & static

`yaarg`'s default Python generator does not depend on any runtime data.
Executing Python code to build a documentation is simply unnecessary, slow and potentially dangerous.

Instead, `yaarg` directly reads and parses Python code to find docstrings and type annotations.
It is powered by [Parso](https://parso.readthedocs.io/en/latest/), which has been battle-tested by VSCode.

As a general API reference generator:

- Language agnostic
- Unopinionated on how markdown output should look like

So that one can easily exploit exisiting documentation tooling in their eco-system.
