import json
import os
import time
import requests
from urllib.parse import quote
from config import META_ACCESS_TOKEN, IG_ACCOUNT_ID, FB_PAGE_ID

class IGRateLimitError(Exception):
    """Erro lançado quando o Instagram bloqueia por rate limit (code 4 / subcode 2207051)."""
    pass

class IGActionBlockedError(Exception):
    """Erro lançado quando o Instagram bloqueia uma ação por segurança da comunidade."""
    pass

class MetaAPI:
    def __init__(self, ig_account_id=None, fb_page_id=None, access_token=None):
        self.access_token = access_token or META_ACCESS_TOKEN
        self.ig_account_id = ig_account_id or IG_ACCOUNT_ID
        self.fb_page_id = fb_page_id or FB_PAGE_ID
        self.base_url = "https://graph.facebook.com/v25.0"

    def _get_public_url(self, local_path, gdrive_file_id=None, is_video=False):
        if gdrive_file_id:
            try:
                from gdrive_api import GoogleDriveAPI
                drive = GoogleDriveAPI()
                url = drive.make_file_public(gdrive_file_id, is_video=is_video)
                # Para vídeos usamos URL de download direto (uc?export=download)
                # Para imagens usamos lh3 que é mais rápido
                # Delay maior para vídeos pois o CDN da Meta precisa de mais tempo
                delay = 10 if is_video else 5
                if url:
                    print(f"✅ URL gerada (GDrive): {url} (Aguardando propagação {delay}s...)")
                    time.sleep(delay)
                    return url
            except Exception as e:
                print(f"❌ Erro ao tornar GDrive publico: {e}")

        try:
            with open(local_path, 'rb') as f:
                # User-Agent as vezes ajuda a evitar bloqueios simples
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                res = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f}, headers=headers, timeout=120)
                if res.status_code == 200:
                    r = res.json()
                    if r.get('status') == 'success':
                        url = r['data']['url'].replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                        print(f"✅ URL gerada (tmpfiles): {url}")
                        return url
                    else:
                        print(f"⚠️ Aviso tmpfiles.org: {r.get('message', 'Erro desconhecido')}")
                else:
                    print(f"⚠️ Aviso tmpfiles.org: Status {res.status_code}")
        except Exception as e:
            print(f"⚠️ Erro ao tentar tmpfiles.org: {e}")

        return None

    def _check_status(self, container_id, platform="ig"):
        url = f"{self.base_url}/{container_id}?fields=status_code,status,failure_reason,error_message&access_token={self.access_token}"
        if platform == "fb": url = f"{self.base_url}/{container_id}?fields=status&access_token={self.access_token}"
        # Facebook Reels podem demorar até 10 minutos para processar
        iterations = 60 if platform == "fb" else 30
        
        # Delay inicial: IG Reels precisa de tempo para processar antes de consultar
        initial_delay = 30 if platform == "ig" else 10
        print(f"  ... Aguardando {initial_delay}s antes de verificar status ({platform.upper()})...")
        time.sleep(initial_delay)
        
        for i in range(iterations):
            try:
                res = requests.get(url, timeout=60).json()
                if platform == "ig":
                    status_code = res.get('status_code', 'UNKNOWN')
                    failure_reason = res.get('failure_reason', '')
                    error_msg = res.get('error_message', '')
                    print(f"  ... IG Status [{i+1}/{iterations}]: {status_code}" + (f" | Motivo: {failure_reason}" if failure_reason else "") + (f" | Erro: {error_msg}" if error_msg else ""))
                    if status_code == 'FINISHED': return True
                    if status_code == 'ERROR':
                        print(f"❌ IG Container ERROR: failure_reason={failure_reason} | Resposta: {json.dumps(res, indent=2)}")
                        return False
                    # IN_PROGRESS ou outro status: continuar aguardando
                else:
                    s = res.get('status', {})
                    if isinstance(s, dict):
                        status_val = s.get('video_status')
                        if status_val in ['ready', 'published']: return True
                        if status_val == 'error':
                            print(f"DEBUG FB: Error FB: {json.dumps(res, indent=2)}")
                            return False
                        # Log para outros status (processing, upload_complete, etc)
                        print(f"  ... FB Status [{i+1}/{iterations}]: {status_val}")
                    else:
                        print(f"DEBUG FB: Status format unknown: {res}")
            except Exception as e:
                print(f"  ... Erro ao checar status: {e}")
            time.sleep(10)
        print(f"❌ Timeout ao aguardar status {platform.upper()} para container {container_id}")
        return False

    def _sanitize_caption(self, caption):
        if not caption: return ""
        # Instagram limit: 30 hashtags. Contagem simples por ocorrência de '#'
        import re
        tags = re.findall(r'#\w+', caption)
        if len(tags) > 30:
            print(f"[!] Aviso IG: Legenda com {len(tags)} hashtags. Reduzindo para 30 para cumprir regras da Meta.")
            count = 0
            sanitized = ""
            # Divide a legenda mantendo as hashtags como partes separadas
            parts = re.split(r'(#\w+)', caption)
            for part in parts:
                if part.startswith("#"):
                    count += 1
                    if count <= 30: sanitized += part
                else:
                    sanitized += part
            return sanitized
        return caption

    def _check_ig_error(self, res):
        """Verifica se a resposta da API IG contém erros críticos e lança exceções específicas."""
        error = res.get('error', {})
        if not error:
            return
        code = error.get('code')
        subcode = error.get('error_subcode')
        msg = error.get('message', '')
        user_msg = error.get('error_user_msg', '')
        
        # Rate limit (Application request limit reached)
        if code == 4 or subcode == 2207051:
            print(f"🚨 RATE LIMIT IG DETECTADO! Código {code}/{subcode}: {msg}")
            raise IGRateLimitError(f"IG Rate Limit: {msg}")
        
        # Ação bloqueada por segurança da comunidade
        if subcode in [2207006, 2207025, 2207026, 2207027, 2207028] or 'bloqueada' in user_msg.lower() or 'restricted' in msg.lower():
            print(f"🚨 AÇÃO BLOQUEADA IG! Código {code}/{subcode}: {user_msg or msg}")
            raise IGActionBlockedError(f"IG Action Blocked: {user_msg or msg}")

    def upload_ig_reels_resumable(self, video_path, caption, gdrive_file_id=None, _fallback_attempt=False):
        caption = self._sanitize_caption(caption)
        print(f"Upload IG Reels: {video_path} (fallback={_fallback_attempt})")
        
        # Estratégia de tentativa com Fallback de URL
        # 1. Tentar URL primária (preferencialmente GDrive se fornecido)
        url = self._get_public_url(video_path, gdrive_file_id, is_video=True)
        if not url: return False
        
        res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params={'media_type': 'REELS', 'video_url': url, 'caption': caption, 'access_token': self.access_token}, timeout=120).json()
        
        # Verificar erros críticos ANTES de qualquer retry
        self._check_ig_error(res)
        
        if 'id' not in res:
            # Se falhou na criação do container com link do GDrive E ainda não tentamos tmpfiles
            if gdrive_file_id and not _fallback_attempt:
                print("⚠️ Falha na criação do container com GDrive. Tentando fallback via tmpfiles...")
                url = self._get_public_url(video_path, None, is_video=True)
                if url:
                    res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params={'media_type': 'REELS', 'video_url': url, 'caption': caption, 'access_token': self.access_token}, timeout=120).json()
                    self._check_ig_error(res)
            
            if 'id' not in res:
                print(f"DEBUG FB: Error Container IG Reels: {json.dumps(res, indent=2)}")
                return False
        
        cid = res['id']
        if not self._check_status(cid, "ig"):
            # Se falhou no processamento e tínhamos GDrive E ainda não tentamos fallback
            if gdrive_file_id and not _fallback_attempt:
                print("❌ Erro de processamento Meta com GDrive. Tentando REPROCESSO total via tmpfiles (1 tentativa)...")
                return self.upload_ig_reels_resumable(video_path, caption, None, _fallback_attempt=True)
            print(f"❌ Falha definitiva no processamento IG Reels (fallback={_fallback_attempt}). Desistindo.")
            return False
            
        print("Aguardando propagacao interna Meta (15s)...")
        time.sleep(15)
        pub = requests.post(f"{self.base_url}/{self.ig_account_id}/media_publish", params={'creation_id': cid, 'access_token': self.access_token}, timeout=120).json()
        if 'id' in pub:
            print(f"REEL PUBLICADO NO IG! ID: {pub['id']}")
            return pub['id']
        print(f"DEBUG FB: Error Publish IG Reels: {json.dumps(pub, indent=2)}")
        return False

    def upload_ig_image(self, image_path, caption, gdrive_file_id=None):
        caption = self._sanitize_caption(caption)
        print(f"Upload IG Imagem: {image_path}")
        url = self._get_public_url(image_path, gdrive_file_id, is_video=False)
        if not url: return False
        res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params={'image_url': url, 'caption': caption, 'access_token': self.access_token}, timeout=120).json()
        self._check_ig_error(res)
        if 'id' not in res:
            print(f"DEBUG FB: Error Container IG Imagem: {json.dumps(res, indent=2)}")
            return False
        cid = res['id']
        print("Aguardando propagacao interna Meta (15s)...")
        time.sleep(15)
        pub = requests.post(f"{self.base_url}/{self.ig_account_id}/media_publish", params={'creation_id': cid, 'access_token': self.access_token}, timeout=120).json()
        if 'id' in pub:
            print(f"IMAGEM PUBLICADA NO IG! ID: {pub['id']}")
            return pub['id']
        print(f"DEBUG FB: Error Publish IG Imagem: {json.dumps(pub, indent=2)}")
        return False

    def upload_ig_carousel(self, items, caption):
        caption = self._sanitize_caption(caption)
        print(f"Upload IG Carrossel ({len(items)} itens)")
        child_ids = []
        for item in items:
            url = self._get_public_url(item['local_path'], item.get('gdrive_id'))
            if not url: continue
            payload = {'is_carousel_item': 'true', 'access_token': self.access_token}
            if item['media_type'] == 'VIDEO' or item['local_path'].lower().endswith('.mp4'):
                payload['media_type'] = 'REELS'
                payload['video_url'] = url
            else:
                payload['image_url'] = url
            res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params=payload, timeout=120).json()
            if 'id' in res: child_ids.append(res['id'])
        if not child_ids: return False
        for cid in child_ids: self._check_status(cid, "ig")
        res = requests.post(f"{self.base_url}/{self.ig_account_id}/media", params={'media_type': 'CAROUSEL', 'children': ','.join(child_ids), 'caption': caption, 'access_token': self.access_token}, timeout=120).json()
        if 'id' not in res: return False
        mcid = res['id']
        print("Aguardando propagacao interna Meta (15s)...")
        time.sleep(15)
        pub = requests.post(f"{self.base_url}/{self.ig_account_id}/media_publish", params={'creation_id': mcid, 'access_token': self.access_token}, timeout=120).json()
        if 'id' in pub:
            print(f"CARROSSEL PUBLICADO NO IG! ID: {pub['id']}")
            return pub['id']
        return False

    def upload_fb_reels_resumable(self, video_path, caption):
        print(f"Upload FB Reels: {video_path}")
        fs = os.path.getsize(video_path)
        init = requests.post(f"{self.base_url}/{self.fb_page_id}/video_reels", data={'upload_phase': 'start', 'access_token': self.access_token, 'file_size': fs}, timeout=60).json()
        if 'video_id' not in init:
            print(f"DEBUG FB: Start Phase Failed: {json.dumps(init, indent=2)}")
            return False
        video_id = init['video_id']
        
        with open(video_path, 'rb') as f:
            up_res = requests.post(init['upload_url'], headers={'Authorization': f'OAuth {self.access_token}', 'offset': '0', 'file_size': str(fs)}, data=f.read(), timeout=300)
            if up_res.status_code not in [200, 201]:
                print(f"DEBUG FB: Upload Phase Failed (Status {up_res.status_code}): {up_res.text}")
                return False
        
        # O processamento só começa DEPOIS do finish no modo resumable do FB
        finish = requests.post(f"{self.base_url}/{self.fb_page_id}/video_reels", data={'access_token': self.access_token, 'video_id': video_id, 'upload_phase': 'finish', 'video_state': 'PUBLISHED', 'description': caption}, timeout=120).json()
        
        if not finish.get('success'):
            print(f"DEBUG FB: Finish Phase Failed: {json.dumps(finish, indent=2)}")
            return False

        print(f"Aguardando processamento FB Reels (video_id: {video_id})...")
        if not self._check_status(video_id, "fb"):
            print(f"DEBUG FB: Timeout or Error waiting for video_id {video_id} to be published.")
            # Nota: Mesmo com timeout no status check, o post pode acabar sendo publicado depois
            return False
        
        print(f"REEL PUBLICADO NO FB! ID: {video_id}")
        return video_id

    def upload_fb_image(self, image_path, caption):
        print(f"Upload FB Imagem: {image_path}")
        with open(image_path, 'rb') as f:
            res = requests.post(f"{self.base_url}/{self.fb_page_id}/photos", data={'access_token': self.access_token, 'message': caption}, files={'source': f}, timeout=120).json()
        if 'id' in res:
            print(f"IMAGEM PUBLICADA NO FB! ID: {res['id']}")
            return res['id']
        return False

    def upload_fb_carousel(self, items, caption):
        print(f"Upload FB Carrossel ({len(items)} imagens)")
        attached = []
        for item in items:
            if item['local_path'].lower().endswith('.mp4'): continue
            with open(item['local_path'], 'rb') as f:
                res = requests.post(f"{self.base_url}/{self.fb_page_id}/photos", data={'access_token': self.access_token, 'published': 'false'}, files={'source': f}, timeout=120).json()
                if 'id' in res: attached.append({'media_fbid': res['id']})
        if not attached: return False
        res = requests.post(f"{self.base_url}/{self.fb_page_id}/feed", data={'access_token': self.access_token, 'attached_media': json.dumps(attached), 'message': caption}, timeout=120).json()
        if 'id' in res:
            print(f"CARROSSEL PUBLICADO NO FB! ID: {res['id']}")
            return res['id']
        return False

    def get_account_details(self, access_token):
        try:
            res = requests.get(f"{self.base_url}/me/accounts?fields=name,access_token,instagram_business_account{{id,username}}&access_token={access_token}", timeout=60).json()
            results = []
            if 'data' in res:
                for p in res['data']:
                    item = {"name": p.get("name"), "fb_page_id": p.get("id"), "access_token": p.get("access_token"), "ig_account_id": None, "ig_username": None}
                    ig = p.get("instagram_business_account")
                    if ig:
                        item["ig_account_id"] = ig.get("id")
                        item["ig_username"] = ig.get("username")
                    results.append(item)
            return results
        except: return []

    def refresh_token(self, old_token):
        params = {"grant_type": "fb_exchange_token", "client_id": "1283566600658374", "client_secret": "bf2533e5778d3036b43a61c6f1f9c192", "fb_exchange_token": old_token}
        try:
            r = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params=params, timeout=60).json()
            return r.get("access_token", old_token), r.get("expires_in")
        except: return old_token, None

