"""
DOE Execution: test_runner.py
Bateria de testes end-to-end do Reels Bot.
Gera mídias de teste, injeta na fila, executa o bot e produz relatório.
"""
import os
import sys
import json
import time
import struct
import subprocess
import traceback
import shutil
from datetime import datetime

# Forçar output em UTF-8 para evitar erros de encoding no Windows (CP1252)
if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

# Adicionar a raiz do projeto ao path para importar os módulos
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from meta_api import MetaAPI
from gdrive_api import GoogleDriveAPI

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
TEST_DIR = os.path.join(PROJECT_ROOT, '.tmp', 'test_assets')
REPORT_PATH = os.path.join(PROJECT_ROOT, '.tmp', 'test_report.md')
QUEUE_PATH = os.path.join(PROJECT_ROOT, 'schedule_queue.json')
HISTORY_PATH = os.path.join(PROJECT_ROOT, 'posted_history.json')
ACCOUNTS_PATH = os.path.join(PROJECT_ROOT, 'accounts.json')

TEST_CAPTION = "✅ [TESTE AUTOMÁTICO] Reels Bot — Validação de Sistema. Ignore esta publicação. 🤖"

# ─────────────────────────────────────────────
# GERAÇÃO DE MÍDIAS DE TESTE
# ─────────────────────────────────────────────

def _make_minimal_mp4(path):
    """Cria um arquivo .mp4 mínimo válido para teste (vídeo preto de 1s)."""
    # ftyp box (24 bytes)
    ftyp = (
        b'\x00\x00\x00\x18' # size
        b'ftyp'
        b'isom'             # major brand
        b'\x00\x00\x02\x00' # minor version
        b'isom' b'iso2'
    )
    # mdat box minimal (8 bytes header + 1 byte payload)
    mdat = b'\x00\x00\x00\x09mdat\x00'
    
    # moov box com track mínimo (necessário para algumas APIs aceitarem o arquivo)
    # Usando um moov mínimo bem-formado
    moov_content = (
        b'\x00\x00\x00\x6c'  # mvhd size=108 (0x6c)
        b'mvhd'
        b'\x00\x00\x00\x00'  # version + flags
        + b'\x00' * 16       # creation/modification/timescale/duration (zeros ok para teste)
        + b'\x00\x01\x00\x00' # rate
        + b'\x01\x00'         # volume
        + b'\x00' * 70        # padding + matrix + next track id
    )
    moov = struct.pack('>I', 8 + len(moov_content)) + b'moov' + moov_content
    
    with open(path, 'wb') as f:
        f.write(ftyp + mdat + moov)
    return path


def _make_jpeg(path, color=(30, 120, 200)):
    """Cria um JPEG mínimo de 1x1 pixel com a cor especificada (RGB)."""
    try:
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (100, 100), color)
        img.save(path, "JPEG", quality=85)
    except ImportError:
        # Fallback: JPEG mínimo hard-coded (1x1 pixel azul)
        _write_raw_jpeg(path)
    return path


def _write_raw_jpeg(path):
    """JPEG mínimo válido de 1x1 pixel azul (sem Pillow)."""
    data = bytes([
        0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
        0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
        0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
        0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
        0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
        0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
        0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
        0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
        0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
        0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
        0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,
        0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,0x24,0x33,0x62,0x72,
        0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
        0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,
        0x46,0x47,0x48,0x49,0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,
        0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6A,0x73,0x74,0x75,
        0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,
        0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,
        0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,
        0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,
        0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,
        0xF5,0xF6,0xF7,0xF8,0xF9,0xFA,0xFF,0xDA,0x00,0x08,0x01,0x01,
        0x00,0x00,0x3F,0x00,0xFB,0xD7,0xFF,0xD9
    ])
    with open(path, 'wb') as f:
        f.write(data)


