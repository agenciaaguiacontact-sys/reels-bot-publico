import sys, io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from gdrive_api import GoogleDriveAPI
import os
from dotenv import load_dotenv

load_dotenv()
drive = GoogleDriveAPI()
fid = os.getenv('GDRIVE_FOLDER_ID', 'NAO_DEFINIDO')
print(f'Folder ID local: [{fid}]')

try:
    results = drive.service.files().list(
        q="mimeType='application/json' and trashed=false",
        fields="files(id, name, parents)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get('files', [])
    print(f"Total arquivos JSON: {len(files)}")
    for f in files:
        parents = f.get('parents', ['sem pasta'])
        match = "[MATCH]" if fid in parents else ""
        print(f"{match} {f['name']} -> pasta {parents[0] if parents else 'n/a'}")
except Exception as e:
    print(f"Erro: {e}")
