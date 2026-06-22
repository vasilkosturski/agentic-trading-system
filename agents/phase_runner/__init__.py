"""One trading cycle, top to bottom.

Public Interface: ``run_cycle``. Everything else (``Lifecycle``, telemetry
helpers, per-phase functions) is private to the package — leading underscore
on the module name and not re-exported here.
"""

from phase_runner.cycle import run_cycle

__all__ = ["run_cycle"]
