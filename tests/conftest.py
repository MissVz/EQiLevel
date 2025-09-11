import sys, pathlib, warnings
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Silence noisy deprecation warnings from SWIG-wrapped deps that we don't control
warnings.filterwarnings(
    'ignore',
    message=r"builtin type (SwigPyObject|SwigPyPacked|swigvarlink) has no __module__ attribute",
    category=DeprecationWarning,
)
