import os
import io
import time
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from config import GDRIVE_FOLDER_ID

class GoogleDriveAPI:
    def __init__(self, credentials_path='credentials.json'):
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.folder_id = GDRIVE_FOLDER_ID
        
        gdrive_b64 = os.getenv('GDRIVE_JSON_B64')
        if gdrive_b64:
            import base64
            try:
                decoded = base64.b64decode(gdrive_b64.strip()).decode('utf-8')
                creds_dict = json.loads(decoded)
                if 'private_key' in creds_dict:
                    pk = creds_dict['private_key']
                    if "\\n" in pk:
                        creds_dict['private_key'] = pk.replace("\\n", "\n")
                self.creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=self.scopes)
                print("Credenciais do Google Drive carregadas via Base64.")
            except Exception as e:
                print(f"Erro ao decodificar GDRIVE_JSON_B64: {e}")
                self.service = None
                return
        elif os.path.exists(credentials_path):
            self.creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=self.scopes)
        else:
            print(f"Aviso: Nem variavel GDRIVE_JSON_B64 nem arquivo {credentials_path} foram encontrados!")
            self.service = None
            return

        self.service = build('drive', 'v3', credentials=self.creds)

    def list_mp4_files(self, folder_id=None):
        f_id = folder_id or self.folder_id
        if not self.service or not f_id: return []
        query = f"'{f_id}' in parents and mimeType='video/mp4' and trashed=false"
        all_items = []
        page_token = None
        try:
            while True:
                results = self.service.files().list(
                    q=query, pageSize=100, pageToken=page_token,
                    fields="nextPageToken, files(id, name, parents)",
                    supportsAllDrives=True, includeItemsFromAllDrives=True
                ).execute()
                all_items.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token: break
            return all_items
        except Exception as e:
            print(f"Erro ao listar arquivos do Drive: {e}")
            return all_items

    def list_media_recursive(self, folder_id=None):
        """Lista vídeos, imagens e zips recursivamente dentro de uma pasta do Drive."""
        f_id = folder_id or self.folder_id
        if not self.service or not f_id: return []
        
        # Filtro para vídeos, imagens e zips
        mime_types = [
            "video/mp4", "video/quicktime", "video/x-msvideo", 
            "image/jpeg", "image/png", "application/zip", "application/x-zip-compressed"
        ]
        mime_query = " or ".join([f"mimeType='{t}'" for t in mime_types])
        
        # Busca recursiva: não usamos 'in parents', mas sim uma busca que encontra tudo
        # onde a pasta raiz está na árvore de ancestrais. No entanto, a API v3 não suporta 
        # 'descendant of' diretamente de forma simples sem varrer pastas.
        # Estratégia: Listar todos os arquivos compatíveis que não estão na lixeira e 
        # depois filtrar os que pertencem à árvore da pasta raiz (ou apenas listar tudo se for a raiz).
        
        query = f"({mime_query}) and trashed=false"
        
        all_items = []
        page_token = None
        
        # Cache de nomes de pastas para evitar múltiplas chamadas
        folder_names = {}

        def get_folder_name(fid):
            if fid in folder_names: return folder_names[fid]
            try:
                res = self.service.files().get(fileId=fid, fields="name").execute()
                name = res.get("name")
                folder_names[fid] = name
                return name
            except:
                return "Desconhecida"

        try:
            while True:
                results = self.service.files().list(
                    q=query, pageSize=100, pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType, parents)",
                    supportsAllDrives=True, includeItemsFromAllDrives=True
                ).execute()
                
                files = results.get('files', [])
                for f in files:
                    # Se especificamos uma pasta, verificamos se o arquivo está nela (ou subpastas)
                    # Para simplificar e performar melhor, se for a pasta raiz do bot, pegamos tudo.
                    # Se for uma pasta específica de conta, filtramos.
                    if folder_id:
                        # Verificação simples de parentesco imediato ou recursivo (opcional)
                        # Por enquanto, se o usuário pediu uma pasta, vamos assumir que ele quer os arquivos dela.
                        # Mas para ser verdadeiramente recursivo, teríamos que checar toda a árvore.
                        # Para o Reels Bot, geralmente as contas têm pastas separadas.
                        parents = f.get('parents', [])
                        if folder_id in parents:
                            # Adiciona nome da pasta pai para organização
                            f['folder'] = get_folder_name(folder_id)
                            all_items.append(f)
                        else:
                            # Busca profunda: se parent não é o folder_id, checamos se o parent está dentro do folder_id
                            # Isso exige mapear a árvore. Para o MVP, vamos pegar os que estão na pasta e um nível abaixo.
                            for p in parents:
                                f['folder'] = get_folder_name(p)
                                all_items.append(f)
                                break
                    else:
                        # Pasta raiz: pega tudo
                        parents = f.get('parents', [])
                        if parents:
                            f['folder'] = get_folder_name(parents[0])
                        all_items.append(f)

                page_token = results.get('nextPageToken')
                if not page_token: break
                
            return all_items
        except Exception as e:
            print(f"Erro na busca recursiva do Drive: {e}")
            return all_items

    def download_file(self, file_id, file_path):
        """Baixa um arquivo do Drive para o caminho especificado.
        
        Args:
            file_id: ID do arquivo no Google Drive
            file_path: Caminho completo de destino (ex: '.tmp/video.mp4')
        """
        if not self.service or not file_id:
            return None
        # Garante que o diretório de destino existe
        dest_dir = os.path.dirname(file_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        print(f"Baixando {file_name}...")
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            print(f"Download concluido: {file_path}")
            return file_path
        except Exception as e:
            print(f"Erro ao baixar {file_name}: {e}")
            return None

    def delete_file(self, file_id):
        if not self.service: return
        try:
            self.service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            print("Arquivo apagado do Drive permanentemente.")
        except Exception as e:
            print(f"Tentando mover para lixeira: {e}")
            try:
                self.service.files().update(fileId=file_id, body={'trashed': True}, supportsAllDrives=True).execute()
                print("Arquivo movido para a lixeira.")
            except Exception as e2:
                print(f"Erro ao remover arquivo: {e2}")

    def upload_file(self, file_path, name, mimetype='video/mp4', folder_id=None):
        f_id = folder_id or self.folder_id
        if not self.service or not f_id: return None
        file_metadata = {'name': name, 'parents': [f_id]}
        media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            return file.get('id')
        except Exception as e:
            print(f"Erro ao fazer upload: {e}")
            return None

    def search_file_by_name(self, name, folder_id=None):
        f_id = folder_id or self.folder_id
        if not self.service or not f_id: return None
        query = f"'{f_id}' in parents and name='{name}' and trashed=false"
        try:
            results = self.service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            items = results.get('files', [])
            return items[0]['id'] if items else None
        except: return None

    def get_json(self, name, folder_id=None):
        file_id = self.search_file_by_name(name, folder_id)
        if not file_id: return None
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return json.loads(fh.getvalue().decode('utf-8'))
        except Exception as e:
            print(f"Erro ao ler JSON: {e}")
            return None

    def save_json(self, name, data, folder_id=None):
        f_id = folder_id or self.folder_id
        content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        fh = io.BytesIO(content)
        media = MediaIoBaseUpload(fh, mimetype='application/json', resumable=False)
        file_id = self.search_file_by_name(name, f_id)
        try:
            if file_id:
                self.service.files().update(fileId=str(file_id), body={'name': name}, media_body=media, supportsAllDrives=True).execute()
            else:
                self.service.files().create(body={'name': name, 'parents': [f_id]}, media_body=media, supportsAllDrives=True).execute()
            return True
        except Exception as e:
            msg = str(e)
            if hasattr(e, 'content'):
                content = e.content.decode('utf-8')
                msg += " | Body: " + content
                if 'storageQuotaExceeded' in content:
                    print(f"❌ ERRO DE COTA: A Conta de Serviço não tem espaço. Crie o arquivo '{name}' manualmente no Drive e compartilhe-o.")
            print(f"Erro ao salvar JSON no Drive: {msg}")
            return False

    def make_file_public(self, file_id):
        if not self.service: return None
        try:
            self.service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}, supportsAllDrives=True).execute()
            # Formato lh3 é um link direto que o Instagram aceita bem para imagens
            url = f"https://lh3.googleusercontent.com/d/{file_id}"
            print(f"Arquivo tornado publico: {url}")
            return url
        except Exception as e:
            print(f"Erro ao tornar arquivo publico: {e}")
            return None

    def list_files_in_folder(self, folder_id, mime_filter=None):
        if not self.service: return []
        query = f"'{folder_id}' in parents and trashed=false"
        if mime_filter: query += f" and ({mime_filter})"
        try:
            results = self.service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True, fields="files(id, name, mimeType)").execute()
            return results.get('files', [])
        except Exception as e:
            print(f"Erro ao listar arquivos na pasta {folder_id}: {e}")
            return None

    def cleanup_storage(self, days=7):
        if not self.service: return False
        import datetime
        limit_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = f"trashed = false and modifiedTime < '{limit_date}'"
        if self.folder_id: query = f"'{self.folder_id}' in parents and " + query
        try:
            results = self.service.files().list(q=query, fields="files(id, name, size)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            files = results.get('files', [])
            if not files: return True
            print(f"Limpando {len(files)} arquivos antigos do Drive...")
            for f in files:
                try:
                    if f['name'] in ['schedule_queue.json', 'posted_history.json', 'accounts.json']: continue
                    self.service.files().delete(fileId=f['id'], supportsAllDrives=True).execute()
                except: pass
            return True
        except: return False
