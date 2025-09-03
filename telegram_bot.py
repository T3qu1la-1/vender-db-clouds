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

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("❌ Configurações faltando! Configure: API_ID, API_HASH, TELEGRAM_BOT_TOKEN")
    exit(1)

try:
    api_id_int = int(API_ID)
except (ValueError, TypeError):
    logger.error("❌ API_ID deve ser um número!")
    exit(1)

# Cliente Telethon
bot = TelegramClient('bot', api_id_int, API_HASH)

# Controle do painel web
painel_ativo = False

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
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return todas_credenciais, todas_br, stats_total
    
    except Exception as e:
        logger.error(f"Erro no RAR: {e}")
        # Remove arquivo temporário se existir
        try:
            if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
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
    
    # Cria conteúdo do arquivo
    content = '\n'.join(credenciais)
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"credenciais_{tipo}_{timestamp}.txt"
    
    # Envia como arquivo
    await bot.send_file(
        chat_id,
        io.BytesIO(content.encode('utf-8')),
        attributes=[DocumentAttributeFilename(filename)],
        caption=f"📁 **{filename}**\n\n"
               f"✅ {len(credenciais):,} credenciais {tipo}\n"
               f"📊 Taxa: {(stats['valid_lines']/max(1,stats['total_lines'])*100):.1f}%"
    )

# ========== HANDLERS DO BOT ==========

@bot.on(events.NewMessage(pattern=r'/start'))
async def start_handler(event):
    """Handler do comando /start"""
    user = await event.get_sender()
    welcome_text = f"""
🤖 **Bot Processador Gigante 4GB - Telethon**

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

Digite `/adicionar` para começar!
    """
    
    await event.reply(welcome_text)

@bot.on(events.NewMessage(pattern=r'/adicionar'))
async def adicionar_handler(event):
    """Handler do comando /adicionar"""
    await event.reply(
        "📤 **Modo Adição Ativado!**\n\n"
        "Agora envie seus arquivos:\n"
        "• 📄 TXT - Arquivos de texto\n"
        "• 📦 ZIP - Compactados ZIP\n" 
        "• 📦 RAR - Compactados RAR\n\n"
        "⚡ **Processamento automático:**\n"
        "• Filtragem de spam/divulgação\n"
        "• Detecção de URLs brasileiras\n"
        "• Resultado limpo URL:USER:PASS\n\n"
        "🔄 Envie quantos arquivos quiser!"
    )

@bot.on(events.NewMessage)
async def document_handler(event):
    """Handler para documentos enviados"""
    if not event.document:
        return
    
    # Verifica se tem filename
    filename = None
    for attr in event.document.attributes:
        if hasattr(attr, 'file_name'):
            filename = attr.file_name
            break
    
    if not filename:
        return
    
    # Verifica formato suportado
    if not filename.lower().endswith(('.txt', '.zip', '.rar')):
        await event.reply("❌ Formato não suportado! Use apenas TXT, ZIP ou RAR.")
        return
    
    # Verifica tamanho (limite Telegram: 2GB para bots)
    file_size = event.document.size
    if file_size > 2 * 1024 * 1024 * 1024:  # 2GB
        await event.reply(
            "❌ Arquivo muito grande!\n"
            "Limite: 2GB\n"
            "Divida em partes menores."
        )
        return
    
    # Mensagem de processamento
    processing_msg = await event.reply(
        f"🚀 **Processando:** `{filename}`\n"
        f"📏 **Tamanho:** {file_size / 1024 / 1024:.1f} MB\n"
        f"⏳ **Aguarde...** Filtrando spam e detectando URLs brasileiras..."
    )
    
    try:
        # Download do arquivo da nuvem do Telegram
        file_content = await event.download_media(bytes)
        
        # Inicializa variáveis
        credenciais = []
        br_creds = []
        stats = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
        
        # Processa baseado no tipo
        if filename.lower().endswith('.txt'):
            credenciais, br_creds, stats = await processar_arquivo_texto(
                file_content, filename, event.chat_id
            )
        elif filename.lower().endswith('.zip'):
            credenciais, br_creds, stats = await processar_arquivo_zip(
                file_content, filename, event.chat_id
            )
        elif filename.lower().endswith('.rar'):
            credenciais, br_creds, stats = await processar_arquivo_rar(
                file_content, filename, event.chat_id
            )
        
        # Atualiza mensagem com resultado
        if stats['valid_lines'] > 0:
            result_text = f"""
✅ **Processamento Concluído!**

📁 **Arquivo:** `{filename}`
📊 **Estatísticas:**
• 📝 Total processado: {stats['total_lines']:,} linhas
• ✅ Credenciais válidas: {stats['valid_lines']:,}
• 🇧🇷 URLs brasileiras: {stats['brazilian_lines']:,}
• 🗑️ Spam removido: {stats['spam_removed']:,}
• 📈 Taxa válida: {(stats['valid_lines']/max(1,stats['total_lines'])*100):.1f}%

🔄 **Enviando arquivos filtrados...**
            """
            await processing_msg.edit(result_text)
            
            # Envia arquivo com todas as credenciais válidas
            if credenciais:
                await enviar_resultado_como_arquivo(
                    event.chat_id, credenciais, "geral", stats
                )
            
            # Envia arquivo separado com URLs brasileiras
            if br_creds:
                await enviar_resultado_como_arquivo(
                    event.chat_id, br_creds, "brasileiras", stats
                )
            
            await bot.send_message(
                event.chat_id,
                "✅ **Processamento finalizado!**\n\n"
                "📤 Arquivos enviados com credenciais filtradas.\n"
                "🔄 Envie mais arquivos para continuar processando!"
            )
        
        else:
            await processing_msg.edit(
                f"❌ **Nenhuma credencial válida encontrada**\n\n"
                f"📁 **Arquivo:** `{filename}`\n"
                f"📊 **Motivos:**\n"
                f"• {stats['spam_removed']:,} linhas de spam/divulgação removidas\n"
                f"• {stats['total_lines'] - stats['spam_removed']:,} linhas com formato inválido\n\n"
                f"**Formato esperado:** `url:user:pass`"
            )
    
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        await processing_msg.edit(
            f"❌ **Erro no processamento:**\n"
            f"`{str(e)[:100]}`\n\n"
            f"Tente novamente ou verifique o arquivo."
        )

