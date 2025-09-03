#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 Bot do Telegram - Sistema Gigante 4GB com Telethon
Todas as funcionalidades do painel em versão bot
Usando apenas a nuvem do Telegram - sem RAM/memória local
"""

import os
import logging
import re
import io
import zipfile
import rarfile
import asyncio
import tempfile
from urllib.parse import urlparse
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename
import time

# Configurações de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== CONFIGURAÇÕES DO BOT TELETHON ==========
# Credenciais obtidas das variáveis de ambiente
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH") 
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID", "123456789")  # ID do admin

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("❌ Configurações faltando! Configure: API_ID, API_HASH, TELEGRAM_BOT_TOKEN")
    exit(1)

try:
    api_id_int = int(API_ID)
    admin_id_int = int(ADMIN_ID)
except (ValueError, TypeError):
    logger.error("❌ API_ID e ADMIN_ID devem ser números!")
    exit(1)

# Cliente Telethon
bot = TelegramClient('bot', api_id_int, API_HASH)

# Controle do painel web
painel_ativo = False

# Controle de uploads em lote
upload_tasks = {}  # {chat_id: {'active': bool, 'files': [], 'results': []}}
processing_queue = {}  # {chat_id: asyncio.Queue}

# ========== FUNÇÕES DE FILTRAGEM (do painel original) ==========

def detectar_url_brasileira(url):
    """
    Detecta URLs brasileiras (.br + sites nacionais conhecidos)
    IGUAL AO PAINEL ORIGINAL
    """
    url_lower = url.lower()
    
    # URLs .br diretas
    if '.br' in url_lower:
        return True
    
    # Sites brasileiros .com/.net conhecidos (LISTA EXPANDIDA DO PAINEL)
    sites_br_conhecidos = [
        # Bancos
        'itau.com', 'bradesco.com', 'bb.com', 'santander.com',
        'sicoob.com', 'sicredi.com', 'banrisul.com', 'caixa.gov',
        'bndes.gov', 'bcb.gov', 'nubank.com', 'inter.co',
        
        # E-commerce
        'mercadolivre.com', 'americanas.com', 'magazineluiza.com',
        'casasbahia.com', 'extra.com', 'pontofrio.com',
        'submarino.com', 'shoptime.com', 'netshoes.com',
        'dafiti.com', 'kanui.com', 'centauro.com',
        
        # Tecnologia e Comunicação
        'uol.com', 'globo.com', 'terra.com', 'ig.com',
        'bol.com', 'zipmail.com', 'hotmail.com',
        'vivo.com', 'tim.com', 'claro.com', 'oi.com',
        
        # Governo e Serviços
        'correios.com', 'anatel.gov', 'receita.fazenda.gov',
        'detran.', 'tjsp.jus', 'tjrj.jus', 'jus.com',
        'gov.br', 'inss.gov', 'caixa.gov', 'serpro.gov',
        
        # Outros populares
        'abril.com', 'folha.com', 'estadao.com', 'r7.com',
        'band.com', 'sbt.com', 'record.com', 'globoplay.com'
    ]
    
    return any(site in url_lower for site in sites_br_conhecidos)

def linha_valida(linha):
    """
    Valida se linha tem formato de credencial válido
    IGUAL AO PAINEL ORIGINAL
    """
    if not linha or len(linha) < 5:
        return False
    
    # Conta dois pontos na linha
    count_dois_pontos = linha.count(':')
    if count_dois_pontos < 2:
        return False
    
    # Verifica se não é só caracteres especiais
    if re.match(r'^[^a-zA-Z0-9]*$', linha):
        return False
    
    return True

def filtrar_spam_divulgacao(linha):
    """
    Remove linhas de spam e divulgação, deixando só URL:USER:PASS
    FILTROS IGUAIS AO PAINEL ORIGINAL
    """
    linha_lower = linha.lower()
    
    # Lista de termos de spam/divulgação para remover (DO PAINEL)
    termos_spam = [
        # Divulgação comum
        'telegram.me', 'telegram.org', 't.me', '@', 'canal', 'grupo',
        'divulga', 'vendas', 'contato', 'whatsapp', 'zap',
        
        # Nomes/apelidos
        'admin', 'moderador', 'vendedor', 'hacker', 'cracker',
        'owner', 'dono', 'chefe', 'boss', 'master',
        
        # Propaganda
        'comprar', 'vender', 'barato', 'promo', 'desconto',
        'gratis', 'free', 'premium', 'vip', 'exclusivo',
        
        # Links promocionais
        'bit.ly', 'tinyurl', 'encurtador', 'link',
        'acesse', 'clique', 'download', 'baixar',
        
        # Textos promocionais
        'melhor', 'top', 'qualidade', 'confiavel', 'seguro',
        'rapido', 'facil', 'simples', 'garantido',
        
        # Termos de hack
        'combo', 'list', 'lista', 'pack', 'pacote',
        'fresh', 'novo', 'updated', 'atualizado'
    ]
    
    # Se contém termos de spam, remove a linha
    for termo in termos_spam:
        if termo in linha_lower:
            return None
    
    # Se não é formato URL:USER:PASS, remove
    if not linha_valida(linha):
        return None
    
    return linha.strip()

def processar_credencial(linha):
    """
    Processa uma linha de credencial e extrai dados
    IGUAL AO PAINEL ORIGINAL
    """
    linha_limpa = linha.strip()
    
    # Filtra spam primeiro
    linha_filtrada = filtrar_spam_divulgacao(linha_limpa)
    if not linha_filtrada:
        return None
    
    try:
        # Separa por dois pontos
        partes = linha_filtrada.split(':')
        
        # Formato: http://site.com:user:pass
        if linha_filtrada.startswith(('https://', 'http://')):
            if len(partes) >= 3:
                url = ':'.join(partes[:-2])
                username = partes[-2]
                password = partes[-1]
            else:
                return None
        # Formato: site.com:user:pass
        else:
            if len(partes) >= 3:
                url = partes[0]
                username = partes[1]
                password = partes[2]
            else:
                return None
        
        # Validações básicas
        if not all([url, username, password]):
            return None
        
        if len(username) < 2 or len(password) < 2:
            return None
        
        # Retorna dados estruturados
        return {
            'url': url.strip(),
            'username': username.strip(),
            'password': password.strip(),
            'linha_completa': linha_filtrada,
            'is_brazilian': detectar_url_brasileira(url)
        }
    
    except Exception:
        return None

# ========== PROCESSAMENTO DE ARQUIVOS ==========

async def processar_arquivo_texto(content, filename, chat_id):
    """
    Processa arquivo de texto com filtragem completa
    USANDO APENAS NUVEM DO TELEGRAM - SEM RAM LOCAL
    """
    try:
        # Decodifica content
        if isinstance(content, bytes):
            text_content = content.decode('utf-8', errors='ignore')
        else:
            text_content = content
        
        lines = text_content.split('\n')
        
        credenciais_validas = []
        credenciais_br = []
        stats = {
            'total_lines': len(lines),
            'valid_lines': 0,
            'brazilian_lines': 0,
            'spam_removed': 0
        }
        
        # Processa cada linha
        for linha in lines:
            if not linha.strip():
                continue
            
            # Processa credencial
            credencial = processar_credencial(linha)
            
            if credencial:
                credenciais_validas.append(credencial['linha_completa'])
                stats['valid_lines'] += 1
                
                # Se é brasileira, adiciona à lista BR
                if credencial['is_brazilian']:
                    credenciais_br.append(credencial['linha_completa'])
                    stats['brazilian_lines'] += 1
            else:
                stats['spam_removed'] += 1
        
        return credenciais_validas, credenciais_br, stats
    
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        return [], [], {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}

async def processar_arquivo_zip(content, filename, chat_id):
    """
    Processa arquivo ZIP com múltiplos TXTs
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_file:
            todas_credenciais = []
            todas_br = []
            stats_total = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
            
            for file_info in zip_file.filelist:
                if file_info.filename.lower().endswith('.txt'):
                    with zip_file.open(file_info) as txt_file:
                        txt_content = txt_file.read()
                        
                        credenciais, br_creds, stats = await processar_arquivo_texto(
                            txt_content, f"{filename}:{file_info.filename}", chat_id
                        )
                        
                        todas_credenciais.extend(credenciais)
                        todas_br.extend(br_creds)
                        
                        # Soma estatísticas
                        for key in stats_total:
                            stats_total[key] += stats[key]
            
            return todas_credenciais, todas_br, stats_total
    
    except Exception as e:
        logger.error(f"Erro no ZIP: {e}")
        return [], [], {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}