def generate_test_assets():
    """Gera os arquivos de mídia de teste."""
    os.makedirs(TEST_DIR, exist_ok=True)
    print("🎨 Gerando mídias de teste...")

    video_path = os.path.join(TEST_DIR, 'test_reel.mp4')
    img1_path = os.path.join(TEST_DIR, 'test_image.jpg')
    img2_path = os.path.join(TEST_DIR, 'test_carousel_1.jpg')
    img3_path = os.path.join(TEST_DIR, 'test_carousel_2.jpg')

    _make_minimal_mp4(video_path)
    _make_jpeg(img1_path, color=(30, 120, 200))   # Azul
    _make_jpeg(img2_path, color=(200, 60, 60))    # Vermelho
    _make_jpeg(img3_path, color=(60, 180, 60))    # Verde

    print(f"  ✅ Vídeo: {video_path}")
    print(f"  ✅ Imagem 1 (single): {img1_path}")
    print(f"  ✅ Imagem 2 (carousel item 1): {img2_path}")
    print(f"  ✅ Imagem 3 (carousel item 2): {img3_path}")

    return {
        'video': video_path,
        'image': img1_path,
        'carousel': [img2_path, img3_path]
    }


# ─────────────────────────────────────────────
# UPLOAD PARA GDRIVE E INJEÇÃO NA FILA
# ─────────────────────────────────────────────

def upload_and_prepare_queue(assets, accounts, drive):
    """Faz upload das mídias de teste ao Drive e prepara a fila de agendamentos."""
    print("\n☁️ Fazendo upload dos assets de teste Para o Google Drive...")
    
    # Pasta de teste criada pelo bot para contornar problemas de permissão
    TEST_FOLDER_ID_FALLBACK = "1Vf7ezsZ5jTGE-eD-Zp3TBA31Xa-YV"
    test_folder_id = None
    for acc in accounts:
        if acc.get('gdrive_folder_id'):
            test_folder_id = acc['gdrive_folder_id']
            break
    
    if not test_folder_id:
        print(f"  ⚠️ Nenhuma pasta configurada. Usando fallback: {TEST_FOLDER_ID_FALLBACK}")
        test_folder_id = TEST_FOLDER_ID_FALLBACK
    
    # Tentar upload na pasta da conta, se falhar, usar fallback
    def _safe_upload(path, name, mime, preferred_folder):
        print(f"  📤 Tentando upload de {name}...")
        res = drive.upload_file(path, name, mime, preferred_folder)
        if not res and preferred_folder != TEST_FOLDER_ID_FALLBACK:
            print(f"  ⚠️ Falha na pasta preferida. Usando fallback: {TEST_FOLDER_ID_FALLBACK}")
            res = drive.upload_file(path, name, mime, TEST_FOLDER_ID_FALLBACK)
        return res

    jobs = []
    test_timestamp = int(time.time()) - 60  # Agendado 1 min atrás = executa imediatamente

    # Todas as contas como destino de todos os testes
    # (para testar múltiplas contas de uma vez)

    # T1/T4 — REELS (IG e FB são cobertos pelo DOE no content_processor)
    video_id = _safe_upload(assets['video'], 'test_reel.mp4', 'video/mp4', test_folder_id)
    if video_id or os.path.exists(assets['video']):
        if not video_id: print("  ⚠️ Usando arquivo LOCAL para teste de REELS (Bypass Drive).")
        jobs.append({
            "gdrive_id": video_id,
            "filename": "test_reel.mp4",
            "media_type": "REELS",
            "caption": TEST_CAPTION + " [REELS]",
            "schedule_time": test_timestamp,
            "accounts": accounts,
            "_test_type": "REELS",
            "_local_path_override": assets['video']
        })
    else:
        print("  ⚠️ Falha no upload e arquivo local não encontrado — pulando testes de REELS.")

    # T2/T5 — IMAGE
    img_id = _safe_upload(assets['image'], 'test_image.jpg', 'image/jpeg', test_folder_id)
    if img_id or os.path.exists(assets['image']):
        if not img_id: print("  ⚠️ Usando arquivo LOCAL para teste de IMAGE (Bypass Drive).")
        jobs.append({
            "gdrive_id": img_id,
            "filename": "test_image.jpg",
            "media_type": "IMAGE",
            "caption": TEST_CAPTION + " [IMAGE]",
            "schedule_time": test_timestamp,
            "accounts": accounts,
            "_test_type": "IMAGE",
            "_local_path_override": assets['image']
        })
    else:
        print("  ⚠️ Falha no upload e arquivo local não encontrado — pulando testes de IMAGE.")

    # T3/T6 — CAROUSEL
    # Upload individual de cada item e criação do job
    carousel_items_for_api = []
    for i, cp in enumerate(assets['carousel']):
        cid = _safe_upload(cp, f'test_carousel_{i+1}.jpg', 'image/jpeg', test_folder_id)
        if cid or os.path.exists(cp):
            if not cid: print(f"  ⚠️ Usando item LOCAL {i+1} para CAROUSEL (Bypass Drive).")
            carousel_items_for_api.append({
                'gdrive_id': cid, 
                'filename': f'test_carousel_{i+1}.jpg', 
                'media_type': 'IMAGE', 
                '_local_path_override': cp
            })

    if len(carousel_items_for_api) >= 2:
        jobs.append({
            "gdrive_id": None,
            "filename": "test_carousel",
            "media_type": "CAROUSEL",
            "caption": TEST_CAPTION + " [CAROUSEL]",
            "schedule_time": test_timestamp,
            "accounts": accounts,
            "_carousel_items_gdrive": carousel_items_for_api,
            "_test_type": "CAROUSEL"
        })
    else:
        print("  ⚠️ Itens de carousel insuficientes — pulando testes de CAROUSEL.")

    return jobs


