from importlib import import_module
import sys
import os

# allow modules located in parent directory
__path__.append(os.path.dirname(os.path.dirname(__file__)))

for name in ("routes", "main", "models", "database"):
    try:
        module = import_module(name)
        globals()[name] = module
        sys.modules[__name__ + '.' + name] = module
    except Exception:
        pass
