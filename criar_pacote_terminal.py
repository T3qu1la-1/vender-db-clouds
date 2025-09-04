
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 Gerador de Pacote CloudBR Terminal
Cria um ZIP com os arquivos essenciais para uso standalone
"""

import zipfile
import os
from datetime import datetime

def criar_pacote_terminal():
    """Cria pacote ZIP com arquivos essenciais do terminal"""
    
    # Nome do arquivo ZIP
    timestamp = datetime.now().strftime("%d%m%Y-%H%M")
    nome_zip = f"cloudbr-terminal-{timestamp}.zip"
    
    # Arquivos essenciais para o terminal
    arquivos_essenciais = [
        'terminal.py',
        'iniciar.sh',
        'cloudsaqui/README.md'
    ]
    
    try:
        with zipfile.ZipFile(nome_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # Adiciona arquivos principais
            for arquivo in arquivos_essenciais:
                if os.path.exists(arquivo):
                    zipf.write(arquivo, arquivo)
                    print(f"✅ Adicionado: {arquivo}")
                else:
                    print(f"⚠️ Arquivo não encontrado: {arquivo}")
            
            # Cria pasta cloudsaqui se não existir no ZIP
            zipf.writestr('cloudsaqui/', '')
            
            # Adiciona README específico do pacote
            readme_content = """# 📦 CloudBR Terminal - Pacote Standalone

## 🚀 Como usar:

### Windows (PowerShell/CMD):
```cmd
# Instalar Python se necessário
# Baixar o pacote e extrair

# Instalar dependências
pip install flask rarfile requests

# Executar
python terminal.py
```

### Linux/Mac:
```bash
# Instalar dependências
pip3 install flask rarfile requests

# Dar permissão ao script
chmod +x iniciar.sh

# Executar
./iniciar.sh
```

## 📁 Estrutura:
- terminal.py - Script principal do terminal
- iniciar.sh - Script de inicialização (Linux/Mac)
- cloudsaqui/ - Pasta para seus arquivos TXT/ZIP/RAR

## 💡 Instruções:
1. Coloque seus arquivos na pasta 'cloudsaqui'
2. Execute terminal.py
3. Escolha a opção de processamento
4. Resultados aparecerão na pasta principal

## 🇧🇷 Recursos:
- Filtro automático para URLs brasileiras
- Suporte a TXT/ZIP/RAR até 4GB
- Interface em português
- Processamento em lote
"""
            
            zipf.writestr('README-PACOTE.md', readme_content)
            
        print(f"\n🎉 Pacote criado com sucesso: {nome_zip}")
        print(f"📏 Tamanho: {os.path.getsize(nome_zip) / 1024:.1f} KB")
        print("\n📥 Baixe este arquivo e extraia no seu computador!")
        
        return nome_zip
        
    except Exception as e:
        print(f"❌ Erro ao criar pacote: {e}")
        return None

if __name__ == "__main__":
    print("📦 Criando pacote CloudBR Terminal...")
    print("=" * 50)
    
    pacote = criar_pacote_terminal()
    
    if pacote:
        print("\n✅ Pacote pronto para download!")
        print("💡 Clique com botão direito no arquivo ZIP e 'Download'")
