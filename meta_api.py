import json
import os
import time
import requests
from urllib.parse import quote
from config import META_ACCESS_TOKEN, IG_ACCOUNT_ID, FB_PAGE_ID

class MetaAPI:
    def __init__(self, ig_account_id=None, fb_page_id=None, access_token=None):
        self.access_token = access_token or META_ACCESS_TOKEN
        self.ig_account_id = ig_account_id or IG_ACCOUNT_ID
        self.fb_page_id = fb_page_id or FB_PAGE_ID
        self.base_url = "https://graph.facebook.com/v25.0"
    def _get_public_url(self, item_id, platform="ig"):
                    if platform == "ig":
                                    return f"https://www.instagram.com/reels/{item_id}/"
                    else:
                                    return f"https://www.facebook.com/{self.fb_page_id}/videos/{item_id}/"
                            
    def _check_status(self, container_id, platform="ig"):
        """Verifica se o video terminou de ser processado pela Meta"""
        if platform == "ig":
            url = f"{self.base_url}/{container_id}?fields=status_code&access_token={self.access_token}"
        else:
            url = f"{self.base_url}/{container_id}?fields=status&access_token={self.access_token}"
            
        for _ in range(10):  # Tenta até 10 vezes (esperando até 1 minuto)
            response = requests.get(url).json()
            if platform == "ig":
                status = response.get('status_code')
                if status == 'FINISHED':
                    return True
                elif status == 'ERROR':
                    print(f"Erro no processamento do IG: {response}")
                    return False
            else:
                # https://developers.facebook.com/docs/video-api/guides/reels-publishing#processing-phase
                url_fb = f"{self.base_url}/{container_id}?fields=status&access_token={self.access_token}"
                fb_res = requests.get(url_fb).json()
                v_status = fb_res.get('status', {})
                if isinstance(v_status, dict):
                    st = v_status.get('video_status')
                    if st == 'ready': return True
                    if st == 'error': 
                        print(f"Erro no processamento do Facebook: {fb_res}")
                        return False
                elif v_status == 'ready':
                    return True
                
                print(f"Aguardando processamento Facebook... ({v_status})")
                
            time.sleep(10)
        return False
    def upload_ig_reels_resumable(self, video_path, caption, gdrive_file_id=None):
        """
        Upload para Instagram Reels - estratégia híbrida:
        - <= 90MB: video_url via Google Drive ou tmpfiles.org (rápido)
        - >  90MB: resumable upload nativo (upload_type=resumable, suporta caption)
        """
        if not self.ig_account_id:
            print("[ERROR] IG_ACCOUNT_ID não configurado.")
            return False

        print(f"\n{'='*60}")
        print(f"INICIANDO UPLOAD PARA INSTAGRAM")
        print(f"{'='*60}")
        print(f"VIDEO: {video_path}")
        
        if caption:
            caption = caption.strip()
            # REGRA DE OURO DO INSTAGRAM: Máximo 30 hashtags.
            # Se houver 31 hashtags, a API PUBLICA O VÍDEO E APAGA A LEGENDA SILENCIOSAMENTE!
            import re
            hashtags = re.findall(r'#\w+', caption)
            if len(hashtags) > 30:
                print(f"⚠️  ALERTA CRÍTICO: Detectado {len(hashtags)} hashtags. Instagram suporta NO MÁXIMO 30!")
                print("⚠️  Cortando hashtags excedentes para evitar a perda total da legenda...")
                
                parts = re.split(r'(#\w+)', caption)
                new_caption = ""
                tags_found = 0
                for part in parts:
                    if part.startswith('#'):
                        tags_found += 1
                        if tags_found <= 30:
                            new_caption += part
                    else:
                        new_caption += part
                # Limpa espaços duplos
                caption = re.sub(r' +', ' ', new_caption).strip()

            print(f"📝 Caption: '{caption[:50]}...'")
            print(f"📏 Tamanho: {len(caption)} caracteres")
            if len(caption) > 2200:
                caption = caption[:2200]
        else:
            print(f"📝 Nenhuma caption fornecida")
        
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            print("[ERROR] O arquivo de video esta vazio (0 bytes).")
            return False
        
        file_size_mb = file_size / (1024*1024)
        print(f"📦 Tamanho do arquivo: {file_size_mb:.2f} MB")
        
        if file_size_mb > 90:
            print(f"\n🔄 Arquivo grande ({file_size_mb:.2f} MB) - Comprimindo com ffmpeg...")
            compressed = self._compress_video(video_path)
            if compressed:
                print(f"✅ Vídeo comprimido: {compressed}")
                # IMPORTANTE: gdrive_file_id=None força upload do arquivo comprimido LOCAL
                # (não a URL do arquivo original grande no Google Drive)
                result = self._upload_ig_via_url(compressed, caption, None, os.path.getsize(compressed)/(1024*1024))
                try:
                    os.remove(compressed)
                except:
                    pass
                return result
            else:
                print(f"⚠️  Compressão falhou, tentando mesmo assim...")
        
        return self._upload_ig_via_url(video_path, caption, gdrive_file_id, file_size_mb)

    def _compress_video(self, video_path):
        """
        Comprime o vídeo usando ffmpeg para caber no limite de 100MB do Instagram.
        Retorna o caminho do arquivo comprimido ou None se falhar.
        """
        import subprocess
        import shutil
        
        if not shutil.which('ffmpeg'):
            print(f"   ffmpeg não encontrado no sistema")
            return None
        
        compressed_path = video_path.replace('.mp4', '_compressed.mp4')
        if compressed_path == video_path:
            compressed_path = video_path + '_compressed.mp4'
        
        try:
            # Comprimir para ~85MB: Reduzir escala apenas se for > 720p
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-vf', "scale='if(gt(ih,720),-2,iw)':'if(gt(ih,720),720,ih)'",
                '-c:v', 'libx264', '-crf', '28', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                compressed_path
            ]
            
            print(f"   Executando ffmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(compressed_path):
                compressed_mb = os.path.getsize(compressed_path) / (1024*1024)
                print(f"   ✅ Comprimido para {compressed_mb:.2f} MB")
                if compressed_mb > 95:
                    print(f"   ⚠️  Ainda muito grande ({compressed_mb:.2f} MB), tentando CRF 32...")
                    compressed_path2 = compressed_path.replace('_compressed.mp4', '_compressed2.mp4')
                    cmd2 = [
                        'ffmpeg', '-y', '-i', compressed_path,
                        '-c:v', 'libx264', '-crf', '32', '-preset', 'fast',
                        '-c:a', 'aac', '-b:a', '96k',
                        compressed_path2
                    ]
                    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
                    if result2.returncode == 0 and os.path.exists(compressed_path2):
                        os.remove(compressed_path)
                        return compressed_path2
                return compressed_path
            else:
                print(f"   ❌ ffmpeg erro: {result.stderr[-200:]}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ ffmpeg timeout (>5 min)")
            return None
        except Exception as e:
            print(f"   ❌ ffmpeg exceção: {e}")
            return None

    def _upload_ig_via_url(self, video_path, caption, gdrive_file_id, file_size_mb):
        """
        Upload via video_url.
        Prioriza tmpfiles.org/file.io (mais estáveis para o Instagram) e usa GDrive como fallback.
        """
        video_url = None
        
        # 1. Tentar upload para servidor temporário (MAIS PRIORITÁRIO - Testado e funciona 100%)
        print(f"\n[STEP 1] Fazendo upload temporário para servidor público...")
        
        # Tentar tmpfiles.org primeiro (é o mais estável para arquivos grandes e pequenos)
        try:
            print(f"   Tentando tmpfiles.org...")
            with open(video_path, 'rb') as f:
                r = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f}, timeout=120)
            d = r.json()
            if d.get('status') == 'success':
                video_url = d['data']['url'].replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                print(f"   ✅ tmpfiles.org: OK")
            else:
                print(f"   ⚠️  tmpfiles.org falhou")
        except Exception as e:
            print(f"   ⚠️  tmpfiles.org erro: {e}")

        # Fallback 1: file.io
        if not video_url:
            try:
                print(f"   Tentando file.io...")
                with open(video_path, 'rb') as f:
                    r = requests.post('https://file.io', files={'file': f}, data={'expires': '1d'}, timeout=120)
                d = r.json()
                if d.get('success'):
                    video_url = d['link']
                    print(f"   ✅ file.io: OK")
                else:
                    print(f"   ⚠️  file.io falhou")
            except Exception as e:
                print(f"   ⚠️  file.io erro: {e}")
        
        # Fallback 2: Google Drive (Somente se os outros falharem)
        if not video_url and gdrive_file_id:
            print(f"\n[STEP 1 (Fallback)] Tentando Google Drive como servidor público...")
            try:
                from gdrive_api import GoogleDriveAPI
                drive = GoogleDriveAPI()
                if drive.service:
                    video_url = drive.make_file_public(gdrive_file_id)
                    if video_url:
                        print(f"✅ Google Drive: URL pública criada")
                    else:
                        print(f"⚠️  Google Drive falhou")
            except Exception as e:
                print(f"⚠️  Google Drive erro: {e}")
        
        if not video_url:
            print(f"[ERROR] Todos os serviços de upload temporário falharam")
            return False
        
        print(f"✅ URL para Instagram: {video_url}")
        
        # Criar container COM video_url e caption
        print(f"\n[STEP 2] Criando container no Instagram...")
        # NOTA: O teste "vídeo das árvores" que deu 100% certo (commit 3b37108) 
        # usou EXATAMENTE requests.post(url, params=payload) SEM mexer no encoding padrão.
        
        url_media = f"{self.base_url}/{self.ig_account_id}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'access_token': self.access_token
        }
        
        if caption:
            payload['caption'] = caption
            print(f"📝 Caption incluída no container (Modo Teste de Sucesso)")
        
        res = requests.post(url_media, params=payload).json()
        
        if 'id' not in res:
            print(f"[ERROR] Erro ao criar container: {res}")
            return False
        
        container_id = res['id']
        print(f"✅ Container criado: {container_id}")
        
        print(f"\n[STEP 3] Aguardando processamento...")
        if not self._check_status(container_id, "ig"):
            print(f"[ERROR] Falha no processamento")
            return False
        
        print(f"✅ Processamento concluído")
        
        # Pequeno aguardo antes de publicar para garantir propagação
        time.sleep(5)
        
        pub_res = requests.post(
            f"{self.base_url}/{self.ig_account_id}/media_publish",
            params={'creation_id': container_id, 'access_token': self.access_token}
        ).json()
        
        if 'id' not in pub_res:
            print(f"[ERROR] Erro ao publicar: {pub_res}")
            return False
        
        media_id = pub_res['id']
        print(f"\n{'='*60}")
        print(f"✅ REEL PUBLICADO NO INSTAGRAM!")
        print(f"{'='*60}")
        print(f"Media ID: {media_id}")
        
        time.sleep(3)
        verify_res = requests.get(
            f"{self.base_url}/{media_id}",
            params={'fields': 'caption,permalink', 'access_token': self.access_token}
        ).json()
        
        if 'caption' in verify_res and verify_res['caption']:
            print(f"✅ Caption verificada: '{verify_res['caption'][:80]}'")
        else:
            print(f"⚠️  Caption não confirmada via API logo após publicação")
        
        if 'permalink' in verify_res:
            print(f"🔗 Link: {verify_res['permalink']}")
        
        return True

    def upload_fb_reels_resumable(self, video_path, caption):
        """Faz o upload de um vídeo para o Facebook Page Reels
        
        IMPORTANTE: A API do Facebook NÃO suporta agendamento nativo para Reels.
        O agendamento deve ser feito no lado do servidor (GitHub Actions).
        """
        if not self.fb_page_id:
            print("FB_PAGE_ID não configurado.")
            return False
            
        print(f"Iniciando envio para Facebook Page: {video_path}")
        file_size = os.path.getsize(video_path)
        
        # 1. Initialize session
        init_url = f"{self.base_url}/{self.fb_page_id}/video_reels"
        init_payload = {
            'upload_phase': 'start',
            'access_token': self.access_token,
            'file_size': file_size
        }
        init_res = requests.post(init_url, data=init_payload).json()
        
        if 'video_id' not in init_res:
            error_data = init_res.get('error', init_res)
            print(f"[ERROR] Erro ao iniciar sessão FB: {error_data}")
            return False
            
        video_id = init_res['video_id']
        upload_url = init_res['upload_url']
        
        # 2. Enviar arquivo
        headers = {
            'Authorization': f'OAuth {self.access_token}',
            'offset': '0',
            'file_size': str(file_size)
        }
        
        with open(video_path, 'rb') as f:
            video_data = f.read()
            
        # upload_url already has the endpoint, we just post to it
        upload_res = requests.post(upload_url, headers=headers, data=video_data)
        
        # 3. Check status
        print("Arquivo enviado (FB). Aguardando processamento da Meta...")
        if not self._check_status(video_id, "fb"):
             print("Aviso: O vídeo ainda não está 'ready' no Facebook, mas tentaremos publicar assim mesmo.")
             
        # 4. Concluir e Publicar (sempre PUBLISHED, sem agendamento)
        finish_url = f"{self.base_url}/{self.fb_page_id}/video_reels"
        finish_payload = {
            'access_token': self.access_token,
            'video_id': video_id,
            'upload_phase': 'finish',
            'video_state': 'PUBLISHED',
            'description': caption,
            'share_to_feed': True
        }
            
        finish_res = requests.post(finish_url, data=finish_payload).json()
        
        if finish_res.get('success'):
            print(f"[SUCESSO] Reel publicado com sucesso na Pagina do FB!")
            return True
        else:
            error_data = finish_res.get('error', finish_res)
            print(f"[ERROR] Erro ao publicar no FB (Step 4): {error_data}")
            return False


    def _enforce_caption_limit(self, caption):
        if not caption: return caption
        caption = caption.strip()
        import re
        hashtags = re.findall(r'#\w+', caption)
        if len(hashtags) > 30:
            print(f"⚠️  Cortando hashtags excedentes (max 30 permitidas)...")
            parts = re.split(r'(#\w+)', caption)
            new_caption = ""
            tags_found = 0
            for part in parts:
                if part.startswith('#'):
                    tags_found += 1
                    if tags_found <= 30: new_caption += part
                else:
                    new_caption += part
            caption = re.sub(r' +', ' ', new_caption).strip()
        return caption[:2200]

    def upload_ig_image(self, image_path, caption, gdrive_file_id=None):
        if not self.ig_account_id: return False
        print(f"\nIniciando upload IMAGEM IG: {image_path}")
        caption = self._enforce_caption_limit(caption)
        
        img_url = self._get_public_url(image_path, gdrive_file_id)
        if not img_url: return False
        
        print("Criando container IG...")
        url_media = f"{self.base_url}/{self.ig_account_id}/media"
        payload = {'image_url': img_url, 'access_token': self.access_token}
        if caption: payload['caption'] = caption
        res = requests.post(url_media, params=payload).json()
        
        if 'id' not in res: return False
        cid = res['id']
        
        print("Aguardando processamento IG...")
        if not self._check_status(cid, "ig"): return False
        
        print("Publicando...")
        pub = requests.post(f"{self.base_url}/{self.ig_account_id}/media_publish", params={'creation_id': cid, 'access_token': self.access_token}).json()
        if 'id' in pub:
            print(f"✅ IMAGEM PUBLICADA NO IG! ID: {pub['id']}")
            return True
        return False

    def upload_ig_carousel(self, file_paths, caption):
        if not self.ig_account_id: return False
        print(f"\nIniciando upload CARROSSEL IG ({len(file_paths)} itens)")
        caption = self._enforce_caption_limit(caption)
        
        child_ids = []
        for path in file_paths:
            print(f"-> Processando item: {os.path.basename(path)}")
            url = self._get_public_url(path)
            if not url: return False
            
            payload = {'is_carousel_item': 'true', 'access_token': self.access_token}
            if path.lower().endswith('.mp4'):
                payload['media_type'] = 'REELS'
                payload['video_url'] = url
            else:
                payload['image_url'] = url
                
            res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params=payload).json()
            if 'id' in res: child_ids.append(res['id'])
        
        if not child_ids: return False
        
        print("Aguardando processamento dos itens do carrossel...")
        for cid in child_ids:
            self._check_status(cid, "ig")
            
        print("Criando container MESTRE CARROSSEL...")
        payload = {
            'media_type': 'CAROUSEL',
            'children': ','.join(child_ids),
            'access_token': self.access_token
        }
        if caption: payload['caption'] = caption
        master = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params=payload).json()
        if 'id' not in master: return False
        mcid = master['id']
        
        if not self._check_status(mcid, "ig"): return False
        
        print("Publicando Carrossel...")
        pub = requests.post(f"{self.base_url}/{self.ig_account_id}/media_publish", params={'creation_id': mcid, 'access_token': self.access_token}).json()
        if 'id' in pub:
            print(f"✅ CARROSSEL PUBLICADO NO IG! ID: {pub['id']}")
            return True
        return False

    def upload_fb_image(self, image_path, caption):
        if not self.fb_page_id: return False
        print(f"\nIniciando upload IMAGEM FB: {image_path}")
        
        url_fb = f"{self.base_url}/{self.fb_page_id}/photos"
        payload = {'access_token': self.access_token}
        if caption: payload['message'] = caption
        
        with open(image_path, 'rb') as f:
            res = requests.post(url_fb, data=payload, files={'source': f}).json()
            
        if 'id' in res:
            print(f"✅ IMAGEM PUBLICADA NO FB! ID: {res['id']}")
            return True
        return False
        
    def upload_fb_carousel(self, file_paths, caption):
        if not self.fb_page_id: return False
        print(f"\nIniciando upload CARROSSEL FB (Múltiplas Fotos)")
        
        attached_media = []
        for path in file_paths:
            if path.lower().endswith('.mp4'): continue # FB Nao aceita video misturado fácil no feed de fotos, vamos focar em imagens
            url_fb = f"{self.base_url}/{self.fb_page_id}/photos"
            payload = {'access_token': self.access_token, 'published': 'false'}
            with open(path, 'rb') as f:
                res = requests.post(url_fb, data=payload, files={'source': f}).json()
                if 'id' in res: attached_media.append({'media_fbid': res['id']})
                
        if not attached_media: return False
        
        url_feed = f"{self.base_url}/{self.fb_page_id}/feed"
        payload = {'access_token': self.access_token, 'attached_media': json.dumps(attached_media)}
        if caption: payload['message'] = caption
        
        pub = requests.post(url_feed, data=payload).json()
        if 'id' in pub:
            print(f"✅ CARROSSEL PUBLICADO NO FB! ID: {pub['id']}")
            return True
        return False

    def get_account_details(self, access_token):
        """Busca detalhes de todas as páginas e contas IG vinculadas ao token"""
        try:
            # 1. Info das Páginas e IGs vinculados
            pages_url = f"{self.base_url}/me/accounts?fields=name,access_token,instagram_business_account{{id,username,profile_picture_url}}&access_token={access_token}"
            pages_res = requests.get(pages_url).json()
            
            results = []
            if 'data' in pages_res:
                for page in pages_res['data']:
                    item = {
                        "name": page.get("name"),
                        "fb_page_id": page.get("id"),
                        "access_token": page.get("access_token"), # Token de Página (geralmente eterno se gerado de long-lived)
                        "ig_account_id": None,
                        "ig_username": None,
                        "profile_pic": None
                    }
                    
                    ig = page.get("instagram_business_account")
                    if ig:
                        item["ig_account_id"] = ig.get("id")
                        item["ig_username"] = ig.get("username")
                        item["profile_pic"] = ig.get("profile_picture_url")
                    
                    results.append(item)
            return results
        except Exception as e:
            print(f"Erro ao buscar detalhes da conta: {e}")
            return []

    def refresh_token(self, old_token):
        """Tenta renovar um token (se for de usuário) ou apenas retorna o mesmo se for de página"""
        # APP_ID e APP_SECRET fixos
        APP_ID = "1283566600658374"
        APP_SECRET = "bf2533e5778d3036b43a61c6f1f9c192"
        
        url = f"https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": old_token
        }
        try:
            r = requests.get(url, params=params).json()
            if "access_token" in r:
                return r["access_token"], r.get("expires_in")
            return old_token, None
        except:
            return old_token, None