# ─────────────────────────────────────────────
# EXECUÇÃO DIRETA (SEM INJEÇÃO NA FILA DO BOT)
# ─────────────────────────────────────────────

def run_direct_tests(jobs, drive):
    """
    Executa os uploads diretamente via MetaAPI (sem passar pelo bot),
    garantindo teste direto das funções de cada tipo de mídia.
    """
    results = []

    for job in jobs:
        test_type = job.get('_test_type', 'UNKNOWN')
        media_type = job.get('media_type')
        accounts = job.get('accounts', [])
        caption = job.get('caption', TEST_CAPTION)
        gdrive_id = job.get('gdrive_id')
        filename = job.get('filename')

        print(f"\n{'='*50}")
        print(f"🔬 Testando: {test_type} | gdrive_id={gdrive_id}")
        print(f"{'='*50}")

        for acc in accounts:
            acc_name = acc.get('name', 'Conta sem nome')
            ig_id = acc.get('ig_account_id')
            fb_id = acc.get('fb_page_id')
            token = acc.get('access_token')

            acc_meta = MetaAPI(ig_id, fb_id, token)

            # ─── Download da mídia temporária ───
            local_path = None
            carousel_local = []

            local_override = job.get('_local_path_override')
 
            if media_type == 'CAROUSEL':
                carousel_data = job.get('_carousel_items_gdrive', [])
                for item in carousel_data:
                    lp_ov = item.get('_local_path_override')
                    if lp_ov and os.path.exists(lp_ov):
                        carousel_local.append({'local_path': lp_ov, 'gdrive_id': item['gdrive_id'], 'media_type': 'IMAGE', '_is_local': True})
                    elif item['gdrive_id']:
                        lp = drive.download_file(item['gdrive_id'], item['filename'], os.path.join(PROJECT_ROOT, '.tmp'))
                        if lp:
                            carousel_local.append({'local_path': lp, 'gdrive_id': item['gdrive_id'], 'media_type': 'IMAGE'})
            elif local_override and os.path.exists(local_override):
                local_path = local_override
                print(f"  ✅ Usando asset local: {local_path}")
            elif gdrive_id:
                local_path = drive.download_file(gdrive_id, filename, os.path.join(PROJECT_ROOT, '.tmp'))

            # ─── IG Tests ───
            if ig_id:
                ig_result = {'account': acc_name, 'platform': 'Instagram', 'type': test_type, 'success': False, 'post_id': None, 'error': None}
                try:
                    print(f"  📸 IG ({acc_name}) → {media_type}...")
                    if media_type == 'REELS' and local_path:
                        ig_result['success'] = acc_meta.upload_ig_reels_resumable(local_path, caption, gdrive_id)
                    elif media_type == 'IMAGE' and local_path:
                        ig_result['success'] = acc_meta.upload_ig_image(local_path, caption, gdrive_id)
                    elif media_type == 'CAROUSEL' and carousel_local:
                        ig_result['success'] = acc_meta.upload_ig_carousel(carousel_local, caption)
                    print(f"  → {'✅ SUCESSO' if ig_result['success'] else '❌ FALHA'}")
                except Exception as e:
                    ig_result['error'] = traceback.format_exc()
                    print(f"  → ❌ EXCEÇÃO: {e}")
                results.append(ig_result)

            # ─── FB Tests ───
            if fb_id:
                fb_result = {'account': acc_name, 'platform': 'Facebook', 'type': test_type, 'success': False, 'post_id': None, 'error': None}
                try:
                    print(f"  📘 FB ({acc_name}) → {media_type}...")
                    if media_type == 'REELS' and local_path:
                        fb_result['success'] = acc_meta.upload_fb_reels_resumable(local_path, caption)
                    elif media_type == 'IMAGE' and local_path:
                        fb_result['success'] = acc_meta.upload_fb_image(local_path, caption)
                    elif media_type == 'CAROUSEL' and carousel_local:
                        fb_result['success'] = acc_meta.upload_fb_carousel(carousel_local, caption)
                    print(f"  → {'✅ SUCESSO' if fb_result['success'] else '❌ FALHA'}")
                except Exception as e:
                    fb_result['error'] = traceback.format_exc()
                    print(f"  → ❌ EXCEÇÃO: {e}")
                results.append(fb_result)

        # Limpeza dos arquivos temporários baixados
        # (Apenas se NÃO forem originais do assets/)
        if local_path and os.path.exists(local_path) and '.tmp\\test_assets' not in local_path:
            os.remove(local_path)
        for it in carousel_local:
            if os.path.exists(it['local_path']) and not it.get('_is_local'):
                os.remove(it['local_path'])

    return results


