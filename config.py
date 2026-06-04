import os
from dotenv import load_dotenv

load_dotenv()

ALLEGRO_CLIENT_ID = os.getenv("ALLEGRO_CLIENT_ID", "")
ALLEGRO_CLIENT_SECRET = os.getenv("ALLEGRO_CLIENT_SECRET", "")
