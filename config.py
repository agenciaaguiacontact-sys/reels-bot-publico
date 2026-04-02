import os
from dotenv import load_dotenv

load_dotenv()

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")

if not META_ACCESS_TOKEN:
    print("Aviso: META_ACCESS_TOKEN não configurado no .env")