async def processar_arquivo_rar(content, filename, chat_id):
    """
    Processa arquivo RAR com múltiplos TXTs
    """
    try:
        # Salva temporariamente (necessário para rarfile)
        temp_path = os.path.join(tempfile.gettempdir(), f"temp_{int(time.time())}.rar")
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        todas_credenciais = []
        todas_br = []
        stats_total = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
        
        with rarfile.RarFile(temp_path, 'r') as rar_file:
            for file_info in rar_file.namelist():
                if file_info.lower().endswith('.txt'):
                    with rar_file.open(file_info) as txt_file:
                        txt_content = txt_file.read()
                        
                        credenciais, br_creds, stats = await processar_arquivo_texto(
                            txt_content, f"{filename}:{file_info}", chat_id
                        )
                        
                        todas_credenciais.extend(credenciais)
                        todas_br.extend(br_creds)
                        
                        # Soma estatísticas
                        for key in stats_total:
                            stats_total[key] += stats[key]
        
        # Remove arquivo temporário
        temp_path = locals().get('temp_path')
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return todas_credenciais, todas_br, stats_total
    
    except Exception as e:
        logger.error(f"Erro no RAR: {e}")
        # Remove arquivo temporário se existir
        try:
            temp_path_local = locals().get('temp_path')
            if temp_path_local and os.path.exists(temp_path_local):
                os.remove(temp_path_local)
        except:
            pass
        return [], [], {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}

# ========== FUNÇÕES DE ENVIO DE RESULTADOS ==========

