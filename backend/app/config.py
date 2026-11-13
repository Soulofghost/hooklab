import os

PORT = int(os.getenv("HOOKLAB_PORT", "8000"))
DB_PATH = os.getenv("HOOKLAB_DB_PATH", "backend/data/hooklab.db")
