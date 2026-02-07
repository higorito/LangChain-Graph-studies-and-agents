from dotenv import load_dotenv
from checkpointers.env import get_env

load_dotenv()

DB_DSN = get_env("DB_DSN")