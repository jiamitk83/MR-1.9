import os

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "school_register.db")
BACKUP_DIR = DATA_DIR
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Application constants
APP_NAME = "School Mark Register"
VERSION = "1.9.0"
