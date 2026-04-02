import os
import time
import json
from gdrive_api import GoogleDriveAPI
from meta_api import MetaAPI

def main():
    print("=== Iniciando Cérebro da Nuvem (Reels Bot) ===")
    
    drive = GoogleDriveAPI()
    if not drive.service:
        print("Erro: API do Drive não inicializada.")
        return

    # 1. Carregar fila de agendamento LOCAL (O Github Actions traz isso pra gente)
    queue = []
    if os.path.exists("schedule_queue.json"):
        try:
            with open("schedule_queue.json", "r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception as e:
            print(f"Erro lendo schedule_queue.json: {e}")
            return
            
    posted_history = []
    if os.path.exists("posted_history.json"):
        try:
            with open("posted_history.json", "r", encoding="utf-8") as f:
                posted_history = json.load(f)
        except:
            pass
    
    # Helper to get list of IDs already posted
    def get_posted_ids(hist):
        ids = []
        for x in hist:
            if isinstance(x, dict): ids.append(x.get("id"))
            else: ids.append(x)
        return ids
    
    posted_ids = get_posted_ids(posted_history)
    
    # SUPER-PARANOID: Helper to check GITHUB directly (not just local disk)
    def is_posted_on_github(fid):
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            return False
            
        try:
            import requests, base64
            repo = "agenciaaguiacontact-sys/reels-bot-publico"
            url = f"https://api.github.com/repos/{repo}/contents/posted_history.json"
            h = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
            r = requests.get(url, headers=h)
            if r.status_code == 200:
                data = r.json()
                content = base64.b64decode(data['content']).decode('utf-8')
                hist = json.loads(content)
                return fid in get_posted_ids(hist)
        except Exception as e:
            print(f"Erro na checagem paranoica do GitHub: {e}")
        return False
        
    current_time = int(time.time())
    posted_any = False
    new_queue = []
    
    # 2. Verificar agendamentos
    for job in queue:
        schedule_time = job.get("schedule_time", 0)
        
        if schedule_time <= current_time:
            filename = job.get("filename", "video.mp4")
            file_id = job.get("gdrive_id")
            caption = job.get("caption", "")
            accounts = job.get("accounts", [])
            
            # SUPER-PARANOID CHECK: Refetch truth from GitHub Cloud repo
            if is_posted_on_github(file_id):
                print(f"⚠️ [DEDUPLICAÇÃO CLOUD] {filename} já foi postado e registrado no GitHub. Pulando.")
                continue

            print(f"\n---> Chegou a hora da mídia: {filename}")
            local_path = drive.download_file(file_id, filename)
            if not local_path or not os.path.exists(local_path):
                print("Falha ao baixar mídia do Drive.")
                new_queue.append(job)
                continue
                
            # Identificar tipo de mídia
            is_zip = filename.lower().endswith(".zip")
            is_image = filename.lower().endswith((".jpg", ".jpeg", ".png"))
            
            # Extrair se for ZIP (Carrossel)
            temp_extract_dir = None
            carousel_files = []
            if is_zip:
                import zipfile
                temp_extract_dir = os.path.abspath(f"temp_carousel_{int(time.time())}")
                os.makedirs(temp_extract_dir, exist_ok=True)
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                # Listar e ordenar arquivos extraídos
                carousel_files = [os.path.join(temp_extract_dir, f) for f in os.listdir(temp_extract_dir) if not f.startswith("__")]
                carousel_files.sort()
                print(f"📦 Carrossel detectado: {len(carousel_files)} itens extraídos.")

            failed_accounts = []
            any_acc_success = False
            
            for acc in accounts:
                acc_name = acc.get("name", "Sem Nome")
                print(f"  > [CONTA: {acc_name}]")
                meta = MetaAPI(
                    ig_account_id=acc.get("ig_account_id"),
                    fb_page_id=acc.get("fb_page_id"),
                    access_token=acc.get("access_token")
                )
                
                # --- INSTAGRAM ---
                if meta.ig_account_id:
                    print("    - Tentando INSTAGRAM...")
                    success = False
                    if is_zip:
                        success = meta.upload_ig_carousel(carousel_files, caption)
                    elif is_image:
                        success = meta.upload_ig_image(local_path, caption, gdrive_file_id=file_id)
                    else:
                        success = meta.upload_ig_reels_resumable(local_path, caption, gdrive_file_id=file_id)
                    
                    if success:
                        print("    ✅ Sucesso no Instagram!")
                        acc['ig_account_id'] = None
                    else:
                        print("    ❌ Falha no Instagram.")
                
                # --- FACEBOOK ---
                if meta.fb_page_id:
                    print("    - Tentando FACEBOOK...")
                    success = False
                    if is_zip:
                        success = meta.upload_fb_carousel(carousel_files, caption)
                    elif is_image:
                        success = meta.upload_fb_image(local_path, caption)
                    else:
                        success = meta.upload_fb_reels_resumable(local_path, caption)
                        
                    if success:
                        print("    ✅ Sucesso no Facebook!")
                        acc['fb_page_id'] = None
                    else:
                        print("    ❌ Falha no Facebook.")

                # Se sobrarm IDs pendentes, a conta vai para a lista de falhas/pendencias
                if acc.get('ig_account_id') or acc.get('fb_page_id'):
                    failed_accounts.append(acc)
                else:
                    any_acc_success = True

            if os.path.exists(local_path):
                os.remove(local_path)
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                import shutil
                shutil.rmtree(temp_extract_dir)
                
            if not failed_accounts and any_acc_success:
                print(f"✅ SUCESSO TOTAL! Apagando {filename} do Drive...")
                drive.delete_file(file_id)
                new_entry = {
                    "id": file_id,
                    "filename": filename,
                    "post_time": current_time
                }
                posted_history.append(new_entry)
                posted_ids.append(file_id)
                posted_any = True
            elif failed_accounts:
                print(f"⚠️ SUCESSO PARCIAL: Mantendo na fila para {len(failed_accounts)} conta(s) que falharam.")
                job["accounts"] = failed_accounts
                new_queue.append(job)
                posted_any = True # Sync queue because it changed
            else:
                print("❌ FALHA TOTAL no lote. Mantendo mídia na fila para retentativa.")
                new_queue.append(job)
        else:
            new_queue.append(job)
            time_left = schedule_time - current_time
            print(f"- {job.get('filename')} aguardando sua hora (faltam {time_left//60} min).")

    # 3. BÔNUS: Modo Compatibilidade (Vídeos soltos no Drive sem JSON)
    all_videos = drive.list_mp4_files()
    queued_ids = [j.get("gdrive_id") for j in queue]
    
    default_accounts = []
    if os.path.exists("accounts.json"):
        with open("accounts.json", "r", encoding="utf-8") as f:
            default_accounts = json.load(f)
            
    for v in all_videos:
        file_id = v['id']
        if file_id not in posted_ids and file_id not in queued_ids:
            print(f"\n---> Vídeo Solto detectado (Modo Imediato): {v['name']}")
            filename = v['name']
            caption = os.path.splitext(filename)[0]
            
            local_path = drive.download_file(file_id, filename)
            if not local_path: continue
            
            failed_accounts = []
            any_acc_success = False
            
            if default_accounts:
                for acc in default_accounts:
                    print(f"  > Postando Imediato para {acc.get('name')}")
                    # Trabalha em uma cópia para não estragar o default_accounts se houver reuso
                    temp_acc = acc.copy()
                    meta = MetaAPI(temp_acc.get("ig_account_id"), temp_acc.get("fb_page_id"), temp_acc.get("access_token"))
                    
                    if meta.ig_account_id:
                        # Passar gdrive_file_id para usar Google Drive
                        if meta.upload_ig_reels_resumable(local_path, caption, gdrive_file_id=file_id):
                            temp_acc['ig_account_id'] = None
                    if meta.fb_page_id:
                        if meta.upload_fb_reels_resumable(local_path, caption):
                            temp_acc['fb_page_id'] = None
                    
                    if not temp_acc.get('ig_account_id') and not temp_acc.get('fb_page_id'):
                        any_acc_success = True
                    else:
                        failed_accounts.append(temp_acc)
            else:
                meta = MetaAPI()
                # Passar gdrive_file_id para usar Google Drive
                if (meta.ig_account_id and meta.upload_ig_reels_resumable(local_path, caption, gdrive_file_id=file_id)) or \
                   (meta.fb_page_id and meta.upload_fb_reels_resumable(local_path, caption)):
                    any_acc_success = True
                else:
                    print("❌ Falha imediata no upload (sem contas padrão configuradas).")
            
            if os.path.exists(local_path):
                os.remove(local_path)
                
            if not failed_accounts and any_acc_success:
                print(f"✅ SUCESSO TOTAL no modo imediato! Apagando {filename} do Drive...")
                drive.delete_file(file_id)
                posted_history.append({
                    "id": file_id,
                    "filename": filename,
                    "post_time": current_time
                })
                posted_any = True
            elif failed_accounts:
                print(f"⚠️ SUCESSO PARCIAL (Imediato): Movendo para fila agendada para retentativa.")
                new_queue.append({
                    "gdrive_id": file_id,
                    "filename": filename,
                    "caption": caption,
                    "schedule_time": current_time + 900, # Tenta de novo no próximo ciclo
                    "accounts": failed_accounts
                })
                posted_any = True

    # 4. Salvar fila e historico (O Git Push do Workflow cuidará de subir pro repo)
    if posted_any or len(new_queue) != len(queue):
        print("\nSincronizando banco de dados local (schedule_queue.json e posted_history.json)...")
        with open("schedule_queue.json", "w", encoding="utf-8") as f:
            json.dump(new_queue, f, indent=2, ensure_ascii=False)
        with open("posted_history.json", "w", encoding="utf-8") as f:
            json.dump(posted_history[-500:], f, indent=2) # Mantem apenas os ultimos 500
        
    print("\n=== Ciclo da Nuvem Concluído ===")

if __name__ == "__main__":
    main()
