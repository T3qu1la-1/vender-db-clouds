#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 CloudBR Terminal - Sistema de Processamento de Credenciais
Versão Console/Terminal com interface interativa em português
Processa arquivos TXT/ZIP/RAR até 4GB
"""

import os
import sys
import re
import zipfile
import rarfile
import sqlite3
import time
from datetime import datetime
from collections import defaultdict
import subprocess

# ========== CONFIGURAÇÕES ==========

# URLs brasileiras para detecção
DOMINIOS_BRASILEIROS = {
    '.com.br', '.br', '.org.br', '.net.br', '.gov.br', '.edu.br',
    '.mil.br', '.art.br', '.adv.br', '.blog.br', '.eco.br', '.emp.br',
    '.eng.br', '.esp.br', '.etc.br', '.far.br', '.flog.br', '.fnd.br',
    '.fot.br', '.fst.br', '.g12.br', '.geo.br', '.ggf.br', '.imb.br',
    '.ind.br', '.inf.br', '.jor.br', '.jus.br', '.lel.br', '.mat.br',
    '.med.br', '.mp.br', '.mus.br', '.nom.br', '.not.br', '.ntr.br',
    '.odo.br', '.ppg.br', '.pro.br', '.psc.br', '.psi.br', '.qsl.br',
    '.radio.br', '.rec.br', '.slg.br', '.srv.br', '.taxi.br', '.teo.br',
    '.tmp.br', '.trd.br', '.tur.br', '.tv.br', '.vet.br', '.vlog.br',
    '.wiki.br', '.zlg.br'
}

# Sites brasileiros conhecidos (.com/.net)
SITES_BRASILEIROS = {
    'uol.com', 'globo.com', 'terra.com', 'ig.com', 'r7.com', 'band.com',
    'sbt.com', 'record.com', 'folha.com', 'estadao.com', 'veja.com',
    'abril.com', 'editora.com', 'saraiva.com', 'americanas.com',
    'submarino.com', 'magazineluiza.com', 'casasbahia.com', 'extra.com',
    'pontofrio.com', 'fastshop.com', 'walmart.com', 'carrefour.com',
    'paodelacucar.com', 'mercadolivre.com', 'olx.com', 'webmotors.com',
    'imovelweb.com', 'zapimoveis.com', 'vivareal.com', 'netshoes.com',
    'centauro.com', 'nike.com', 'adidas.com', 'puma.com', 'decathlon.com'
}

# ========== FUNÇÕES AUXILIARES ==========

def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    """Mostra o banner principal"""
    print("=" * 70)
    print("🚀 CloudBR Terminal - Sistema de Processamento de Credenciais")
    print("=" * 70)
    print("📁 Processa arquivos TXT/ZIP/RAR até 4GB")
    print("🇧🇷 Filtro automático para URLs brasileiras")
    print("⚡ Interface de terminal interativa")
    print("=" * 70)
    print()

def aguardar_enter():
    """Aguarda o usuário pressionar Enter"""
    input("\n📥 Pressione ENTER para continuar...")

def is_brazilian_url(url):
    """Verifica se uma URL é brasileira"""
    url_lower = url.lower()
    
    # Verifica domínios .br
    for dominio in DOMINIOS_BRASILEIROS:
        if dominio in url_lower:
            return True
    
    # Verifica sites brasileiros conhecidos
    for site in SITES_BRASILEIROS:
        if site in url_lower:
            return True
    
    return False

def validar_credencial(linha):
    """Valida se uma linha contém credencial no formato email:senha ou user:senha"""
    linha = linha.strip()
    
    # Remove linhas muito curtas ou muito longas
    if len(linha) < 5 or len(linha) > 500:
        return False
    
    # Remove spam comum
    spam_patterns = [
        r'\*{10,}', r'={10,}', r'-{10,}', r'_{10,}',
        r'WOLF', r'CRACKED', r'HACKED', r'FREE',
        r'TELEGRAM', r'DISCORD', r'@', r'#',
        r'https?://', r'www\.', r'\.exe', r'\.zip'
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, linha, re.IGNORECASE):
            return False
    
    # Verifica formato email:senha ou user:senha
    if ':' not in linha:
        return False
    
    partes = linha.split(':')
    if len(partes) != 2:
        return False
    
    usuario, senha = partes
    
    # Valida usuário (email ou username)
    if len(usuario) < 3 or len(senha) < 3:
        return False
    
    # Se contém @, valida como email
    if '@' in usuario:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, usuario):
            return False
    
    return True

def processar_arquivo_txt(arquivo_path):
    """Processa arquivo TXT"""
    credenciais = []
    brasileiras = []
    stats = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
    
    try:
        with open(arquivo_path, 'r', encoding='utf-8', errors='ignore') as f:
            for linha in f:
                stats['total_lines'] += 1
                linha = linha.strip()
                
                if validar_credencial(linha):
                    credenciais.append(linha)
                    stats['valid_lines'] += 1
                    
                    # Verifica se é brasileira
                    if is_brazilian_url(linha):
                        brasileiras.append(linha)
                        stats['brazilian_lines'] += 1
                else:
                    stats['spam_removed'] += 1
    
    except Exception as e:
        print(f"❌ Erro ao processar {arquivo_path}: {e}")
        return [], [], stats
    
    return credenciais, brasileiras, stats

def processar_arquivo_zip(arquivo_path):
    """Processa arquivo ZIP"""
    todas_credenciais = []
    todas_brasileiras = []
    stats_total = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
    
    try:
        with zipfile.ZipFile(arquivo_path, 'r') as zip_file:
            for nome_arquivo in zip_file.namelist():
                if nome_arquivo.lower().endswith('.txt'):
                    print(f"  📄 Processando: {nome_arquivo}")
                    
                    try:
                        with zip_file.open(nome_arquivo) as txt_file:
                            content = txt_file.read().decode('utf-8', errors='ignore')
                            
                            for linha in content.split('\n'):
                                stats_total['total_lines'] += 1
                                linha = linha.strip()
                                
                                if validar_credencial(linha):
                                    todas_credenciais.append(linha)
                                    stats_total['valid_lines'] += 1
                                    
                                    if is_brazilian_url(linha):
                                        todas_brasileiras.append(linha)
                                        stats_total['brazilian_lines'] += 1
                                else:
                                    stats_total['spam_removed'] += 1
                    
                    except Exception as e:
                        print(f"    ⚠️ Erro no arquivo {nome_arquivo}: {e}")
    
    except Exception as e:
        print(f"❌ Erro ao processar ZIP {arquivo_path}: {e}")
    
    return todas_credenciais, todas_brasileiras, stats_total

def processar_arquivo_rar(arquivo_path):
    """Processa arquivo RAR"""
    todas_credenciais = []
    todas_brasileiras = []
    stats_total = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
    
    try:
        with rarfile.RarFile(arquivo_path, 'r') as rar_file:
            for nome_arquivo in rar_file.namelist():
                if nome_arquivo.lower().endswith('.txt'):
                    print(f"  📄 Processando: {nome_arquivo}")
                    
                    try:
                        with rar_file.open(nome_arquivo) as txt_file:
                            content = txt_file.read().decode('utf-8', errors='ignore')
                            
                            for linha in content.split('\n'):
                                stats_total['total_lines'] += 1
                                linha = linha.strip()
                                
                                if validar_credencial(linha):
                                    todas_credenciais.append(linha)
                                    stats_total['valid_lines'] += 1
                                    
                                    if is_brazilian_url(linha):
                                        todas_brasileiras.append(linha)
                                        stats_total['brazilian_lines'] += 1
                                else:
                                    stats_total['spam_removed'] += 1
                    
                    except Exception as e:
                        print(f"    ⚠️ Erro no arquivo {nome_arquivo}: {e}")
    
    except Exception as e:
        print(f"❌ Erro ao processar RAR {arquivo_path}: {e}")
    
    return todas_credenciais, todas_brasileiras, stats_total

def gerar_nome_arquivo(nome_original, tipo="geral"):
    """Gera nome bonito para o arquivo de saída"""
    timestamp = datetime.now().strftime("%d.%m.%Y")
    nome_base = os.path.splitext(nome_original)[0]
    
    if tipo == "brasileiras":
        return f"cloudbr-{nome_base}-BR-{timestamp}.txt"
    else:
        return f"cloudbr-{nome_base}-GERAL-{timestamp}.txt"

def salvar_resultado(credenciais, nome_arquivo):
    """Salva resultado em arquivo"""
    if not credenciais:
        return False
    
    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            for credencial in credenciais:
                f.write(credencial + '\n')
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar {nome_arquivo}: {e}")
        return False

def listar_arquivos():
    """Lista arquivos TXT, ZIP e RAR na pasta atual"""
    arquivos = []
    
    for arquivo in os.listdir('.'):
        if arquivo.lower().endswith(('.txt', '.zip', '.rar')):
            tamanho = os.path.getsize(arquivo)
            arquivos.append({
                'nome': arquivo,
                'tamanho': tamanho,
                'tamanho_mb': tamanho / (1024 * 1024)
            })
    
    return sorted(arquivos, key=lambda x: x['nome'])

def mostrar_menu_principal():
    """Mostra o menu principal"""
    limpar_tela()
    mostrar_banner()
    
    print("🎯 MENU PRINCIPAL:")
    print()
    print("1️⃣  Processar arquivos da pasta atual")
    print("2️⃣  Iniciar painel web (Flask)")
    print("3️⃣  Iniciar bot do Telegram")
    print("4️⃣  Ver arquivos na pasta")
    print("5️⃣  Ajuda e instruções")
    print("6️⃣  Sair")
    print()
    print("=" * 70)

def mostrar_menu_processamento(arquivos):
    """Mostra menu de processamento de arquivos"""
    limpar_tela()
    print("📁 ARQUIVOS ENCONTRADOS:")
    print("=" * 70)
    
    if not arquivos:
        print("❌ Nenhum arquivo TXT/ZIP/RAR encontrado na pasta atual!")
        print()
        print("💡 Coloque seus arquivos na pasta e tente novamente.")
        return []
    
    for i, arquivo in enumerate(arquivos, 1):
        print(f"{i:2d}. 📄 {arquivo['nome']} ({arquivo['tamanho_mb']:.1f} MB)")
    
    print()
    print("0️⃣  Processar TODOS os arquivos")
    print("🔙 Voltar ao menu principal (digite 'v')")
    print("=" * 70)
    
    return arquivos

def processar_arquivo_escolhido(arquivo):
    """Processa um arquivo específico"""
    nome = arquivo['nome']
    print(f"\n🚀 Processando: {nome}")
    print("=" * 50)
    
    start_time = time.time()
    
    # Determina tipo do arquivo e processa
    if nome.lower().endswith('.txt'):
        credenciais, brasileiras, stats = processar_arquivo_txt(nome)
    elif nome.lower().endswith('.zip'):
        credenciais, brasileiras, stats = processar_arquivo_zip(nome)
    elif nome.lower().endswith('.rar'):
        credenciais, brasileiras, stats = processar_arquivo_rar(nome)
    else:
        print("❌ Formato de arquivo não suportado!")
        return
    
    tempo_processamento = time.time() - start_time
    
    # Mostra estatísticas
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"📝 Linhas totais: {stats['total_lines']:,}")
    print(f"✅ Credenciais válidas: {len(credenciais):,}")
    print(f"🇧🇷 URLs brasileiras: {len(brasileiras):,}")
    print(f"🗑️ Spam removido: {stats['spam_removed']:,}")
    print(f"⏱️ Tempo: {tempo_processamento:.1f}s")
    
    if len(credenciais) > 0:
        taxa = (len(credenciais) / stats['total_lines']) * 100
        print(f"📈 Taxa de sucesso: {taxa:.1f}%")
    
    # Salva resultados
    if credenciais:
        nome_geral = gerar_nome_arquivo(nome, "geral")
        if salvar_resultado(credenciais, nome_geral):
            print(f"\n✅ Arquivo geral salvo: {nome_geral}")
    
    if brasileiras:
        nome_br = gerar_nome_arquivo(nome, "brasileiras")
        if salvar_resultado(brasileiras, nome_br):
            print(f"✅ Arquivo brasileiro salvo: {nome_br}")
    
    if not credenciais:
        print("\n❌ Nenhuma credencial válida encontrada!")

def processar_todos_arquivos(arquivos):
    """Processa todos os arquivos da lista"""
    print(f"\n🚀 PROCESSAMENTO EM LOTE - {len(arquivos)} arquivo(s)")
    print("=" * 70)
    
    todas_credenciais = []
    todas_brasileiras = []
    stats_total = {'total_lines': 0, 'valid_lines': 0, 'brazilian_lines': 0, 'spam_removed': 0}
    
    start_time = time.time()
    
    for i, arquivo in enumerate(arquivos, 1):
        nome = arquivo['nome']
        print(f"\n📁 [{i}/{len(arquivos)}] Processando: {nome}")
        
        # Processa baseado na extensão
        if nome.lower().endswith('.txt'):
            creds, brs, stats = processar_arquivo_txt(nome)
        elif nome.lower().endswith('.zip'):
            creds, brs, stats = processar_arquivo_zip(nome)
        elif nome.lower().endswith('.rar'):
            creds, brs, stats = processar_arquivo_rar(nome)
        else:
            continue
        
        # Adiciona aos totais
        todas_credenciais.extend(creds)
        todas_brasileiras.extend(brs)
        
        # Soma estatísticas
        for key in stats_total:
            stats_total[key] += stats[key]
        
        print(f"  ✅ {len(creds):,} válidas, {len(brs):,} brasileiras")
    
    tempo_total = time.time() - start_time
    
    # Remove duplicatas
    credenciais_unicas = list(set(todas_credenciais))
    brasileiras_unicas = list(set(todas_brasileiras))
    
    # Mostra resumo final
    print("\n" + "=" * 70)
    print("🎯 RESUMO FINAL DO LOTE:")
    print("=" * 70)
    print(f"📁 Arquivos processados: {len(arquivos)}")
    print(f"📝 Linhas totais: {stats_total['total_lines']:,}")
    print(f"✅ Credenciais válidas: {len(credenciais_unicas):,}")
    print(f"🇧🇷 URLs brasileiras: {len(brasileiras_unicas):,}")
    print(f"🗑️ Spam removido: {stats_total['spam_removed']:,}")
    print(f"⏱️ Tempo total: {tempo_total:.1f}s")
    
    if len(credenciais_unicas) > 0:
        taxa = (len(credenciais_unicas) / stats_total['total_lines']) * 100
        print(f"📈 Taxa de sucesso: {taxa:.1f}%")
    
    # Salva resultados consolidados
    timestamp = datetime.now().strftime("%d.%m.%Y-%H%M")
    
    if credenciais_unicas:
        nome_geral = f"cloudbr-LOTE-GERAL-{timestamp}.txt"
        if salvar_resultado(credenciais_unicas, nome_geral):
            print(f"\n✅ Arquivo geral consolidado: {nome_geral}")
    
    if brasileiras_unicas:
        nome_br = f"cloudbr-LOTE-BR-{timestamp}.txt"
        if salvar_resultado(brasileiras_unicas, nome_br):
            print(f"✅ Arquivo brasileiro consolidado: {nome_br}")
    
    if not credenciais_unicas:
        print("\n❌ Nenhuma credencial válida encontrada em nenhum arquivo!")

def mostrar_ajuda():
    """Mostra instruções de uso"""
    limpar_tela()
    print("📖 AJUDA E INSTRUÇÕES:")
    print("=" * 70)
    print()
    print("🎯 COMO USAR:")
    print("1. Coloque seus arquivos TXT/ZIP/RAR na pasta do script")
    print("2. Execute o script: python terminal.py")
    print("3. Escolha uma opção do menu")
    print("4. Os resultados serão salvos na mesma pasta")
    print()
    print("📁 FORMATOS SUPORTADOS:")
    print("• Arquivos TXT com credenciais (email:senha ou user:senha)")
    print("• Arquivos ZIP contendo TXTs")
    print("• Arquivos RAR contendo TXTs")
    print("• Tamanho máximo: 4GB por arquivo")
    print()
    print("🇧🇷 FILTRO BRASILEIRO:")
    print("• Detecta automaticamente URLs .br")
    print("• Sites brasileiros conhecidos (.com/.net)")
    print("• Gera arquivo separado com credenciais brasileiras")
    print()
    print("📤 ARQUIVOS DE SAÍDA:")
    print("• cloudbr-[nome]-GERAL-[data].txt - Todas as credenciais válidas")
    print("• cloudbr-[nome]-BR-[data].txt - Apenas URLs brasileiras")
    print("• cloudbr-LOTE-[tipo]-[data-hora].txt - Processamento em lote")
    print()
    print("⚡ OUTRAS VERSÕES:")
    print("• Painel Web: python app_web.py (porta 5000)")
    print("• Bot Telegram: python telegram_bot.py")
    print("=" * 70)

def iniciar_painel_web():
    """Inicia o painel web Flask"""
    print("\n🌐 Iniciando painel web Flask...")
    print("🔗 Acesse: http://localhost:5000")
    print("⚠️ Pressione Ctrl+C para parar")
    
    try:
        subprocess.run([sys.executable, 'app_web.py'])
    except KeyboardInterrupt:
        print("\n✅ Painel web parado.")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar painel web: {e}")

def iniciar_bot_telegram():
    """Inicia o bot do Telegram"""
    print("\n🤖 Iniciando bot do Telegram...")
    print("⚠️ Pressione Ctrl+C para parar")
    
    try:
        subprocess.run([sys.executable, 'telegram_bot.py'])
    except KeyboardInterrupt:
        print("\n✅ Bot do Telegram parado.")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar bot: {e}")

# ========== FUNÇÃO PRINCIPAL ==========

def main():
    """Função principal do programa"""
    while True:
        mostrar_menu_principal()
        
        try:
            opcao = input("🎯 Escolha uma opção (1-6): ").strip()
            
            if opcao == '1':
                # Processar arquivos
                arquivos = listar_arquivos()
                arquivos_menu = mostrar_menu_processamento(arquivos)
                
                if not arquivos_menu:
                    aguardar_enter()
                    continue
                
                escolha = input("\n🎯 Escolha um arquivo (número) ou 0 para todos: ").strip()
                
                if escolha.lower() == 'v':
                    continue
                
                try:
                    if escolha == '0':
                        processar_todos_arquivos(arquivos)
                    else:
                        indice = int(escolha) - 1
                        if 0 <= indice < len(arquivos):
                            processar_arquivo_escolhido(arquivos[indice])
                        else:
                            print("❌ Opção inválida!")
                except ValueError:
                    print("❌ Digite um número válido!")
                
                aguardar_enter()
            
            elif opcao == '2':
                # Painel web
                iniciar_painel_web()
                aguardar_enter()
            
            elif opcao == '3':
                # Bot Telegram
                iniciar_bot_telegram()
                aguardar_enter()
            
            elif opcao == '4':
                # Ver arquivos
                arquivos = listar_arquivos()
                limpar_tela()
                print("📁 ARQUIVOS NA PASTA ATUAL:")
                print("=" * 70)
                
                if arquivos:
                    for arquivo in arquivos:
                        print(f"📄 {arquivo['nome']} - {arquivo['tamanho_mb']:.1f} MB")
                else:
                    print("❌ Nenhum arquivo TXT/ZIP/RAR encontrado!")
                
                aguardar_enter()
            
            elif opcao == '5':
                # Ajuda
                mostrar_ajuda()
                aguardar_enter()
            
            elif opcao == '6':
                # Sair
                limpar_tela()
                print("👋 Obrigado por usar o CloudBR Terminal!")
                print("🚀 Sistema encerrado com sucesso.")
                break
            
            else:
                print("❌ Opção inválida! Digite um número de 1 a 6.")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n👋 Saindo do programa...")
            break
        except Exception as e:
            print(f"\n❌ Erro inesperado: {e}")
            aguardar_enter()

if __name__ == "__main__":
    main()