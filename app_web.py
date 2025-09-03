#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 Painel Web Flask - Sistema Gigante 4GB
Painel web separado para rodar junto com o bot
"""

from app import app

if __name__ == "__main__":
    print("🌐 Iniciando Painel Web Flask...")
    print("🚀 Painel disponível na porta 5000")
    print("⚡ Todas as funcionalidades do painel original")
    app.run(host="0.0.0.0", port=5000, debug=True)