import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "PrototypeScarlett"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
