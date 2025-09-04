# 🚀 CloudBR - Sistema de Processamento de Credenciais

> **Sistema completo com 3 versões:** Terminal, Web Panel e Bot Telegram  
> **Capacidade:** Processa arquivos TXT/ZIP/RAR até 4GB  
> **Foco:** URLs brasileiras com detecção automática avançada

---

## 📋 Índice

- [🎯 Visão Geral](#-visão-geral)
- [⚡ Características Principais](#-características-principais)  
- [🔧 Instalação Rápida](#-instalação-rápida)
- [💻 Versão Terminal](#-versão-terminal)
- [🌐 Versão Web Panel](#-versão-web-panel)  
- [🤖 Versão Bot Telegram](#-versão-bot-telegram)
- [📁 Arquivos de Saída](#-arquivos-de-saída)
- [🇧🇷 Detecção Brasileira](#-detecção-brasileira)
- [⚙️ Requisitos Técnicos](#️-requisitos-técnicos)
- [🛠️ Desenvolvimento](#️-desenvolvimento)
- [❓ FAQ](#-faq)

---

## 🎯 Visão Geral

O **CloudBR** é um sistema avançado de processamento de credenciais que oferece **3 interfaces diferentes** para atender qualquer necessidade:

| Versão | Ideal Para | Características |
|--------|------------|----------------|
| **🖥️ Terminal** | Uso offline e processamento em lote | Menu interativo, pasta local |
| **🌐 Web Panel** | Interface moderna no navegador | Upload até 4GB, SQLite por IP |
| **🤖 Bot Telegram** | Uso móvel e processamento remoto | Chat automatizado, histórico |

---

## ⚡ Características Principais

### 🚀 **Performance Avançada**
- ✅ **Arquivos até 4GB** cada
- ✅ **Streaming direto** para arquivos grandes (500MB+)  
- ✅ **Multi-threading** e processamento paralelo
- ✅ **Sistema de sharding** com SQLites distribuídos
- ✅ **Auto-limpeza** de dados temporários

### 🇧🇷 **Detecção Brasileira Inteligente**  
- ✅ **Domínios .br** completos (200+ variações)
- ✅ **Sites brasileiros** .com/.net conhecidos
- ✅ **Padrões urbanos** (cidades, CEPs, expressões)
- ✅ **Filtros anti-spam** avançados
- ✅ **Validação dupla** de credenciais

### 📤 **Saídas Organizadas**
- ✅ **Naming bonito** com timestamps
- ✅ **Arquivos separados** (geral + brasileiro)
- ✅ **Estatísticas detalhadas** de processamento
- ✅ **Histórico completo** por usuário

---

## 🔧 Instalação Rápida

### **1️⃣ Clone o Repositório**
```bash
git clone https://github.com/seu-usuario/cloudbr-sistema.git
cd cloudbr-sistema
```

### **2️⃣ Instale Dependências**
```bash
pip install -r requirements.txt
```
Ou instale individualmente:
```bash
pip install flask rarfile requests telethon email-validator gunicorn
```

### **3️⃣ Inicie o Sistema**
```bash
# Modo interativo (recomendado)
./iniciar.sh

# Ou escolha diretamente:
python terminal.py     # Versão terminal
python app_web.py      # Versão web
python telegram_bot.py # Bot telegram
```

---

## 💻 Versão Terminal

### **🎯 Como Usar**

1. **Prepare os Arquivos**
   ```bash
   # Coloque seus arquivos na pasta do script
   cp /caminho/para/arquivo.txt ./
   cp /caminho/para/arquivo.zip ./
   ```

2. **Execute o Script**
   ```bash
   python terminal.py
   ```

3. **Navegue no Menu**
   ```
   🎯 MENU PRINCIPAL:
   
   1️⃣  Processar arquivos da pasta atual
   2️⃣  Iniciar painel web (Flask)  
   3️⃣  Iniciar bot do Telegram
   4️⃣  Ver arquivos na pasta
   5️⃣  Ajuda e instruções
   6️⃣  Sair
   ```

### **⚡ Recursos Terminal**

- **📁 Auto-detecção** de arquivos TXT/ZIP/RAR
- **🎯 Menu numerado** intuitivo em português
- **📊 Estatísticas em tempo real** 
- **🔄 Processamento em lote** de múltiplos arquivos
- **💾 Saída local** na mesma pasta

### **📤 Exemplo de Uso**
```bash
$ python terminal.py

🚀 CloudBR Terminal - Sistema de Processamento de Credenciais
================================================================
📁 Processa arquivos TXT/ZIP/RAR até 4GB
🇧🇷 Filtro automático para URLs brasileiras
⚡ Interface de terminal interativa
================================================================

🎯 MENU PRINCIPAL:

1️⃣  Processar arquivos da pasta atual

🎯 Escolha uma opção (1-6): 1

📁 ARQUIVOS ENCONTRADOS:
================================================================
 1. 📄 credenciais.txt (245.3 MB)
 2. 📄 dados.zip (1.2 GB)
 3. 📄 backup.rar (890.5 MB)

0️⃣  Processar TODOS os arquivos
🔙 Voltar ao menu principal (digite 'v')

🎯 Escolha um arquivo (número) ou 0 para todos: 0

🚀 PROCESSAMENTO EM LOTE - 3 arquivo(s)
================================================================

📁 [1/3] Processando: credenciais.txt
  ✅ 485,329 válidas, 125,847 brasileiras

📁 [2/3] Processando: dados.zip
  📄 Processando: dados1.txt
  📄 Processando: dados2.txt
  ✅ 1,204,556 válidas, 89,234 brasileiras

📁 [3/3] Processando: backup.rar
  ✅ 890,445 válidas, 201,332 brasileiras

================================================================
🎯 RESUMO FINAL DO LOTE:
================================================================
📁 Arquivos processados: 3
📝 Linhas totais: 8,945,332
✅ Credenciais válidas: 2,580,330
🇧🇷 URLs brasileiras: 416,413
🗑️ Spam removido: 6,364,999
⏱️ Tempo total: 247.3s
📈 Taxa de sucesso: 28.8%

✅ Arquivo geral consolidado: cloudbr-LOTE-GERAL-04.09.2025-1423.txt
✅ Arquivo brasileiro consolidado: cloudbr-LOTE-BR-04.09.2025-1423.txt
```

---

## 🌐 Versão Web Panel

### **🎯 Como Usar**

1. **Inicie o Servidor**
   ```bash
   python app_web.py
   ```

2. **Acesse o Painel**
   ```
   🔗 URL: http://localhost:5000
   ```

3. **Interface Moderna**
   - **📤 Upload até 4GB** por arquivo simultâneo
   - **🎨 Design dark** responsivo
   - **📊 Dashboard em tempo real** 
   - **⚡ Sistema por IP** (sessões isoladas)

### **⚡ Recursos Web Panel**

- **🔒 Sistema por IP** - Cada usuário tem SQLites isolados  
- **📈 Estatísticas live** - Contadores em tempo real
- **🗄️ 8 SQLites por IP** - Performance distribuída  
- **🧹 Auto-limpeza** - Remove dados inativos (20min)
- **💾 Downloads organizados** - Arquivos e bancos completos
- **🤖 Integração com Bot** - Inicie o Telegram direto pelo painel

### **📱 Interface Responsiva**
```html
🚀 Central TXT Pro - Sistema por IP

📊 Dashboard:
┌─────────────────┬─────────────────┬─────────────────┐
│  ✅ 2,580,330   │  🇧🇷 416,413    │  📁 8 SQLites   │
│  Credenciais    │  Brasileiras    │  Ativos         │
└─────────────────┴─────────────────┴─────────────────┘

🎯 Menu:
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  📤 Processamento │  📥 Downloads   │  ⚙️ Configurações │  🤖 Bot Telegram │
│  Upload e proc.  │  Filtros/DBs    │  Dados/SQLites  │  Iniciar bot    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 🤖 Versão Bot Telegram

### **🎯 Como Usar**

1. **Inicie o Bot**
   ```bash
   python telegram_bot.py
   ```

2. **No Telegram**
   ```
   /adicionar - Iniciar processamento
   /meuhistorico - Ver histórico completo
   ```

3. **Envie Arquivos**
   - Arraste arquivos TXT/ZIP/RAR até 4GB
   - Receba resultados automaticamente
   - Histórico salvo permanentemente

### **⚡ Recursos Bot Telegram**

- **🚀 Processamento até 4GB** por arquivo
- **📱 Interface mobile-first** otimizada  
- **💾 Histórico permanente** com SQLite
- **🎯 Naming automatico** `cloudbr#X-@usuario.txt`
- **📊 Estatísticas completas** por processamento
- **🔄 Sistema de fila** para múltiplos arquivos

### **💬 Exemplo de Conversa**
```
👤 Usuário: /adicionar

🤖 Bot: 🎯 Sistema de Processamento ATIVADO!

📤 Envie seus arquivos TXT/ZIP/RAR (até 4GB cada)
⚡ Processamento automático com filtros brasileiros
📁 Resultado: cloudbr#1-@seunome.txt

---

👤 Usuário: [Envia arquivo.zip - 1.2GB]

🤖 Bot: 🚀 Download Ultra Rápido 1º

📁 arquivo.zip  
📏 1,200.5 MB
⚡ Iniciando download otimizado...

[Progresso] 📊 45% • 89.3 MB/s • ETA: 8.2min

---

🤖 Bot: ⚡ Processamento 1º - ULTRA RÁPIDO

📁 arquivo.zip
📏 1,200.5 MB  
⏱️ Download: 14.3s (84.0 MB/s)
🔄 Filtrando + processando...

---

🤖 Bot: 🎯 LOTE FINALIZADO - cloudbr#1

👤 @seunome - Finalização #1
📊 Resumo:
📁 Arquivos: 1 | 📝 Linhas: 2,456,789
✅ Válidas: 892,445 | 🇧🇷 Brasileiras: 234,567  
🗑️ Spam: 1,564,344 | 📈 Taxa: 36.3%

📤 Enviando resultados com naming bonito...

---

🤖 Bot: [Arquivo] cloudbr#1-@seunome.txt

📁 cloudbr#1-@seunome.txt

✅ 892,445 credenciais GERAL
📊 Taxa: 36.3%  
👤 @seunome - Finalização #1

---

🤖 Bot: [Arquivo] cloudbr#1-@seunome-BR.txt  

📁 cloudbr#1-@seunome-BR.txt

✅ 234,567 credenciais BRASILEIRAS
📊 Taxa: 36.3%
👤 @seunome - Finalização #1

---

🤖 Bot: 🎉 PROCESSAMENTO COMPLETO!

👤 @seunome - cloudbr#1
✅ 1 arquivos processados  
📤 Resultados enviados com naming bonito
💾 Histórico salvo no SQLite

🔄 /adicionar | 📊 /meuhistorico
```

---

## 📁 Arquivos de Saída

### **🎨 Naming Bonito Automático**

| Versão | Formato | Exemplo |
|--------|---------|---------|
| **Terminal** | `cloudbr-[nome]-[tipo]-[data].txt` | `cloudbr-dados-GERAL-04.09.2025.txt` |
| **Web Panel** | `resultado_[tipo]_[timestamp].txt` | `resultado_brasileiras_1725456789.txt` |  
| **Bot Telegram** | `cloudbr#[num]-@[user][-BR].txt` | `cloudbr#1-@joao-BR.txt` |

### **📊 Conteúdo dos Arquivos**

#### **Arquivo Geral (`-GERAL`):**
```
email1@dominio.com:senha123
usuario2@site.net:abc456  
login3@empresa.org:def789
[... todas as credenciais válidas ...]
```

#### **Arquivo Brasileiro (`-BR`):**
```  
user@uol.com.br:senha123
admin@globo.com:abc456
teste@americanas.com:def789
contato@prefeitura.gov.br:xyz321
[... apenas URLs brasileiras ...]
```

### **📈 Estatísticas Incluídas**

Todos os processamentos geram relatórios com:
- **📝 Total de linhas** processadas
- **✅ Credenciais válidas** encontradas  
- **🇧🇷 URLs brasileiras** detectadas
- **🗑️ Spam removido** automaticamente
- **📈 Taxa de sucesso** percentual
- **⏱️ Tempo de processamento** 
- **👤 Informações do usuário** (bot/web)

---

## 🇧🇷 Detecção Brasileira

### **🎯 Domínios .br Completos**
```
.com.br, .org.br, .net.br, .gov.br, .edu.br, .mil.br,
.art.br, .adv.br, .blog.br, .eco.br, .emp.br, .eng.br,
.esp.br, .etc.br, .far.br, .flog.br, .fnd.br, .fot.br,
.fst.br, .g12.br, .geo.br, .ggf.br, .imb.br, .ind.br,
.inf.br, .jor.br, .jus.br, .lel.br, .mat.br, .med.br,
[... +200 variações ...]
```

### **🏢 Sites Brasileiros (.com/.net)**  
```
uol.com, globo.com, terra.com, ig.com, r7.com,
americanas.com, submarino.com, magazineluiza.com,
mercadolivre.com, olx.com, webmotors.com,
zapimoveis.com, vivareal.com, netshoes.com,
[... +50 sites conhecidos ...]
```

### **🏙️ Padrões Urbanos Brasileiros**
```python
# Cidades principais  
'saopaulo', 'riodejaneiro', 'brasilia', 'salvador', 
'fortaleza', 'belohorizonte', 'manaus', 'curitiba',
'recife', 'goiania', 'porto', 'alegre', [...]

# Expressões tipicamente brasileiras
'ltda', 'eireli', 'mei', 'cpf', 'cnpj', 'cep', 'pix',
'cartaobndes', 'sebrae', 'senai', 'sesi', 'senac'
```

### **🚫 Anti-Spam Avançado**
Remove automaticamente:
- **Cabeçalhos** de crackers (`WOLF`, `CRACKED`, `HACKED`)
- **Links e promocionais** (`https://`, `www.`, `TELEGRAM`) 
- **Separadores visuais** (`***`, `===`, `---`)
- **Linhas muito curtas/longas** (< 5 ou > 500 caracteres)
- **Formatos inválidos** sem `:` ou com múltiplos `:`

---

## ⚙️ Requisitos Técnicos

### **🐍 Python & Dependências**
```txt
Python >= 3.8
flask >= 2.3.0
rarfile >= 4.0  
requests >= 2.31.0
telethon >= 1.29.0
email-validator >= 2.0.0
gunicorn >= 21.0.0 (produção)
```

### **💾 Recursos de Sistema**
- **RAM:** 4GB+ recomendado (para arquivos 1GB+)
- **Storage:** Espaço = 2x tamanho do maior arquivo  
- **CPU:** Multi-core recomendado (processamento paralelo)
- **Network:** Conectividade estável (bot Telegram)

### **🔧 Ferramentas Externas**
- **unrar** (Linux/Mac): `sudo apt install unrar` / `brew install unrar`
- **SQLite3** (incluso no Python)
- **Telegram API** (bot version) - chaves hardcoded

---

## 🛠️ Desenvolvimento

### **📁 Estrutura do Projeto**
```
cloudbr-sistema/
│
├── 🚀 iniciar.sh              # Script principal de inicialização
├── 💻 terminal.py             # Versão terminal (menu interativo)
├── 🌐 app.py                  # Core Flask (lógica principal)  
├── 🌐 app_web.py              # Launcher web panel
├── 🤖 telegram_bot.py         # Bot completo do Telegram
├── ⚙️ main.py                 # Entry point alternativo
├── 📋 requirements.txt        # Dependências Python
├── 📖 README.md               # Esta documentação
└── 📝 replit.md               # Config/preferências internas
```

### **🔧 Configurações Personalizáveis**

#### **Terminal (terminal.py):**
```python  
# Domínios brasileiros
DOMINIOS_BRASILEIROS = {'.com.br', '.br', ...}

# Sites brasileiros  
SITES_BRASILEIROS = {'uol.com', 'globo.com', ...}
```

#### **Web Panel (app.py):**
```python
# Upload limits
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB
app.config['UPLOAD_TIMEOUT'] = 1800  # 30 minutos

# Auto-cleanup  
CLEANUP_INTERVAL = timedelta(minutes=20)
```

#### **Bot Telegram (telegram_bot.py):**
```python
# API Credentials (hardcoded)
API_ID = 25317254
API_HASH = "bef2f48bb6b4120c9189ecfd974eb820" 
BOT_TOKEN = "8287218911:AAGwVkojvUEalSMZD58zx4jtjRgR2adGKVQ"
```

### **🚀 Deploy em Produção**

#### **Web Panel (Gunicorn):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 app_web:app
```

#### **Bot Telegram (Systemd):**
```ini
[Unit]
Description=CloudBR Telegram Bot
After=network.target

[Service]
Type=simple
User=cloudbr
WorkingDirectory=/opt/cloudbr
ExecStart=/usr/bin/python3 telegram_bot.py  
Restart=always

[Install]
WantedBy=multi-user.target
```

#### **Terminal (Cron Jobs):**
```cron
# Processamento automático diário às 02:00
0 2 * * * /opt/cloudbr/terminal.py --auto-process
```

---

## ❓ FAQ

### **🔧 Configuração**

**P: Como configurar as credenciais do bot Telegram?**  
R: As credenciais estão hardcoded no arquivo `telegram_bot.py` nas linhas 15-17. Você pode alterá-las diretamente no código.

**P: Posso rodar múltiplas versões simultaneamente?**  
R: Sim! Terminal, web panel e bot são independentes. Você pode executar todos ao mesmo tempo.

**P: Como alterar a porta do web panel?**  
R: Edite `app_web.py` linha 14: `app.run(host="0.0.0.0", port=NOVA_PORTA, debug=True)`

### **📊 Performance**

**P: Qual o limite real de tamanho de arquivo?**  
R: Tecnicamente 4GB, mas recomendamos 2GB para performance ótima. Arquivos maiores podem funcionar mas serão mais lentos.

**P: Como acelerar o processamento?**  
R: 
- Use arquivos TXT simples (mais rápido que ZIP/RAR)
- Mantenha a máquina com bastante RAM livre
- Feche outros programas pesados durante processamento

**P: O sistema funciona offline?**  
R: Terminal = 100% offline. Web panel = offline após iniciar. Bot Telegram = precisa de internet sempre.

### **🇧🇷 Detecção Brasileira**

**P: Posso adicionar novos domínios brasileiros?**  
R: Sim! Edite as variáveis `DOMINIOS_BRASILEIROS` e `SITES_BRASILEIROS` em qualquer arquivo.

**P: Como o sistema detecta se uma URL é brasileira?**  
R: Usa 3 métodos: 1) Domínios .br oficiais, 2) Sites .com/.net conhecidos, 3) Padrões urbanos/linguísticos.

**P: Por que algumas URLs brasileiras não foram detectadas?**  
R: O sistema é conservador para evitar falsos positivos. Você pode adicionar manualmente novos padrões.

### **🐛 Problemas Comuns**

**P: "Erro ao processar arquivo ZIP/RAR"**  
R: 
1. Instale `unrar`: `sudo apt install unrar` (Linux) ou `brew install unrar` (Mac)
2. Verifique se o arquivo não está corrompido
3. Teste com arquivo menor primeiro

**P: "Bot não responde no Telegram"**  
R:
1. Verifique se `telegram_bot.py` está rodando  
2. Confirme as credenciais API na linha 15-17
3. Teste com comando `/start` primeiro

**P: "Arquivo muito grande" no web panel**  
R:
1. Confirme que o arquivo é realmente ≤ 4GB
2. Tente dividir em arquivos menores  
3. Use a versão terminal para arquivos muito grandes

### **💡 Dicas Avançadas**

**P: Como processar milhares de arquivos automaticamente?**  
R: Use a versão terminal com script bash:
```bash
#!/bin/bash
for arquivo in *.txt *.zip *.rar; do
    echo "Processando $arquivo..."
    python3 terminal.py --auto --input "$arquivo"
done
```

**P: Como migrar dados entre versões?**  
R: Todas as versões geram arquivos TXT compatíveis. Você pode usar a saída de uma como entrada de outra.

**P: Como fazer backup dos resultados?**  
R:
- Terminal: arquivos ficam na pasta local
- Web panel: use o botão "Download Todos SQLites"  
- Bot Telegram: arquivos ficam salvos no chat

---

## 🏆 Conclusão

O **CloudBR** oferece a solução mais completa para processamento de credenciais com foco brasileiro:

- **🖥️ Terminal:** Para processamento offline e em lote
- **🌐 Web Panel:** Para interface moderna e uploads grandes  
- **🤖 Bot Telegram:** Para uso móvel e compartilhamento

Cada versão mantém a mesma **qualidade de detecção brasileira** e **performance até 4GB**, oferecendo **flexibilidade total** para qualquer cenário de uso.

---

**🚀 Desenvolvido com foco na comunidade brasileira**  
**⚡ Performance, qualidade e facilidade de uso**  
**🇧🇷 Detecção brasileira mais avançada disponível**

---

*Para suporte técnico, abra uma issue no repositório GitHub.*