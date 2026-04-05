import os
import json
import time
import sys

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

def cleanup_tmp():
    print("[-] Limpando pasta .tmp...")
    if os.path.exists('.tmp'):
        for f in os.listdir('.tmp'):
            p = os.path.join('.tmp', f)
            try:
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    import shutil
                    shutil.rmtree(p)
            except Exception as e:
                print(f"[!] Erro ao remover {f}: {e}")
    
    # Limpeza extra: Arquivos temporários e logs soltos na raiz
    print("[-] Limpando arquivos temporários da raiz...")
    for f in os.listdir('.'):
        if (f.startswith('temp_') and f.endswith('.json')) or \
           (f.startswith('final_debug_log_') and f.endswith('.txt')) or \
           (f == 'debug_log.txt' and os.path.getsize(f) > 5 * 1024 * 1024): # Log maior que 5MB
            try:
                os.remove(f)
                print(f"  [x] Removido: {f}")
            except:
                pass

def cleanup_downloads(days=1):
    """Limpa arquivos na pasta downloads que tenham mais de 'days' dias."""
    print(f"[-] Limpando pasta downloads (arquivos > {days} dia)...")
    if not os.path.exists('downloads'):
        return
    
    now = time.time()
    for f in os.listdir('downloads'):
        p = os.path.join('downloads', f)
        if os.path.isfile(p):
            # Não remove pastas de carrossel, apenas arquivos individuais (mídias)
            if os.path.getmtime(p) < now - (days * 86400):
                try:
                    os.remove(p)
                    print(f"  [x] Removido de downloads: {f}")
                except:
                    pass

def archive_history(limit=500):
    """Move entradas excedentes do histórico para a pasta archive/."""
    print(f"[-] Verificando arquivamento de histórico (limite: {limit})...")
    history_path = 'posted_history.json'
    if not os.path.exists(history_path):
        return
        
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
            
        if len(history) <= limit:
            print(f"[OK] Histórico dentro do limite ({len(history)} itens).")
            return
            
        # Separar itens excedentes (os mais antigos)
        excess_count = len(history) - limit
        to_archive = history[:excess_count]
        remaining = history[excess_count:]
        
        # Criar pasta de arquivo se não existir
        os.makedirs('archive', exist_ok=True)
        
        # Agrupar por mês/ano baseado no post_time
        import datetime
        for item in to_archive:
            ts = item.get('post_time', time.time())
            dt = datetime.datetime.fromtimestamp(ts)
            archive_name = f"archive/history_{dt.year}_{dt.month:02d}.json"
            
            # Carregar arquivo de arquivo existente ou criar novo
            existing_archive = []
            if os.path.exists(archive_name):
                with open(archive_name, 'r', encoding='utf-8') as af:
                    existing_archive = json.load(af)
            
            existing_archive.append(item)
            
            with open(archive_name, 'w', encoding='utf-8') as af:
                json.dump(existing_archive, af, indent=2, ensure_ascii=False)
        
        # Salvar histórico principal reduzido
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(remaining, f, indent=2, ensure_ascii=False)
            
        print(f"[OK] Arquivados {excess_count} itens com sucesso.")
        
    except Exception as e:
        print(f"[ERR] Erro ao arquivar histórico: {e}")

def main():
    print("=== DOE: Cleanup Tool ===")
    drive = GoogleDriveAPI()
    
    # 1. Limpeza de Downloads e Temporários Incondicional
    cleanup_downloads(days=1)
    cleanup_tmp()
    archive_history(limit=500)
    
    results_path = '.tmp/last_execution_results.json'
    if not os.path.exists(results_path):
        print("[EMPTY] Nenhum resultado de execução para processar.")
        return

    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    # Carregar estados atuais locais
    try:
        with open('schedule_queue.json', 'r', encoding='utf-8') as f: queue = json.load(f)
        with open('posted_history.json', 'r', encoding='utf-8') as f: history = json.load(f)
    except:
        print("[ERR] Erro ao carregar estados locais para limpeza.")
        return

    new_queue = []
    # Usar um conjunto de gdrive_ids processados para evitar duplicatas na nova fila
    processed_job_ids = [res['job'].get('gdrive_id') for res in results]
    
    # Manter na fila o que não foi processado nesta execução
    for job in queue:
        if job.get('gdrive_id') not in processed_job_ids:
            new_queue.append(job)

    # Processar resultados da execução
    for res in results:
        job = res['job']
        gdrive_id = job.get('gdrive_id')
        filename = job.get('filename')
        
        if res['any_success']:
            if not res['failed_accounts']:
                # Sucesso total!
                print(f"[OK] [FULL SUCCESS] {filename}. Removendo do Drive.")
                drive.delete_file(gdrive_id)
                history.append({"id": gdrive_id, "filename": filename, "post_time": int(time.time()), "accounts": res['success_accounts']})
            else:
                # Sucesso parcial
                print(f"[!] [PARTIAL SUCCESS] {filename}. Mantendo falhas na fila.")
                job['accounts'] = res['failed_accounts']
                new_queue.append(job)
                history.append({"id": gdrive_id, "filename": filename, "post_time": int(time.time()), "status": "partial", "success_accounts": res['success_accounts']})
        else:
            # Falha total
            print(f"[ERR] [TOTAL FAILURE] {filename}. Mantendo na fila para retentar.")
            new_queue.append(job)

    # Salvar estados locais atualizados
    with open('schedule_queue.json', 'w', encoding='utf-8') as f:
        json.dump(new_queue, f, indent=2, ensure_ascii=False)
    
    with open('posted_history.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print("[OK] Estados locais atualizados.")
    
    # Limpar resultados e temporários finais
    if os.path.exists(results_path):
        os.remove(results_path)
    
    # Re-executar arquivamento após atualização
    archive_history(limit=500)

if __name__ == "__main__":
    main()
