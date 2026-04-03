# 📊 Relatório de Testes — Reels Bot

**Data:** 2026-04-03 00:00:35
**Duração:** 658.6s
**Score:** 8/12 testes passaram
**Status Geral:** 🟡 PARCIAL

## ✅ Sucessos

| Conta | Plataforma | Tipo de Mídia |
|-------|-----------|---------------|
| Dentista Curioso | Instagram | IMAGE |
| Dentista Curioso | Facebook | IMAGE |
| Enfermagem Curiosa | Instagram | IMAGE |
| Enfermagem Curiosa | Facebook | IMAGE |
| Dentista Curioso | Instagram | CAROUSEL |
| Dentista Curioso | Facebook | CAROUSEL |
| Enfermagem Curiosa | Instagram | CAROUSEL |
| Enfermagem Curiosa | Facebook | CAROUSEL |

## ❌ Falhas

| Conta | Plataforma | Tipo de Mídia | Erro |
|-------|-----------|---------------|------|
| Dentista Curioso | Instagram | REELS | `Retornou False sem exceção` |
| Dentista Curioso | Facebook | REELS | `Retornou False sem exceção` |
| Enfermagem Curiosa | Instagram | REELS | `Retornou False sem exceção` |
| Enfermagem Curiosa | Facebook | REELS | `Retornou False sem exceção` |

### Detalhes dos Erros


## 🤖 Teste do Orquestrador (main.py --once)

**Status:** ❌ Verificar log

```
Credenciais do Google Drive carregadas via Base64.
Sincronizando do GDrive (Download)...
=== DOE Orchestrator: Reels Bot Cloud ===

--- Executando: C:\Users\robso\AppData\Local\Programs\Python\Python312\python.exe execution/sync_manager.py --action download ---

--- STDERR ---
Traceback (most recent call last):
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\execution\sync_manager.py", line 22, in download_all
    print(f"\u26a0\ufe0f {f} vazio ou não encontrado no Drive.")
  File "C:\Users\robso\AppData\Local\Programs\Python\Python312\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-1: character maps to <undefined>

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\execution\sync_manager.py", line 57, in <module>
    main()
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\execution\sync_manager.py", line 52, in main
    download_all(drive)
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\execution\sync_manager.py", line 24, in download_all
    print(f"\u274c Erro ao baixar {f}: {e}")
  File "C:\Users\robso\AppData\Local\Programs\Python\Python312\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c' in position 0: character maps to <undefined>
Traceback (most recent call last):
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\main.py", line 24, in run_script
    result = subprocess.run(cmd, check=True, env=env)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\robso\AppData\Local\Programs\Python\Python312\Lib\subprocess.py", line 571, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '['C:\\Users\\robso\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', 'execution/sync_manager.py', '--action', 'download']' returned non-zero exit status 1.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\main.py", line 61, in main
    orchestrate()
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\main.py", line 37, in orchestrate
    if not run_script("execution/sync_manager.py", ["--action", "download"]):
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia\main.py", line 27, in run_script
    print(f"\u274c Erro ao executar {script_path}: {e}")
  File "C:\Users\robs
```