# ─────────────────────────────────────────────
# TAMBÉM TESTAR VIA ORQUESTRADOR (main.py --once)
# ─────────────────────────────────────────────

def run_via_orchestrator(jobs):
    """
    Injeta 1 job de teste na fila e executa o bot completo (main.py --once)
    para testar a integração do orquestrador DOE.
    Usa apenas o primeiro job (REELS) para não duplicar todos os posts.
    """
    if not jobs:
        return None, None

    test_job = jobs[0].copy()
    test_job.pop('_test_type', None)
    test_job.pop('_carousel_items_gdrive', None)
    test_job['caption'] = TEST_CAPTION + " [VIA ORQUESTRADOR]"
    test_job['schedule_time'] = int(time.time()) - 60

    # Fazer backup da fila original
    original_queue = []
    if os.path.exists(QUEUE_PATH):
        try:
            with open(QUEUE_PATH, 'r', encoding='utf-8') as f:
                original_queue = json.load(f)
        except:
            pass

    # Injetar apenas o job de teste
    with open(QUEUE_PATH, 'w', encoding='utf-8') as f:
        json.dump([test_job], f, indent=2, ensure_ascii=False)

    print("\n🤖 Executando bot via orquestrador (python main.py --once)...")
    stdout_log = ""
    try:
        # Injetar a pasta de teste no ambiente para o orquestrador não falhar na sincronização
        env = os.environ.copy()
        env["GDRIVE_FOLDER_ID"] = "1Vf7ezsZ5jTGE-eD-Zp3TBA31Xa-YV"
        
        res = subprocess.run(
            [sys.executable, 'main.py', '--once'],
            capture_output=True, text=True, timeout=600,
            cwd=PROJECT_ROOT, env=env
        )
        stdout_log = res.stdout + ("\n--- STDERR ---\n" + res.stderr if res.stderr.strip() else "")
        print(stdout_log)
    except subprocess.TimeoutExpired:
        stdout_log = "TIMEOUT: O bot não concluiu em 10 minutos."
        print(f"  ⚠️ {stdout_log}")
    except Exception as e:
        stdout_log = f"ERRO AO EXECUTAR: {e}"
        print(f"  ❌ {stdout_log}")
    finally:
        # Restaurar a fila original
        with open(QUEUE_PATH, 'w', encoding='utf-8') as f:
            json.dump(original_queue, f, indent=2, ensure_ascii=False)

    return test_job, stdout_log


# ─────────────────────────────────────────────
# RELATÓRIO FINAL
# ─────────────────────────────────────────────

