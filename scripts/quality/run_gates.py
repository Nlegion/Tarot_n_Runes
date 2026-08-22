"""Quality gate runner."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = [
    [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
    [sys.executable, "-m", "ruff", "format", "--check", "."],
    [sys.executable, "-m", "bandit", "-r", "src", "-c", ".bandit"],
    [sys.executable, "-m", "vulture", "src", "--min-confidence", "80"],
    [sys.executable, "-m", "pytest", "tests", "-q"],
]


def main() -> int:
    for cmd in COMMANDS:
        print(f"\n>>> {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode
    print("\nAll quality gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