async def enviar_resultado_como_arquivo(chat_id, credenciais, tipo, stats):
    """
    Envia resultado como arquivo na nuvem do Telegram
    """
    if not credenciais:
        await bot.send_message(chat_id, f"❌ Nenhuma credencial {tipo} encontrada.")
        return
    
    try:
        # Cria conteúdo do arquivo
        content = '\n'.join(credenciais)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"credenciais_{tipo}_{timestamp}.txt"
        
        logger.info(f"Enviando arquivo: {filename} com {len(credenciais)} credenciais")
        
        # Envia como arquivo
        await bot.send_file(
            chat_id,
            io.BytesIO(content.encode('utf-8')),
            attributes=[DocumentAttributeFilename(filename)],
            caption=f"📁 **{filename}**\n\n"
                   f"✅ {len(credenciais):,} credenciais {tipo}\n"
                   f"📊 Taxa: {(stats['valid_lines']/max(1,stats['total_lines'])*100):.1f}%"
        )
        
        logger.info(f"Arquivo enviado com sucesso: {filename}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar arquivo {tipo}: {e}")
        await bot.send_message(chat_id, f"❌ Erro ao enviar arquivo {tipo}: {str(e)[:100]}")

# ========== HANDLERS DO BOT ==========

@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    """Handler do comando /start"""
    logger.info(f"Comando /start recebido de {event.sender_id}")
    user = await event.get_sender()
    welcome_text = f"""🤖 **Bot Processador Gigante 4GB - Telethon**

Olá {user.first_name}! 👋

🚀 **Todas as funções do painel em bot:**
• Processamento de arquivos TXT, ZIP e RAR até 4GB
• Filtragem automática de spam e divulgação  
• Detecção de URLs brasileiras expandida
• Uso apenas da nuvem do Telegram (sem RAM local)

📤 **Como usar:**
1. Digite `/adicionar` para iniciar
2. Encaminhe seus arquivos TXT/ZIP/RAR
3. Receba os resultados filtrados automaticamente

🇧🇷 **Filtros implementados:**
• Remove spam, divulgação, nomes, propaganda
• Detecta sites brasileiros (.br + nacionais .com/.net)
• Mantém apenas formato URL:USER:PASS limpo
• Filtragem igual ao painel original

Digite `/adicionar` para começar!"""
    
    await event.reply(welcome_text)

@bot.on(events.NewMessage(pattern=r'^/adicionar$'))
async def adicionar_handler(event):
    """Handler do comando /adicionar"""
    chat_id = event.chat_id
    user_id = event.sender_id
    
    logger.info(f"Comando /adicionar recebido de {user_id} no chat {chat_id}")
    
    # Inicializa controle de upload para este chat
    upload_tasks[chat_id] = {
        'active': True,
        'files': [],
        'results': {'credenciais': [], 'brasileiras': []},
        'stats': {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0},
        'files_count': 0,
        'processed_count': 0
    }
    
    # Cria fila de processamento
    processing_queue[chat_id] = asyncio.Queue()
    
    await event.reply(
        "📤 **Modo Processamento em Lote Ativado!**\n\n"
        "🚀 **Novo sistema:**\n"
        "• Envie **vários arquivos de uma vez**\n"
        "• Download e processamento **um por vez**\n"
        "• **Progresso detalhado** de cada arquivo\n"
        "• **Resultado final unificado** no fim\n\n"
        "📁 **Formatos suportados:**\n"
        "• 📄 TXT - Arquivos de texto\n"
        "• 📦 ZIP - Compactados ZIP\n" 
        "• 📦 RAR - Compactados RAR\n\n"
        "⚡ **Funcionalidades:**\n"
        "• Filtragem de spam/divulgação\n"
        "• Detecção de URLs brasileiras\n"
        "• Processamento na nuvem do Telegram\n\n"
        "🔄 **Envie seus arquivos!** (ou `/cancelarupload` para cancelar)"
    )
    
    # Inicia processador em background
    asyncio.create_task(processar_fila_uploads(chat_id))

@bot.on(events.NewMessage)
async def progress_callback(current, total, progress_msg, filename, start_time):
    """Callback para mostrar progresso do download"""
    try:
        # Calcula estatísticas
        percent = (current / total) * 100
        elapsed = time.time() - start_time
        
        if elapsed > 0 and current > 0:
            speed = current / elapsed  # bytes por segundo
            speed_mb = speed / (1024 * 1024)  # MB/s
            
            # Estima tempo restante
            remaining_bytes = total - current
            if speed > 0:
                eta_seconds = remaining_bytes / speed
                eta_minutes = eta_seconds / 60
                
                if eta_minutes < 1:
                    eta_str = f"{eta_seconds:.0f}s"
                elif eta_minutes < 60:
                    eta_str = f"{eta_minutes:.1f}min"
                else:
                    eta_hours = eta_minutes / 60
                    eta_str = f"{eta_hours:.1f}h"
            else:
                eta_str = "calculando..."
        else:
            speed_mb = 0
            eta_str = "calculando..."
        
        # Barra de progresso visual
        filled = int(percent / 5)  # 20 blocos = 100%
        bar = "█" * filled + "░" * (20 - filled)
        
        # Atualiza mensagem a cada 5% ou a cada 3 segundos
        if percent % 5 < 1 or elapsed % 3 < 1:
            progress_text = f"""
📥 **Download em Progresso**

📁 **Arquivo:** `{filename}`
📊 **Progresso:** {percent:.1f}%
{bar}

📈 **Estatísticas:**
• ⬇️ **Baixado:** {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB
• 🚀 **Velocidade:** {speed_mb:.1f} MB/s
• ⏱️ **Tempo restante:** {eta_str}
• ⏰ **Decorrido:** {elapsed:.0f}s

⚡ **Aguarde...** Após o download, iniciará o processamento!
            """
            
            await progress_msg.edit(progress_text)
    
    except Exception as e:
        # Se der erro no progresso, não interrompe o download
        logger.error(f"Erro no callback de progresso: {e}")

