import platform
import sys


def run_python_check() -> str:
    version = platform.python_version()
    executable = sys.executable
    return f"python {version} ({executable})"
