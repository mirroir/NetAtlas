import os

from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).parent.parent
ENV_TEST = ROOT_DIR / ".env.test"

load_dotenv(ENV_TEST, override=True)

os.environ["NETATLAS_ENV"] = "test"