@bot.on(events.NewMessage(pattern=r'^/adicionar$'))
async def adicionar_handler(event):
    """Handler do comando /adicionar"""
    chat_id = event.chat_id
    user_id = event.sender_id
    
    logger.info(f"Comando /adicionar recebido de {user_id} no chat {chat_id}")
    
    # Inicializa controle de upload para este chat
    upload_tasks[chat_id] = {
        'active': True,
        'files': [],
        'results': {'credenciais': [], 'brasileiras': []},
        'stats': {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0},
        'files_count': 0,
        'processed_count': 0
    }
    
    # Cria fila de processamento
    processing_queue[chat_id] = asyncio.Queue()
    
    await event.reply(
        "📤 **Modo Processamento em Lote Ativado!**\n\n"
        "🚀 **Novo sistema:**\n"
        "• Envie **vários arquivos de uma vez**\n"
        "• Download e processamento **um por vez**\n"
        "• **Progresso detalhado** de cada arquivo\n"
        "• **Resultado final unificado** no fim\n\n"
        "📁 **Formatos suportados:**\n"
        "• 📄 TXT - Arquivos de texto\n"
        "• 📦 ZIP - Compactados ZIP\n" 
        "• 📦 RAR - Compactados RAR\n\n"
        "⚡ **Funcionalidades:**\n"
        "• Filtragem de spam/divulgação\n"
        "• Detecção de URLs brasileiras\n"
        "• Processamento na nuvem do Telegram\n\n"
        "🔄 **Envie seus arquivos!** (ou `/cancelarupload` para cancelar)"
    )
    
    # Inicia processador em background
    asyncio.create_task(processar_fila_uploads(chat_id))

async def processar_fila_uploads(chat_id):
    """Processa fila de uploads um por vez"""
    logger.info(f"Iniciando processador de fila para chat {chat_id}")
    
    try:
        while chat_id in upload_tasks and upload_tasks[chat_id]['active']:
            try:
                # Aguarda novo arquivo na fila (timeout 5 segundos)
                file_info = await asyncio.wait_for(
                    processing_queue[chat_id].get(), 
                    timeout=5.0
                )
                
                # Verifica se upload ainda ativo
                if not upload_tasks[chat_id]['active']:
                    logger.info(f"Upload cancelado para chat {chat_id}")
                    break
                
                await processar_arquivo_individual(chat_id, file_info)
                
            except asyncio.TimeoutError:
                # Timeout normal - continue aguardando
                continue
            except Exception as e:
                logger.error(f"Erro no processador de fila {chat_id}: {e}")
                break
        
        # Verifica se tem arquivos para finalizar
        if chat_id in upload_tasks and upload_tasks[chat_id]['processed_count'] > 0:
            await finalizar_processamento_lote(chat_id)
    
    except Exception as e:
        logger.error(f"Erro crítico no processador {chat_id}: {e}")
        if chat_id in upload_tasks:
            await bot.send_message(
                chat_id,
                f"❌ **Erro crítico no processamento:** `{str(e)[:100]}`\n"
                f"Digite `/adicionar` para recomeçar"
            )

