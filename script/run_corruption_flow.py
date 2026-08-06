from __future__ import annotations

from pathlib import Path
import sys

# Tự động thêm 'src' vào sys.path nếu chưa có
_root = Path(__file__).resolve().parent.parent
_src_dir = _root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from pipelines.corruption_flow import main

if __name__ == "__main__":
    main()
