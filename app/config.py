import os

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'school_register.db')}"

# Application constants
APP_NAME = "School Mark Register"
VERSION = "1.9.0"
