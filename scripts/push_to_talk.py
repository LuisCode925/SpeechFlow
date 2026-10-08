"""Punto de entrada de push-to-talk; la lógica vive en src/speechflow/app.py (`--help` muestra su documentación)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from speechflow.app import main

if __name__ == "__main__":
    main()
