# Bundled installer dependency

`tomlkit-0.13.3-py3-none-any.whl` is the unmodified pure-Python wheel from
[official PyPI](https://pypi.org/project/tomlkit/0.13.3/), downloaded on 2026-10-14.
The upstream wheel's SHA-256 was verified against PyPI release metadata:

```text
c89c649d79ee40629a9fda55f8ace8c6a1b42deb912b2a8fd8d942ddadb606b0
```

The launcher verifies that hash before adding the wheel to Python's import path.
It does not extract, download, install or upgrade packages at runtime. The wheel
retains its distribution metadata and MIT license; `tomlkit-LICENSE` is an additional
copy of the upstream license. Upstream repository:
[python-poetry/tomlkit](https://github.com/python-poetry/tomlkit).

Only the installer engine uses this dependency. Installed context/Git hooks remain
standard-library-only and independent of the CLI distribution.
