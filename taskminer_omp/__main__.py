"""python -m taskminer_omp <rl-env-use args...>

Patches rl-env-use's browser seam onto omp's browser relay, then runs
rl-env-use's own CLI. Everything downstream of the browser (plan, mine,
write, verify, panel, harden, climb, export) is untouched.

Needs the rl-env-use checkout importable (sibling ../taskminer, or installed).
"""

import os
import sys


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    # sibling clone from the research step; harmless if rl_env_use is installed
    sys.path.insert(0, os.path.join(os.path.dirname(here), "taskminer"))

    from taskminer_omp.browser_omp import patch

    patch()

    from rl_env_use.__main__ import main as rl_main

    return rl_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
