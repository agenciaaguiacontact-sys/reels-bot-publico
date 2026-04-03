import os
import sys
import json
import time
import zipfile
import traceback
from datetime import datetime
import pytz

# Garante que o diretorio raiz esteja no path, mesmo se executado de dentro de 'execution/'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Forçar output em UTF-8 para evitar erros de encoding no Windows (CP1252)
if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

from gdrive_api import GoogleDriveAPI
from meta_api import MetaAPI

def process_job(job, drive, global_accounts, tz_br):
    file_id = job.get('gdrive_id')
    filename = job.get('filename', 'arquivo_desconhecido')
    media_type = job.get('media_type', 'VIDEO')
    
    # Auto-detecção de tipo de mídia por extensão (Safety net para Cloud)
    ext = filename.lower().split('.')[-1]
    
    # Detecção de Carrossel por ZIP
    if ext == 'zip' and media_type == 'VIDEO':
        print(f"[!] Aviso: Arquivo {filename} é ZIP. Tratando como CAROUSEL.")
        media_type = 'CAROUSEL'
        
    if ext in ['png', 'jpg', 'jpeg', 'webp'] and media_type in ['VIDEO', 'REELS']:
        print(f"[!] Aviso: Arquivo {filename} é imagem mas estava como {media_type}. Ajustando para IMAGE.")
        media_type = 'IMAGE'
    elif ext in ['mp4', 'mov', 'avi', 'mkv'] and media_type == 'IMAGE':
        print(f"[!] Aviso: Arquivo {filename} é vídeo mas estava como IMAGE. Ajustando para VIDEO.")
        media_type = 'VIDEO'

    caption = job.get('caption', '')
    job_accounts = job.get('accounts', global_accounts)
    
    result = {
        "job": job,
        "success_accounts": [],
        "failed_accounts": [],
        "any_success": False,
        "total_posts": 0
    }

    local_path = None
    carousel_items = []
    
    try:
        # Preparacao - Download para .tmp/
        os.makedirs('.tmp', exist_ok=True)
        
        if media_type == 'CAROUSEL':
            # Suporte ao formato de teste (_carousel_items_gdrive) ou pastas dinâmicas
            test_items = job.get('_carousel_items_gdrive')
            if test_items:
                print(f"[*] Baixando {len(test_items)} itens do carrossel (formato extra)...")
                for item in test_items:
                    item_id = item.get('id') or item.get('gdrive_id')
                    local_path = item.get('path') or item.get('_local_path_override')
                    
                    # Pular se não tiver ID nem arquivo local válido
                    if not item_id and not (local_path and os.path.exists(local_path)):
                        continue
                    
                    p = None
                    if item_id:
                        tmp_name = item.get('name') or item.get('filename') or f"item_{item_id}"
                        p = drive.download_file(item_id, os.path.join('.tmp', tmp_name))
                    elif local_path:
                        p = local_path
                        print(f"[*] Usando arquivo local para carrossel: {p}")
                    
                    if p:
                        m_type = item.get('type') or item.get('media_type') or 'IMAGE'
                        carousel_items.append({
                            'local_path': p, 
                            'gdrive_id': item_id, 
                            'media_type': 'IMAGE' if 'IMAGE' in m_type.upper() else 'VIDEO'
                        })
            
            if not file_id and not carousel_items:
                folder_id = job.get('folder_id')
                if folder_id:
                    files = drive.list_files_in_folder(folder_id)
                    if files:
                        for f in files:
                            p = drive.download_file(f['id'], os.path.join('.tmp', f['name']))
                            if p: carousel_items.append({'local_path': p, 'gdrive_id': f['id'], 'media_type': 'IMAGE' if 'image' in f['mimeType'] else 'VIDEO'})
            else:
                tmp_path = os.path.join('.tmp', filename)
                local_path = drive.download_file(file_id, tmp_path)
                if local_path and local_path.lower().endswith('.zip'):
                    tmp_dir = os.path.join('.tmp', f"carousel_{int(time.time())}")
                    os.makedirs(tmp_dir, exist_ok=True)
                    with zipfile.ZipFile(local_path, 'r') as zf: zf.extractall(tmp_dir)
                    for f in os.listdir(tmp_dir):
                        p = os.path.join(tmp_dir, f)
                        carousel_items.append({'local_path': p, 'media_type': 'IMAGE' if f.lower().endswith(('.png','.jpg','.jpeg')) else 'VIDEO'})
                elif local_path:
                    carousel_items.append({'local_path': local_path, 'gdrive_id': file_id, 'media_type': media_type})
        else:
            tmp_path = os.path.join('.tmp', filename)
            local_path = drive.download_file(file_id, tmp_path)
        
        if not local_path and not carousel_items:
            print(f"[ERR] Erro ao baixar {filename}.")
            return result

        for acc in job_accounts:
            acc_name = acc.get('name', 'Conta s/ nome')
            print(f">>> Postando em {acc_name} ({media_type})...")
            acc_meta = MetaAPI(acc.get('ig_account_id'), acc.get('fb_page_id'), acc.get('access_token'))
            
            ig_success = False
            if acc.get('ig_account_id'):
                try:
                    if media_type in ['VIDEO', 'REELS']: ig_success = acc_meta.upload_ig_reels_resumable(local_path, caption, file_id)
                    elif media_type == 'IMAGE': ig_success = acc_meta.upload_ig_image(local_path, caption, file_id)
                    elif media_type == 'CAROUSEL': ig_success = acc_meta.upload_ig_carousel(carousel_items, caption)
                except Exception as e: print(f"[ERR] Erro IG em {acc_name}: {e}")
            
            fb_success = False
            if acc.get('fb_page_id'):
                try:
                    if media_type in ['VIDEO', 'REELS']: fb_success = acc_meta.upload_fb_reels_resumable(local_path, caption)
                    elif media_type == 'IMAGE': fb_success = acc_meta.upload_fb_image(local_path, caption)
                    elif media_type == 'CAROUSEL': fb_success = acc_meta.upload_fb_carousel(carousel_items, caption)
                except Exception as e: print(f"[ERR] Erro FB em {acc_name}: {e}")
                
            if ig_success or fb_success:
                result["any_success"] = True
                result["total_posts"] += 1
                result["success_accounts"].append(acc_name)
            
            if (acc.get('ig_account_id') and not ig_success) or (acc.get('fb_page_id') and not fb_success):
                acc_p = acc.copy()
                if ig_success: acc_p['ig_account_id'] = None
                if fb_success: acc_p['fb_page_id'] = None
                result["failed_accounts"].append(acc_p)

    except Exception:
        traceback.print_exc()
    finally:
        # Nao removemos aqui, deixamos para o cleanup_tool.py
        pass
        
    return result

