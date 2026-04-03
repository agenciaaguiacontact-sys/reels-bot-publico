from gdrive_api import GoogleDriveAPI

def create_test_folder():
    print("Tentando criar uma pasta de teste própria do Service Account...")
    drive = GoogleDriveAPI()
    if not drive.service:
        print("❌ Falha ao inicializar serviço.")
        return

    try:
        file_metadata = {
            'name': 'ReelsBot_Test_Folder',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = drive.service.files().create(body=file_metadata, fields='id').execute()
        folder_id = file.get('id')
        print(f"✅ Pasta de teste criada com sucesso! ID: {folder_id}")
        return folder_id
    except Exception as e:
        print(f"❌ Erro ao criar pasta: {e}")
        return None

if __name__ == "__main__":
    create_test_folder()
