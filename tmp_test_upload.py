import os
import json
from gdrive_api import GoogleDriveAPI

def test_upload():
    print("Iniciando teste de upload no Google Drive...")
    drive = GoogleDriveAPI()
    if not drive.service:
        print("❌ Falha ao inicializar o serviço.")
        return

    try:
        with open('accounts.json', 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        
        folder_id = accounts[0].get('gdrive_folder_id')
        print(f"Tentando upload na pasta: {folder_id} ({accounts[0]['name']})")
        
        # Criar arquivo temporário de 1 byte
        test_file = "tmp_test_upload.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        
        file_id = drive.upload_file(test_file, test_file, 'text/plain', folder_id)
        if file_id:
            print(f"✅ Upload bem-sucedido! ID: {file_id}")
            # Deletar logo em seguida
            drive.delete_file(file_id)
            print("✅ Arquivo de teste deletado.")
        else:
            print("❌ Falha no upload. Verifique as permissões de edição do Service Account na pasta.")

        os.remove(test_file)

    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_upload()