def main():
    print("=== DOE: Content Processor ===")
    drive = GoogleDriveAPI()
    tz_br = pytz.timezone('America/Sao_Paulo')
    
    # Carregar dados locais
    try:
        with open('schedule_queue.json', 'r', encoding='utf-8') as f: queue = json.load(f)
        with open('accounts.json', 'r', encoding='utf-8') as f: accounts = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar arquivos locais: {e}")
        return

    if not queue:
        print("[EMPTY] Fila vazia.")
        return

    current_time = int(time.time())
    max_posts_per_hour = 3
    posts_made_count = 0
    results = []

    for job in queue:
        schedule_time = job.get('schedule_time', 0)
        if current_time >= schedule_time and posts_made_count < max_posts_per_hour:
            dt_local = datetime.fromtimestamp(schedule_time, tz=tz_br)
            print(f"[*] [DUE] {job.get('filename')} (Agendado: {dt_local.strftime('%H:%M:%S')})")
            
            res = process_job(job, drive, accounts, tz_br)
            results.append(res)
            posts_made_count += 1
        
    # Salvar resultados para o cleanup_tool
    os.makedirs('.tmp', exist_ok=True)
    with open('.tmp/last_execution_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Processamento concluído. {len(results)} jobs processados.")

if __name__ == "__main__":
    main()