def build_report(results, orchestrator_job, orchestrator_log, start_time):
    """Gera o relatório final em Markdown."""
    duration = time.time() - start_time
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = len(results)
    passed = sum(1 for r in results if r['success'])

    lines = [
        f"# 📊 Relatório de Testes — Reels Bot",
        f"",
        f"**Data:** {now_str}",
        f"**Duração:** {duration:.1f}s",
        f"**Score:** {passed}/{total} testes passaram",
        f"**Status Geral:** {'🟢 TUDO OK' if passed == total else ('🟡 PARCIAL' if passed > 0 else '🔴 FALHA TOTAL')}",
        f"",
    ]

    # Sucessos
    successes = [r for r in results if r['success']]
    lines.append("## ✅ Sucessos\n")
    if successes:
        lines.append("| Conta | Plataforma | Tipo de Mídia |")
        lines.append("|-------|-----------|---------------|")
        for r in successes:
            lines.append(f"| {r['account']} | {r['platform']} | {r['type']} |")
    else:
        lines.append("> Nenhum teste foi bem-sucedido.")
    lines.append("")

    # Falhas
    failures = [r for r in results if not r['success']]
    lines.append("## ❌ Falhas\n")
    if failures:
        lines.append("| Conta | Plataforma | Tipo de Mídia | Erro |")
        lines.append("|-------|-----------|---------------|------|")
        for r in failures:
            err_short = str(r.get('error') or 'Retornou False sem exceção')
            err_short = err_short.replace('\n', ' ')[:120]
            lines.append(f"| {r['account']} | {r['platform']} | {r['type']} | `{err_short}` |")
        lines.append("")
        lines.append("### Detalhes dos Erros\n")
        for r in failures:
            if r.get('error'):
                lines.append(f"**{r['account']} / {r['platform']} / {r['type']}:**")
                lines.append(f"```\n{r['error']}\n```\n")
    else:
        lines.append("> Nenhuma falha registrada. 🎉")
    lines.append("")

    # Log do orquestrador
    lines.append("## 🤖 Teste do Orquestrador (main.py --once)\n")
    if orchestrator_log:
        orch_ok = "SUCESSO" in orchestrator_log.upper() or "PUBLICADO" in orchestrator_log.upper()
        lines.append(f"**Status:** {'✅ OK' if orch_ok else '❌ Verificar log'}\n")
        lines.append("```")
        lines.append(orchestrator_log[:3000])  # Limita para não explodir o relatório
        lines.append("```")
    else:
        lines.append("> Teste do orquestrador não executado.")

    report = "\n".join(lines)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)

    return report


# ─────────────────────────────────────────────
# LIMPEZA DOS ASSETS DO DRIVE
# ─────────────────────────────────────────────

def cleanup_drive_assets(jobs, drive):
    """Remove os arquivos de teste do Google Drive."""
    print("\n🧹 Removendo assets de teste do Google Drive...")
    for job in jobs:
        gid = job.get('gdrive_id')
        if gid:
            drive.delete_file(gid)
            print(f"  🗑️ Deletado: {gid}")
        for item in job.get('_carousel_items_gdrive', []):
            drive.delete_file(item['gdrive_id'])
            print(f"  🗑️ Deletado (carousel item): {item['gdrive_id']}")

    # Limpar pasta de assets locais
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
        print(f"  🗑️ Pasta .tmp/test_assets removida.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("🧪 REELS BOT — Bateria de Testes End-to-End")
    print("=" * 60)
    start_time = time.time()

    drive = GoogleDriveAPI()

    # 1. Carregar contas
    if not os.path.exists(ACCOUNTS_PATH):
        print("❌ accounts.json não encontrado. Abortando.")
        sys.exit(1)

    with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
        accounts = json.load(f)

    if not accounts:
        print("❌ Nenhuma conta configurada. Abortando.")
        sys.exit(1)

    print(f"\n📱 Contas a testar: {[a.get('name') for a in accounts]}\n")

    # 2. Gerar mídias de teste
    assets = generate_test_assets()

    # 3. Upload para Drive + preparar jobs
    jobs = upload_and_prepare_queue(assets, accounts, drive)

    if not jobs:
        print("❌ Nenhum job de teste foi preparado. Verifique a conexão com o Drive.")
        sys.exit(1)

    # 4. Testes diretos via MetaAPI
    print("\n🔬 Iniciando testes diretos via MetaAPI...")
    results = run_direct_tests(jobs, drive)

    # 5. Teste via orquestrador DOE
    orch_job, orch_log = run_via_orchestrator(jobs)

    # 6. Limpar Drive
    cleanup_drive_assets(jobs, drive)

    # 7. Gerar relatório
    report = build_report(results, orch_job, orch_log, start_time)

    print("\n" + "=" * 60)
    print("📄 RELATÓRIO FINAL")
    print("=" * 60)
    print(report)
    print(f"\n💾 Relatório salvo em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