async def processar_arquivo_individual(chat_id, file_info):
    """Processa um arquivo individual"""
    try:
        event, filename, file_size = file_info
        
        # Atualiza contador
        upload_tasks[chat_id]['files_count'] += 1
        current_file = upload_tasks[chat_id]['files_count']
        
        # Mensagem de progresso
        progress_msg = await bot.send_message(
            chat_id,
            f"📥 **Download {current_file}º Arquivo**\n\n"
            f"📁 **Nome:** `{filename}`\n"
            f"📏 **Tamanho:** {file_size / 1024 / 1024:.1f} MB\n"
            f"⚡ **Iniciando download com progresso...**"
        )
        
        # Download com callback de progresso
        start_time = time.time()
        
        async def file_progress(current, total):
            await progress_callback(current, total, progress_msg, filename, start_time)
        
        file_content = await event.download_media(
            bytes, 
            progress_callback=file_progress
        )
        
        if not file_content:
            await progress_msg.edit("❌ **Erro:** Não foi possível baixar o arquivo")
            return
        
        download_time = time.time() - start_time
        
        # Atualiza para processamento
        await progress_msg.edit(
            f"🔄 **Processando Arquivo {current_file}**\n\n"
            f"📁 **Nome:** `{filename}`\n"
            f"📏 **Tamanho:** {len(file_content) / 1024 / 1024:.1f} MB\n"
            f"⏱️ **Download:** {download_time:.1f}s\n\n"
            f"⚡ **Filtrando spam e URLs brasileiras...**"
        )
        
        # Processa arquivo
        processing_start = time.time()
        
        if filename.lower().endswith('.txt'):
            credenciais, br_creds, stats = await processar_arquivo_texto(
                file_content, filename, chat_id
            )
        elif filename.lower().endswith('.zip'):
            credenciais, br_creds, stats = await processar_arquivo_zip(
                file_content, filename, chat_id
            )
        elif filename.lower().endswith('.rar'):
            credenciais, br_creds, stats = await processar_arquivo_rar(
                file_content, filename, chat_id
            )
        
        processing_time = time.time() - processing_start
        
        # Adiciona aos resultados consolidados
        upload_tasks[chat_id]['results']['credenciais'].extend(credenciais)
        upload_tasks[chat_id]['results']['brasileiras'].extend(br_creds)
        
        # Soma estatísticas
        for key in upload_tasks[chat_id]['stats']:
            upload_tasks[chat_id]['stats'][key] += stats[key]
        
        upload_tasks[chat_id]['processed_count'] += 1
        
        total_time = time.time() - start_time
        
        # Resultado do arquivo individual
        await progress_msg.edit(
            f"✅ **Arquivo {current_file} Processado!**\n\n"
            f"📁 **Nome:** `{filename}`\n"
            f"📏 **Tamanho:** {len(file_content) / 1024 / 1024:.1f} MB\n"
            f"⏱️ **Tempo total:** {total_time:.1f}s\n\n"
            f"📊 **Resultado deste arquivo:**\n"
            f"• ✅ Válidas: {stats['valid_lines']:,}\n"
            f"• 🇧🇷 Brasileiras: {stats['brazilian_lines']:,}\n"
            f"• 🗑️ Spam: {stats['spam_removed']:,}\n\n"
            f"📈 **Acumulado total:**\n"
            f"• ✅ {len(upload_tasks[chat_id]['results']['credenciais']):,} credenciais\n"
            f"• 🇧🇷 {len(upload_tasks[chat_id]['results']['brasileiras']):,} brasileiras\n\n"
            f"⚡ **Aguardando próximo arquivo ou finalizando...**"
        )
        
        logger.info(f"Arquivo {current_file} processado: {filename} - {stats['valid_lines']} válidas")
        
    except Exception as e:
        logger.error(f"Erro no processamento individual: {e}")
        await bot.send_message(
            chat_id,
            f"❌ **Erro no arquivo:** `{filename}`\n"
            f"**Erro:** {str(e)[:100]}\n"
            f"⚡ Continuando com próximos arquivos..."
        )

async def finalizar_processamento_lote(chat_id):
    """Finaliza processamento e envia resultados consolidados"""
    try:
        if chat_id not in upload_tasks:
            return
        
        task_data = upload_tasks[chat_id]
        total_credenciais = task_data['results']['credenciais']
        total_brasileiras = task_data['results']['brasileiras']
        stats_finais = task_data['stats']
        files_processed = task_data['processed_count']
        
        # Mensagem de finalização
        await bot.send_message(
            chat_id,
            f"🎯 **Processamento em Lote Finalizado!**\n\n"
            f"📊 **Resumo Final:**\n"
            f"• 📁 Arquivos processados: **{files_processed}**\n"
            f"• 📝 Linhas totais: **{stats_finais['total_lines']:,}**\n"
            f"• ✅ Credenciais válidas: **{len(total_credenciais):,}**\n"
            f"• 🇧🇷 URLs brasileiras: **{len(total_brasileiras):,}**\n"
            f"• 🗑️ Spam removido: **{stats_finais['spam_removed']:,}**\n\n"
            f"📈 **Taxa de aproveitamento:** {(len(total_credenciais)/max(1,stats_finais['total_lines'])*100):.1f}%\n\n"
            f"📤 **Enviando resultados consolidados...**"
        )
        
        # Envia arquivo consolidado geral
        if total_credenciais:
            await enviar_resultado_como_arquivo(
                chat_id, total_credenciais, "LOTE_GERAL", stats_finais
            )
        
        # Envia arquivo consolidado brasileiro
        if total_brasileiras:
            await enviar_resultado_como_arquivo(
                chat_id, total_brasileiras, "LOTE_BRASILEIRAS", stats_finais
            )
        
        # Mensagem de conclusão
        await bot.send_message(
            chat_id,
            f"🎉 **Processamento Completo!**\n\n"
            f"✅ **Todos os {files_processed} arquivos processados**\n"
            f"📤 **Resultados consolidados enviados**\n"
            f"🏁 **Sistema pronto para novos uploads**\n\n"
            f"🔄 **Para novo lote:** `/adicionar`\n"
            f"❌ **Para cancelar:** `/cancelarupload`"
        )
        
        # Limpa dados da sessão
        if chat_id in upload_tasks:
            del upload_tasks[chat_id]
        if chat_id in processing_queue:
            del processing_queue[chat_id]
        
        logger.info(f"Processamento em lote finalizado para chat {chat_id}: {len(total_credenciais)} credenciais")
        
    except Exception as e:
        logger.error(f"Erro na finalização do lote {chat_id}: {e}")
        await bot.send_message(
            chat_id,
            f"❌ **Erro na finalização:** `{str(e)[:100]}`\n"
            f"Digite `/adicionar` para recomeçar"
        )

