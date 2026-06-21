"""
papertrader/conftest.py

Test modules import the trading code as `import lib.engine`, `import lib.forecasts`,
etc. That only resolves when `papertrader/` is on sys.path — which happened
implicitly when pytest was invoked with the cwd at `papertrader/`, but NOT when
invoked from the repo root. The collection then failed with
`ModuleNotFoundError: No module named 'lib.forecasts'`, silently masking the real
test signal.

pytest discovers and imports this conftest before collecting tests in
`papertrader/tests/`, so inserting this directory onto sys.path here makes
`import lib.*` resolve no matter which directory `pytest` is launched from.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
