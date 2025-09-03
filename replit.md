
# Flask TXT Processor Application - Sistema Gigante 4GB

## Overview
Sistema Flask otimizado para processamento de arquivos TXT/ZIP/RAR de até **4GB**, com arquitetura multi-SQLite distribuída por IP real.

## Correções Implementadas (Set 2025)
### ✅ **Erro 413 Request Entity Too Large - RESOLVIDO**
- **Limite aumentado:** 2GB → **4GB** por arquivo
- **Timeout estendido:** 30min → **2 horas (7200s)**
- **Headers otimizados:** 32KB para requests grandes
- **Workflow atualizado:** "Upload Gigante - 500MB+" configurado para 4GB
- **Tratamento de erro:** Página explicativa para arquivos >4GB

### 🚀 **Sistema de Processamento Multi-SQLite**
- **8 SQLites por IP:** 4 principais + 4 shards distribuídos
- **Streaming direto:** Arquivos 500MB+ processados sem RAM
- **Auto-limpeza:** 20 minutos de inatividade
- **URLs brasileiras:** Detecção automática expandida (.com/.net brasileiros)

## Capacidades Atuais
- ✅ **Upload:** Até 4GB por arquivo simultâneo
- ✅ **Formatos:** TXT, ZIP, RAR
- ✅ **Processamento:** Streaming direto para SQLite
- ✅ **Filtros:** URLs brasileiras automáticas (.br + sites nacionais)
- ✅ **Distribuição:** 4 shards para performance
- ✅ **Timeout:** 2 horas para arquivos gigantes

## Project Structure
- `app.py` - Aplicação Flask principal com sistema multi-SQLite
- `main.py` - Entry point
- `pyproject.toml` - Dependencies
- `replit.md` - Documentação atualizada

## Features
- **Upload de arquivos até 4GB** com tratamento de erro 413
- **Processamento streaming** para arquivos 500MB+
- **Sistema de sharding** com 4 SQLites distribuídos
- **Detecção brasileira expandida** (inclui .com/.net nacionais)
- **Interface dark moderna** com estatísticas por IP
- **Auto-limpeza temporária** (20 min inatividade)

## Workflows Configurados
1. **"Upload Gigante - 500MB+"** (botão Run)
   - Timeout: 7200s (2 horas)
   - Limite: 4GB por arquivo
   - Workers: 1 otimizado
   - Headers: 32KB

## Dependencies
- Flask 3.1.2+ - Web framework
- Gunicorn 23.0.0+ - WSGI server otimizado
- Email-validator 2.2.0+ - Validação
- Flask-SQLAlchemy 3.1.1+ - ORM
- Psycopg2-binary 2.9.10+ - PostgreSQL

## Soluções para Arquivos >4GB
1. **Divida em partes menores** (4GB máximo cada)
2. **Comprima com ZIP/RAR** para reduzir tamanho
3. **Use múltiplos uploads** simultâneos
4. **Processe em lotes** separados

## User Preferences
- Interface em Português (PT-BR)
- Tema escuro com gradientes
- Foco em credenciais brasileiras
- Sistema temporário por IP

## Architecture
- **Flask app** com ProxyFix para Replit
- **8 SQLites por IP:** main, stats, brazilian, domains + 4 shards
- **Streaming direto** para arquivos gigantes
- **Detecção BR expandida** incluindo sites .com/.net brasileiros
- **Auto-cleanup** após inatividade