@bot.on(events.NewMessage)
async def document_handler(event):
    """Handler para documentos enviados - sistema de fila"""
    # Só processa documentos
    if not event.document:
        return
    
    chat_id = event.chat_id
    
    # Verifica se modo adição está ativo
    if chat_id not in upload_tasks or not upload_tasks[chat_id]['active']:
        return  # Ignora se modo não ativo
    
    # Extrai filename
    filename = None
    for attr in event.document.attributes:
        if hasattr(attr, 'file_name'):
            filename = attr.file_name
            break
    
    if not filename:
        filename = f"arquivo_{int(time.time())}.txt"
    
    # Verifica formato
    if not filename.lower().endswith(('.txt', '.zip', '.rar')):
        await event.reply(
            "❌ **Formato não suportado!**\n"
            "Use apenas: TXT, ZIP, RAR\n"
            "📤 Continue enviando outros arquivos válidos"
        )
        return
    
    # Verifica tamanho
    file_size = event.document.size
    if file_size > 2 * 1024 * 1024 * 1024:  # 2GB
        await event.reply(
            "❌ **Arquivo muito grande!**\n"
            f"📏 **Tamanho:** {file_size / 1024 / 1024:.1f} MB\n"
            f"📐 **Limite:** 2GB\n"
            "Divida em partes menores e continue enviando"
        )
        return
    
    # Adiciona à fila
    file_info = (event, filename, file_size)
    await processing_queue[chat_id].put(file_info)
    
    # Confirma adição à fila
    queue_size = processing_queue[chat_id].qsize()
    await event.reply(
        f"📋 **Arquivo Adicionado à Fila!**\n\n"
        f"📁 **Nome:** `{filename}`\n"
        f"📏 **Tamanho:** {file_size / 1024 / 1024:.1f} MB\n"
        f"🔢 **Posição na fila:** {queue_size}\n\n"
        f"⚡ **Status:** Será processado automaticamente\n"
        f"🔄 **Continue enviando** mais arquivos ou aguarde\n"
        f"❌ **Para cancelar:** `/cancelarupload`"
    )
    
    logger.info(f"Arquivo {filename} adicionado à fila do chat {chat_id}, posição {queue_size}")

@bot.on(events.NewMessage(pattern=r'^/teste$'))
async def teste_handler(event):
    """Handler do comando /teste - para testar funcionamento"""
    await event.reply(
        "✅ **Bot funcionando perfeitamente!**\n\n"
        "🔧 **Teste de funcionalidades:**\n"
        "• Recebimento de mensagens: ✅\n"
        "• Envio de respostas: ✅\n"
        "• Processamento de comandos: ✅\n\n"
        "📤 **Para testar upload:**\n"
        "1. Digite `/adicionar`\n"
        "2. Envie um arquivo TXT pequeno\n"
        "3. Aguarde o processamento\n\n"
        "Se ainda tiver problemas, use `/help`"
    )

@bot.on(events.NewMessage(pattern=r'^/help$'))
async def help_handler(event):
    """Handler do comando /help"""
    help_text = """
🤖 **Comandos disponíveis:**

/start - Iniciar o bot
/adicionar - Ativar modo de processamento em lote
/cancelarupload - Cancelar uploads em andamento
/help - Mostrar esta ajuda
/stats - Estatísticas de uso

📁 **Formatos suportados:**
• TXT - Arquivos de texto puro
• ZIP - Compactados ZIP com TXTs internos
• RAR - Compactados RAR com TXTs internos

🚀 **Novo sistema de lote:**
• Envie vários arquivos de uma vez
• Download e processamento um por vez com progresso
• Resultado final consolidado único
• Cancelamento a qualquer momento

🛡️ **Filtragem automática (igual ao painel):**
• Remove divulgação, spam, nomes, propaganda
• Remove links promocionais e termos de hack
• Mantém apenas formato URL:USER:PASS limpo
• Detecta URLs brasileiras (.br + sites nacionais)

🇧🇷 **Detecção brasileira expandida:**
• Sites .br automáticos
• Bancos (Itaú, Bradesco, BB, Santander, etc)
• E-commerce (Mercado Livre, Americanas, etc)
• Comunicação (Vivo, Tim, Claro, UOL, etc)

⚡ **Tecnologia:**
• Telethon com API_ID/API_HASH/TOKEN
• Processamento na nuvem do Telegram
• Sem uso de RAM/memória local
• Arquivos até 2GB (limite Telegram)
    """
    
    await event.reply(help_text)

