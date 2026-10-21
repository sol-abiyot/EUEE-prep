import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_reload_script_asks_before_doing_anything():
    result = subprocess.run(
        [sys.executable, "db.py"],
        input="no\n",
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=30,
    )
    assert result.returncode == 0
    assert "Cancelled" in result.stdout