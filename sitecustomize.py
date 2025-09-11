"""
Global test/runtime warning filters for third‑party SWIG wrappers.

Python automatically imports sitecustomize if it's importable on sys.path.
Keeping this at repo root ensures the filters apply early in tests and local runs.
"""
import warnings

warnings.filterwarnings(
    'ignore',
    message=r'builtin type (SwigPyObject|SwigPyPacked|swigvarlink) has no __module__ attribute',
    category=DeprecationWarning,
)

