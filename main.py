
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 Bot do Telegram - Sistema Gigante 4GB
Entry point principal - executa o bot por padrão
Para executar painel web: python app.py
"""

import sys
import os

if __name__ == "__main__":
    # Se executado com argumento 'web', inicia o painel
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        from app import app
        print("🌐 Iniciando Painel Web Flask...")
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        # Por padrão, executa o bot
        from telegram_bot import main
        import asyncio
        asyncio.run(main())
