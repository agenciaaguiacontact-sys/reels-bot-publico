import subprocess
import time
import os
import sys
import traceback

def run_script(script_path, args=[]):
    """Executa um script de execução determinístico."""
    cmd = [sys.executable, script_path] + args
    print(f"\n--- Executando: {' '.join(cmd)} ---")
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar {script_path}: {e}")
        return False

def orchestrate():
    """Lógica central de orquestração seguindo o Framework DOE."""
    print("=== DOE Orchestrator: Reels Bot Cloud ===")
    
    # 1. Directive: Ler scheduler_protocol.md (Apenas para contexto do agente, o código segue as fases)
    
    # 2. Execution Phase: Sync Download
    if not run_script("execution/sync_manager.py", ["--action", "download"]):
        print("⚠️ Aviso: Falha na sincronização inicial. Continuando com dados locais (Fallback).")
    
    # 3. Execution Phase: Content Processor
    # Nota: O content_processor já gerencia o loop interno da fila e horários
    run_script("execution/content_processor.py")
    
    # 4. Execution Phase: Cleanup and State Update
    run_script("execution/cleanup_tool.py")
    
    # 5. Execution Phase: Sync Upload
    if not run_script("execution/sync_manager.py", ["--action", "upload"]):
        print("❌ Erro ao sincronizar estados finais ao GDrive.")

def main():
    run_once = os.getenv('RUN_ONCE') == 'true' or "--once" in sys.argv
    
    while True:
        try:
            orchestrate()
            
            if run_once:
                print("🏁 Execução única concluída.")
                break
                
            print("\n⏰ Ciclo finalizado. Aguardando 1 minuto para o próximo...")
            time.sleep(60)
            
        except Exception:
            traceback.print_exc()
            time.sleep(60)
            if run_once: break

if __name__ == "__main__":
    main()
