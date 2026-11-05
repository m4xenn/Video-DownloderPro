"""Release runtime security floor; source development remains independent."""
import sys


def require_secure_python(version=None):
    current=tuple(version or sys.version_info[:3])
    minimums={(3,12):(3,12,16),(3,13):(3,13,18),(3,14):(3,14,10),(3,15):(3,15,2)}
    floor=minimums.get(current[:2])
    if floor is None or current<floor:
        raise RuntimeError('Use a security-patched Python runtime; the audited Windows build uses Python 3.14.10 or newer in that series.')
