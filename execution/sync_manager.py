import os
import json
import argparse
import sys

# Garante que o diretorio raiz esteja no path, mesmo se executado de dentro de 'execution/'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gdrive_api import GoogleDriveAPI

# Forçar output em UTF-8 para evitar erros de encoding no Windows (CP1252)
if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

def download_all(drive):
    print("Sincronizando do GDrive (Download)...")
    files = ['schedule_queue.json', 'accounts.json', 'posted_history.json', 'library.json']
    for f in files:
        try:
            data = drive.get_json(f)
            if data is not None:
                with open(f, 'w', encoding='utf-8') as local_f:
                    json.dump(data, local_f, indent=2, ensure_ascii=False)
                print(f"✅ {f} baixado.")
            else:
                print(f"⚠️ {f} vazio ou não encontrado no Drive.")
        except Exception as e:
            print(f"❌ Erro ao baixar {f}: {e}")

def upload_all(drive):
    print("Sincronizando para o GDrive (Upload)...")
    files = ['schedule_queue.json', 'accounts.json', 'posted_history.json', 'library.json'] # Incluindo accounts.json e library.json para Cloud
    for f in files:
        try:
            if os.path.exists(f):
                with open(f, 'r', encoding='utf-8') as local_f:
                    data = json.load(local_f)
                res = drive.save_json(f, data)
                if res:
                    print(f"✅ {f} enviado ao Drive.")
                else:
                    print(f"❌ Falha ao enviar {f} ao Drive.")
            else:
                print(f"⚠️ {f} local não encontrado.")
        except Exception as e:
            print(f"❌ Erro ao enviar {f}: {e}")

def main():
    parser = argparse.ArgumentParser(description="DOE Execution: Sync Manager")
    parser.add_argument("--action", choices=["download", "upload"], required=True)
    args = parser.parse_args()

    drive = GoogleDriveAPI()
    
    if args.action == "download":
        download_all(drive)
    elif args.action == "upload":
        upload_all(drive)

if __name__ == "__main__":
    main()