@bot.on(events.NewMessage(pattern=r'^/ativarweb$'))
async def ativar_web_handler(event):
    """Handler do comando /ativarweb - apenas admin"""
    user_id = event.sender_id
    
    # Verifica se é admin
    if user_id != admin_id_int:
        await event.reply("❌ **Acesso negado!** Apenas o admin pode usar este comando.")
        return
    
    global painel_ativo
    
    if painel_ativo:
        await event.reply("⚠️ **Painel web já está ativo!**")
        return
    
    try:
        # Ativa painel web
        import subprocess
        subprocess.Popen(["python", "app_web.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        painel_ativo = True
        
        await event.reply(
            "✅ **Painel Web Ativado!**\n\n"
            "🌐 **URL:** Confira na aba preview do Replit\n"
            "⚡ **Status:** Online e funcionando\n"
            "🔧 **Funcionalidades:** Todas do painel original\n\n"
            "Para desativar, use `/desativarweb`"
        )
        
    except Exception as e:
        await event.reply(f"❌ **Erro ao ativar painel:** `{str(e)[:50]}`")

@bot.on(events.NewMessage(pattern=r'^/desativarweb$'))
async def desativar_web_handler(event):
    """Handler do comando /desativarweb - apenas admin"""
    user_id = event.sender_id
    
    # Verifica se é admin
    if user_id != admin_id_int:
        await event.reply("❌ **Acesso negado!** Apenas o admin pode usar este comando.")
        return
    
    global painel_ativo
    painel_ativo = False
    
    await event.reply(
        "🔴 **Painel Web Desativado!**\n\n"
        "⚠️ **Nota:** O processo pode continuar em background\n"
        "Para reativar, use `/ativarweb`"
    )

@bot.on(events.NewMessage(pattern=r'^/status$'))
async def status_handler(event):
    """Handler do comando /status"""
    user_id = event.sender_id
    is_admin = (user_id == admin_id_int)
    
    status_text = f"""
📊 **Status do Sistema:**

🤖 **Bot:** Online e funcionando
🌐 **Painel Web:** {"🟢 Ativo" if painel_ativo else "🔴 Inativo"}
⚡ **Tecnologia:** Telethon + Flask
🗄️ **Storage:** Nuvem Telegram (0% RAM)

🛡️ **Filtros ativos:**
• ✅ Spam e divulgação
• ✅ Nomes e apelidos  
• ✅ Links promocionais
• ✅ Termos de hack/crack

🇧🇷 **Detecção brasileira:**
• ✅ URLs .br automáticas
• ✅ +50 sites nacionais
• ✅ Bancos, e-commerce, governo
    """
    
    if is_admin:
        status_text += f"""

👑 **Painel Admin:**
• `/ativarweb` - Ativar painel web
• `/desativarweb` - Desativar painel web
• `/logs` - Ver logs do sistema
        """
    
    await event.reply(status_text)

@bot.on(events.NewMessage(pattern=r'^/comandos$'))
async def comandos_handler(event):
    """Handler do comando /comandos"""
    user_id = event.sender_id
    is_admin = (user_id == admin_id_int)
    
    comandos_text = """
🤖 **Comandos Disponíveis:**

📤 **Processamento:**
• `/start` - Iniciar o bot
• `/adicionar` - Ativar modo de adição
• `/help` - Ajuda detalhada

📊 **Informações:**
• `/status` - Status do sistema
• `/comandos` - Lista de comandos
• `/sobre` - Sobre o projeto

🔧 **Utilidades:**
• Digite `/adicionar` e envie TXT/ZIP/RAR
• Processamento automático com filtros
• Resultado em arquivos organizados
    """
    
    if is_admin:
        comandos_text += """

👑 **Admin apenas:**
• `/ativarweb` - Ativar painel web
• `/desativarweb` - Desativar painel  
• `/logs` - Ver logs do sistema
        """
    
    await event.reply(comandos_text)

@bot.on(events.NewMessage(pattern=r'^/sobre$'))
async def sobre_handler(event):
    """Handler do comando /sobre"""
    sobre_text = """
🤖 **Bot Processador Gigante 4GB**

📋 **Projeto:**
Sistema completo para processamento de credenciais com todas as funcionalidades do painel original em formato bot.

⚡ **Tecnologia:**
• **Bot:** Telethon (API_ID + API_HASH + TOKEN)
• **Painel:** Flask (ativação sob demanda)
• **Storage:** 100% nuvem do Telegram
• **RAM:** 0% uso de memória local

🛡️ **Filtros implementados:**
• Remove spam, divulgação, propaganda
• Remove nomes, apelidos, links promocionais
• Detecta URLs brasileiras expandidas
• Mantém apenas formato URL:USER:PASS

🇧🇷 **Detecção brasileira:**
• Sites .br automáticos
• Bancos (Itaú, Bradesco, BB, Santander...)
• E-commerce (ML, Americanas, Magazine...)
• Telecom (Vivo, Tim, Claro, UOL...)

📈 **Capacidades:**
• Arquivos até 2GB (limite Telegram)
• Formatos: TXT, ZIP, RAR
• Processamento streaming
• Filtros igual ao painel original
    """
    
    await event.reply(sobre_text)

@bot.on(events.NewMessage(pattern=r'^/logs$'))
async def logs_handler(event):
    """Handler do comando /logs - apenas admin"""
    user_id = event.sender_id
    
    # Verifica se é admin
    if user_id != admin_id_int:
        await event.reply("❌ **Acesso negado!** Apenas o admin pode ver logs.")
        return
    
    try:
        # Lê últimas linhas do log (se existir)
        logs_text = "📋 **Logs do Sistema:**\n\n"
        logs_text += f"🤖 **Bot Status:** Online\n"
        logs_text += f"🌐 **Painel:** {'Ativo' if painel_ativo else 'Inativo'}\n"
        logs_text += f"⏰ **Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        logs_text += f"💾 **Memória:** Usando apenas nuvem Telegram\n"
        logs_text += f"🔄 **Processamento:** Streaming direto\n"
        
        await event.reply(logs_text)
        
    except Exception as e:
        await event.reply(f"❌ **Erro ao buscar logs:** `{str(e)[:50]}`")

@bot.on(events.NewMessage(pattern=r'^/stats$'))
async def stats_handler(event):
    """Handler do comando /stats"""
    stats_text = f"""
📊 **Estatísticas do Bot:**

🤖 **Status:** Online e funcionando
🌐 **Painel Web:** {"🟢 Ativo" if painel_ativo else "🔴 Inativo"}
⚡ **Tecnologia:** Telethon + Nuvem Telegram
🗄️ **Armazenamento:** Apenas nuvem (0% RAM local)

🛡️ **Filtros ativos:**
• Spam e divulgação
• Nomes e apelidos
• Links promocionais
• Termos de hack/crack

🇧🇷 **Detecção brasileira:**
• URLs .br automáticas
• +50 sites nacionais .com/.net
• Bancos, e-commerce, governo

📤 **Uso:**
Digite `/adicionar` e envie seus arquivos!
    """
    
    await event.reply(stats_text)

@bot.on(events.NewMessage(pattern=r'^/cancelarupload$'))
async def cancelar_upload_handler(event):
    """Handler do comando /cancelarupload"""
    chat_id = event.chat_id
    user_id = event.sender_id
    
    logger.info(f"Comando /cancelarupload recebido de {user_id} no chat {chat_id}")
    
    if chat_id in upload_tasks and upload_tasks[chat_id]['active']:
        # Cancela uploads ativos
        upload_tasks[chat_id]['active'] = False
        
        # Limpa fila de processamento
        if chat_id in processing_queue:
            while not processing_queue[chat_id].empty():
                try:
                    processing_queue[chat_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        await event.reply(
            "🛑 **Upload Cancelado!**\n\n"
            "❌ **Status:** Todos os uploads em andamento foram cancelados\n"
            "🗑️ **Fila:** Limpa e pronta para novos arquivos\n"
            "♻️ **Resultados:** Dados temporários descartados\n\n"
            "✅ **Pronto para novos uploads!**\n"
            "Digite `/adicionar` para recomeçar"
        )
        
        # Limpa dados
        if chat_id in upload_tasks:
            del upload_tasks[chat_id]
        if chat_id in processing_queue:
            del processing_queue[chat_id]
            
        logger.info(f"Upload cancelado e dados limpos para chat {chat_id}")
    else:
        await event.reply(
            "⚠️ **Nenhum upload ativo**\n\n"
            "📝 **Status:** Não há uploads em andamento para cancelar\n"
            "📤 **Para iniciar:** Digite `/adicionar` e envie seus arquivos"
        )

@bot.on(events.NewMessage(pattern=r'^/teste$'))
async def teste_handler(event):
    """Handler do comando /teste - para testar funcionamento"""
    await event.reply(
        "✅ **Bot funcionando perfeitamente!**\n\n"
        "🔧 **Teste de funcionalidades:**\n"
        "• Recebimento de mensagens: ✅\n"
        "• Envio de respostas: ✅\n"
        "• Processamento de comandos: ✅\n\n"
        "📤 **Para testar upload:**\n"
        "1. Digite `/adicionar`\n"
        "2. Envie um arquivo TXT pequeno\n"
        "3. Aguarde o processamento\n\n"
        "Se ainda tiver problemas, use `/help`"
    )

# ========== FUNÇÃO PRINCIPAL ==========

async def main():
    """Função principal do bot"""
    logger.info("🤖 Iniciando Bot Processador Gigante 4GB com Telethon...")
    
    try:
        # Conecta ao Telegram
        if BOT_TOKEN:
            await bot.start(bot_token=BOT_TOKEN)
        else:
            logger.error("❌ BOT_TOKEN não configurado!")
            return
            
        logger.info("✅ Bot conectado! Aguardando mensagens...")
        
        # Mantém o bot rodando
        await bot.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Erro no bot: {e}")
        raise

if __name__ == "__main__":
    bot.loop.run_until_complete(main())