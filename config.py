import os
from dotenv import load_dotenv

load_dotenv()

ALLEGRO_CLIENT_ID = os.getenv("ALLEGRO_CLIENT_ID", "")
ALLEGRO_CLIENT_SECRET = os.getenv("ALLEGRO_CLIENT_SECRET", "")

# Google Cloud Vision API key — used by image_search.py for reverse-image lookup.
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
