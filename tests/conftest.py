import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
PYTHON_DIR = ROOT_DIR / "python"

sys.path.insert(0, str(PYTHON_DIR))

ENV_TEST = ROOT_DIR / ".env.test"

load_dotenv(ENV_TEST, override=True)

os.environ["NETATLAS_ENV"] = "test"
