from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_generation_quota_command_starts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        [sys.executable, "main.py", "generation-quota", "--iterations", "1"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"iterations": 1' in result.stdout
