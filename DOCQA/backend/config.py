# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

ARXIV_API_KEY = os.getenv("ARXIV_API_KEY") # Arxiv API usually doesn't require a key for basic search, but good to have if needed.
UPLOAD_DIR = "uploaded_documents" # Directory to save uploaded PDFs
os.makedirs(UPLOAD_DIR, exist_ok=True)