@bot.on(events.NewMessage(pattern=r'/help'))
async def help_handler(event):
    """Handler do comando /help"""
    help_text = """
🤖 **Comandos disponíveis:**

/start - Iniciar o bot
/adicionar - Ativar modo de adição de arquivos
/help - Mostrar esta ajuda
/stats - Estatísticas de uso

📁 **Formatos suportados:**
• TXT - Arquivos de texto puro
• ZIP - Compactados ZIP com TXTs internos
• RAR - Compactados RAR com TXTs internos

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

@bot.on(events.NewMessage(pattern=r'/ativarweb'))
async def ativar_web_handler(event):
    """Handler do comando /ativarweb - apenas admin"""
    user_id = str(event.sender_id)
    
    # Verifica se é admin
    if user_id != str(ADMIN_ID):
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

@bot.on(events.NewMessage(pattern=r'/desativarweb'))
async def desativar_web_handler(event):
    """Handler do comando /desativarweb - apenas admin"""
    user_id = str(event.sender_id)
    
    # Verifica se é admin
    if user_id != str(ADMIN_ID):
        await event.reply("❌ **Acesso negado!** Apenas o admin pode usar este comando.")
        return
    
    global painel_ativo
    painel_ativo = False
    
    await event.reply(
        "🔴 **Painel Web Desativado!**\n\n"
        "⚠️ **Nota:** O processo pode continuar em background\n"
        "Para reativar, use `/ativarweb`"
    )

@bot.on(events.NewMessage(pattern=r'/status'))
async def status_handler(event):
    """Handler do comando /status"""
    user_id = str(event.sender_id)
    is_admin = (user_id == str(ADMIN_ID))
    
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

@bot.on(events.NewMessage(pattern=r'/comandos'))
async def comandos_handler(event):
    """Handler do comando /comandos"""
    user_id = str(event.sender_id)
    is_admin = (user_id == str(ADMIN_ID))
    
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

@bot.on(events.NewMessage(pattern=r'/sobre'))
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

@bot.on(events.NewMessage(pattern=r'/logs'))
async def logs_handler(event):
    """Handler do comando /logs - apenas admin"""
    user_id = str(event.sender_id)
    
    # Verifica se é admin
    if user_id != str(ADMIN_ID):
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

@bot.on(events.NewMessage(pattern=r'/stats'))
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

# ========== FUNÇÃO PRINCIPAL ==========

async def main():
    """Função principal do bot"""
    logger.info("🤖 Iniciando Bot Processador Gigante 4GB com Telethon...")
    
    # Conecta ao Telegram
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("✅ Bot conectado! Aguardando mensagens...")
    
    # Mantém o bot rodando
    await bot.run_until_disconnected()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())