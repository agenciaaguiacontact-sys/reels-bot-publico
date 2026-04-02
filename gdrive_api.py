import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from config import GDRIVE_FOLDER_ID

class GoogleDriveAPI:
    def __init__(self, credentials_path='credentials.json'):
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.folder_id = GDRIVE_FOLDER_ID
        
        # 1. Tentar carregar via Base64 (O mais seguro para Nuvem)
        gdrive_b64 = os.getenv('GDRIVE_JSON_B64')
        if gdrive_b64:
            import base64
            try:
                # Decodifica e limpa possíveis quebras de linha/espaços do Github
                decoded = base64.b64decode(gdrive_b64.strip()).decode('utf-8')
                creds_dict = json.loads(decoded)
                
                # RECONSTRUTOR DE PEM: Corrige se o PDF/JSON tiver vindo com \n escapados
                if 'private_key' in creds_dict:
                    pk = creds_dict['private_key']
                    if "\\n" in pk:
                        creds_dict['private_key'] = pk.replace("\\n", "\n")
                
                self.creds = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=self.scopes)
                print("✅ Credenciais do Google Drive carregadas via Base64.")
            except Exception as e:
                print(f"❌ Erro ao decodificar GDRIVE_JSON_B64: {e}")
                self.service = None
                return
        
        # 2. Tentar via variável de ambiente limpa (Legado)
        elif os.getenv('GDRIVE_CREDENTIALS_JSON'):
            credentials_json = os.getenv('GDRIVE_CREDENTIALS_JSON')
            try:
                creds_dict = json.loads(credentials_json)
                self.creds = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=self.scopes)
            except Exception as e:
                print(f"Erro ao carregar credenciais da variável de ambiente: {e}")
                self.service = None
                return
        
        # 3. Tentar via arquivo local (Desktop)
        elif os.path.exists(credentials_path):
            self.creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=self.scopes)
        else:
            print(f"Aviso: Nem variável GDRIVE_JSON_B64 nem arquivo {credentials_path} foram encontrados!")
            self.service = None
            return

        self.service = build('drive', 'v3', credentials=self.creds)

    def list_mp4_files(self, folder_id=None):
        """Lista todos os arquivos .mp4 na pasta configurada ou na pasta informada"""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id:
            return []
            
        # Busca apenas arquivos de vídeo na pasta específica que não estão na lixeira
        query = f"'{f_id}' in parents and mimeType='video/mp4' and trashed=false"
        
        all_items = []
        page_token = None
        
        try:
            while True:
                results = self.service.files().list(
                    q=query, 
                    pageSize=100, # Aumentado para eficiência
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, parents)"
                ).execute()
                
                all_items.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                
                if not page_token:
                    break
                    
            return all_items
        except Exception as e:
            print(f"Erro ao listar arquivos do Drive: {e}")
            return all_items # Retorna o que conseguiu até agora
    
    def list_subfolders(self, folder_id=None):
        """Lista todas as subpastas dentro de uma pasta"""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id:
            return []
        
        query = f"'{f_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        all_folders = []
        page_token = None
        
        try:
            while True:
                results = self.service.files().list(
                    q=query, 
                    pageSize=100, 
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name)"
                ).execute()
                
                all_folders.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                
                if not page_token:
                    break
                    
            return all_folders
        except Exception as e:
            print(f"Erro ao listar subpastas: {e}")
            return all_folders
    
    def list_mp4_files_with_folders(self, folder_id=None):
        """Lista vídeos incluindo informação da subpasta"""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id:
            return []
        
        all_videos = []
        
        # Listar vídeos na pasta raiz
        root_videos = self.list_mp4_files(f_id)
        for v in root_videos:
            v['folder'] = None
            all_videos.append(v)
        
        # Listar subpastas e seus vídeos
        subfolders = self.list_subfolders(f_id)
        for subfolder in subfolders:
            subfolder_videos = self.list_mp4_files(subfolder['id'])
            for v in subfolder_videos:
                v['folder'] = subfolder['name']
                all_videos.append(v)
        
        return all_videos

    def download_file(self, file_id, file_name, destination_folder='./downloads'):
        """Baixa o arquivo do Google Drive para a máquina local"""
        if not self.service:
            print("Serviço do Drive indisponível. Abortando download.")
            return None
            
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            
        file_path = os.path.join(destination_folder, file_name)
        print(f"Baixando {file_name}...")
        
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(file_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download {int(status.progress() * 100)}%.")
                
        print(f"Download concluído: {file_path}")
        return file_path

    def delete_file(self, file_id):
        """Apaga (ou move para a lixeira) o arquivo após ser postado"""
        if not self.service:
            print("Serviço do Drive indisponível. Não foi possível apagar o arquivo.")
            return

        try:
            # Tenta apagar permanentemente
            self.service.files().delete(fileId=file_id).execute()
            print("✅ Arquivo apagado do Drive permanentemente.")
        except Exception as e:
            if "insufficientFilePermissions" in str(e) or "insufficientPermissions" in str(e):
                print(f"⚠️ Sem permissão para delete permanente: Movendo para lixeira...")
                try:
                    self.service.files().update(fileId=file_id, body={'trashed': True}).execute()
                    print("✅ Arquivo movido para a lixeira do Drive.")
                except Exception as e2:
                    print(f"❌ Falha total ao remover arquivo: {e2}")
            else:
                print(f"❌ Erro ao apagar arquivo do Drive: {e}")

    def upload_file(self, file_path, name, mimetype='video/mp4', folder_id=None):
        """Faz o upload de um arquivo para a pasta do GDrive"""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id:
            return None
        file_metadata = {'name': name, 'parents': [f_id]}
        media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"Erro ao fazer upload: {e}")
            return None

    def search_file_by_name(self, name, folder_id=None):
        """Busca um arquivo pelo nome exato na pasta e retorna o ID"""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id:
            return None
        query = f"'{f_id}' in parents and name='{name}' and trashed=false"
        try:
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])
            if items:
                return items[0]['id']
            return None
        except Exception:
            return None

    def get_json(self, name, folder_id=None):
        """Baixa e lê um arquivo JSON (ex: schedule_queue.json) pelo nome"""
        file_id = self.search_file_by_name(name, folder_id)
        if not file_id:
            return None
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"Erro ao ler JSON: {e}")
            return None

    def save_json(self, name, data, folder_id=None):
        """Salva ou atualiza um JSON na núvem"""
        if not self.service:
            return False
            
        f_id = folder_id or self.folder_id
        
        with open("temp_upload.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        file_id = self.search_file_by_name(name, f_id)
        try:
            # Define o content-type para JSON garantindo formato suportado
            mimetype = 'application/json'
            if file_id:
                media = MediaFileUpload("temp_upload.json", mimetype=mimetype)
                self.service.files().update(fileId=file_id, media_body=media).execute()
            else:
                media = MediaFileUpload("temp_upload.json", mimetype=mimetype)
                file_metadata = {'name': name, 'parents': [f_id]}
                self.service.files().create(body=file_metadata, media_body=media).execute()
        except Exception as e:
            print(f"Erro ao salvar JSON no Drive: {e}")
            return False
        finally:
            if os.path.exists("temp_upload.json"):
                os.remove("temp_upload.json")
        return True

    def make_file_public(self, file_id):
        """Torna um arquivo público e retorna a URL de download direto"""
        if not self.service:
            return None
        
        try:
            # Tornar o arquivo público
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Retornar URL de download direto (sem redirecionamento HTML)
            # IMPORTANTE: drive.usercontent.google.com retorna o arquivo direto,
            # enquanto drive.google.com/uc?export=download retorna uma página HTML
            # que o Instagram não consegue processar como vídeo.
            url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
            print(f"✅ Arquivo tornado público: {url}")
            return url
            
        except Exception as e:
            print(f"❌ Erro ao tornar arquivo público: {e}")
            return None
    
    def make_file_private(self, file_id):
        """Remove permissões públicas de um arquivo"""
        if not self.service:
            return False
        
        try:
            # Listar permissões
            permissions = self.service.permissions().list(fileId=file_id).execute()
            
            # Remover permissões públicas
            for perm in permissions.get('permissions', []):
                if perm.get('type') == 'anyone':
                    self.service.permissions().delete(
                        fileId=file_id,
                        permissionId=perm['id']
                    ).execute()
                    print(f"✅ Permissão pública removida")
                    return True
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao remover permissões públicas: {e}")
            return False
