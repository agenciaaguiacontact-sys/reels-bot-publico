import os
import json
from gdrive_api import GoogleDriveAPI

def test_connection():
    print("Iniciando teste de conexão com o Google Drive...")
    drive = GoogleDriveAPI()
    if not drive.service:
        print("❌ Falha ao inicializar o serviço do Google Drive. Verifique credentials.json ou GDRIVE_JSON_B64.")
        return

    try:
        # Tentar listar arquivos da primeira conta para ver se temos acesso
        with open('accounts.json', 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        
        if not accounts:
            print("❌ accounts.json vazio ou não encontrado.")
            return

        folder_id = accounts[0].get('gdrive_folder_id')
        print(f"Testando acesso à pasta: {folder_id} ({accounts[0]['name']})")
        
        files = drive.list_files_in_folder(folder_id)
        if files is not None:
            print(f"✅ Conexão estabelecida! Encontrados {len(files)} arquivos.")
            for f in files[:5]:
                print(f"  - {f['name']} ({f['id']})")
        else:
            print("❌ Falha ao listar arquivos na pasta.")

    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_connection()
