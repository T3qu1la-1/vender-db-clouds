#!/bin/bash
# -*- coding: utf-8 -*-
"""
🚀 CloudBR - Script de Inicialização
Inicia o sistema CloudBR Terminal com menu interativo
"""

clear

echo "=================================================================="
echo "🚀 CloudBR - Sistema de Processamento de Credenciais"
echo "=================================================================="
echo "📁 Processa arquivos TXT/ZIP/RAR até 4GB"
echo "🇧🇷 Filtro automático para URLs brasileiras" 
echo "⚡ 3 versões: Terminal, Web e Telegram Bot"
echo "=================================================================="
echo ""

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado!"
    echo "💡 Instale o Python 3 para continuar"
    echo ""
    exit 1
fi

# Verifica se as dependências estão instaladas
echo "🔍 Verificando dependências..."

# Lista de pacotes necessários
PACOTES=("flask" "rarfile" "requests")
FALTANDO=()

for pacote in "${PACOTES[@]}"; do
    if ! python3 -c "import $pacote" &> /dev/null; then
        FALTANDO+=("$pacote")
    fi
done

# Instala pacotes em falta
if [ ${#FALTANDO[@]} -gt 0 ]; then
    echo "📦 Instalando dependências em falta: ${FALTANDO[*]}"
    pip3 install "${FALTANDO[@]}"
    echo ""
fi

# Verifica se os arquivos principais existem
ARQUIVOS=("terminal.py" "app_web.py")
for arquivo in "${ARQUIVOS[@]}"; do
    if [ ! -f "$arquivo" ]; then
        echo "❌ Arquivo $arquivo não encontrado!"
        echo "💡 Certifique-se de que todos os arquivos estão na pasta"
        echo ""
        exit 1
    fi
done

echo "✅ Dependências verificadas!"
echo ""

# Menu de inicialização
echo "🎯 Escolha como iniciar:"
echo ""
echo "1️⃣  Terminal Interativo (Recomendado)"
echo "2️⃣  Painel Web (localhost:5000)"
echo "3️⃣  Bot do Telegram"
echo "4️⃣  Mostrar ajuda"
echo ""

read -p "🎯 Escolha uma opção (1-4): " opcao

echo ""

case $opcao in
    1)
        echo "🚀 Iniciando CloudBR Terminal..."
        echo "💡 Use Ctrl+C para sair a qualquer momento"
        echo ""
        python3 terminal.py
        ;;
    2)
        echo "🌐 Iniciando Painel Web..."
        echo "🔗 Acesse: http://localhost:5000"
        echo "💡 Use Ctrl+C para parar o servidor"
        echo ""
        python3 app_web.py
        ;;
    3)
        echo "🤖 Iniciando Bot do Telegram..."
        echo "💡 Use Ctrl+C para parar o bot"
        echo ""
        python3 telegram_bot.py
        ;;
    4)
        echo "📖 AJUDA - CloudBR Sistema:"
        echo "=================================================================="
        echo ""
        echo "🎯 VERSÕES DISPONÍVEIS:"
        echo ""
        echo "🖥️  TERMINAL (terminal.py):"
        echo "    • Interface de menu interativo no terminal"
        echo "    • Processa arquivos da pasta local"
        echo "    • Ideal para uso offline e processamento em lote"
        echo ""
        echo "🌐 PAINEL WEB (app_web.py):"
        echo "    • Interface web moderna no navegador"
        echo "    • Upload de arquivos até 4GB"
        echo "    • Acesso via http://localhost:5000"
        echo ""
        echo "🤖 BOT TELEGRAM (telegram_bot.py):"
        echo "    • Bot automatizado no Telegram"
        echo "    • Processa arquivos enviados no chat"
        echo "    • Resultado enviado como arquivos"
        echo ""
        echo "📁 COMO USAR:"
        echo "1. Coloque arquivos TXT/ZIP/RAR na pasta"
        echo "2. Execute: ./iniciar.sh"
        echo "3. Escolha a versão desejada"
        echo "4. Siga as instruções na tela"
        echo ""
        echo "🇧🇷 RECURSOS:"
        echo "• Filtro automático para URLs brasileiras"
        echo "• Remoção de spam e linhas inválidas"
        echo "• Geração de arquivos com nomes organizados"
        echo "• Suporte a arquivos até 4GB"
        echo ""
        echo "=================================================================="
        ;;
    *)
        echo "❌ Opção inválida!"
        echo "💡 Execute novamente e escolha 1, 2, 3 ou 4"
        exit 1
        ;;
esac

echo ""
echo "👋 CloudBR finalizado. Obrigado!"