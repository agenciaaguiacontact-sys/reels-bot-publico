import subprocess
import time
import os
import sys
import traceback

def run_script(script_path, args=[]):
    """Executa um script de execução determinístico com PYTHONPATH configurado."""
    # Garante que o diretório raiz esteja no PYTHONPATH para que os scripts encontrem as APIs
    env = os.environ.copy()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Em Windows, PYTHONPATH usa ';', em Linux usa ':'
    sep = ';' if os.name == 'nt' else ':'
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{root_dir}{sep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = root_dir

    cmd = [sys.executable, script_path] + args
    print(f"\n--- Executando: {' '.join(cmd)} ---")
    try:
        # Passando o ambiente modificado com o PYTHONPATH correto
        result = subprocess.run(cmd, check=True, env=env)
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
    # Detectar se estamos no GitHub Actions ou se o argumento --once foi passado
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    run_once = os.getenv('RUN_ONCE') == 'true' or "--once" in sys.argv or is_github_actions
    
    if is_github_actions:
        print("🤖 Ambiente GitHub Actions detectado. Executando em modo síncrono (Uma vez).")

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
