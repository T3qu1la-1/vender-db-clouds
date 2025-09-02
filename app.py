
from flask import Flask, request, render_template_string, send_file
import os
import logging
import sqlite3
import tempfile
import zipfile
import io
import re
import threading
import time
import hashlib
from urllib.parse import urlparse
from datetime import datetime, timedelta

# Logging simplificado
logging.basicConfig(level=logging.ERROR, format='%(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Sistema de sessões por IP com SQLite
IP_SESSIONS = {}
CLEANUP_TIMERS = {}

def get_user_ip():
    """Obtém IP real do usuário de forma mais precisa"""
    # Tenta vários headers para pegar o IP real
    ip_headers = [
        'HTTP_CF_CONNECTING_IP',      # Cloudflare
        'HTTP_X_FORWARDED_FOR',       # Proxies padrão
        'HTTP_X_REAL_IP',             # Nginx
        'HTTP_X_FORWARDED',           # Outros proxies
        'HTTP_X_CLUSTER_CLIENT_IP',   # Clusters
        'HTTP_FORWARDED_FOR',         # RFC 7239
        'HTTP_FORWARDED',             # RFC 7239
        'REMOTE_ADDR'                 # IP direto
    ]
    
    # Tenta request.headers primeiro
    for header in ['CF-Connecting-IP', 'X-Forwarded-For', 'X-Real-IP', 'X-Forwarded', 'X-Cluster-Client-IP']:
        ip = request.headers.get(header)
        if ip:
            # Se for lista de IPs separados por vírgula, pega o primeiro
            real_ip = ip.split(',')[0].strip()
            if real_ip and real_ip != 'unknown':
                return real_ip
    
    # Tenta request.environ
    for header in ip_headers:
        ip = request.environ.get(header)
        if ip:
            real_ip = ip.split(',')[0].strip()
            if real_ip and real_ip != 'unknown':
                return real_ip
    
    # Fallback para REMOTE_ADDR
    return request.environ.get('REMOTE_ADDR', f'temp_{int(time.time())}')

def get_ip_hash(ip):
    """Gera hash único e seguro para o IP"""
    # Adiciona timestamp para garantir unicidade em caso de IPs temporários
    timestamp = str(int(time.time() // 3600))  # Muda a cada hora
    unique_string = f"{ip}_{timestamp}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:12]

def create_ip_databases(ip_hash, real_ip=None):
    """Cria bancos SQLite específicos para o IP"""
    db_dir = os.path.join(tempfile.gettempdir(), f"user_{ip_hash}")
    os.makedirs(db_dir, exist_ok=True)
    
    print(f"🗄️ Criando SQLites para IP real: {real_ip} -> Hash: {ip_hash}")
    print(f"📁 Diretório SQLite: {db_dir}")
    
    databases = {
        'main': os.path.join(db_dir, 'main.db'),
        'stats': os.path.join(db_dir, 'stats.db'),
        'brazilian': os.path.join(db_dir, 'brazilian.db'),
        'domains': os.path.join(db_dir, 'domains.db')
    }
    
    # Cria tabela principal
    conn = sqlite3.connect(databases['main'])
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        linha_completa TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    
    # Cria tabela de estatísticas
    conn = sqlite3.connect(databases['stats'])
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY,
        total_lines INTEGER DEFAULT 0,
        valid_lines INTEGER DEFAULT 0,
        brazilian_urls INTEGER DEFAULT 0,
        unique_domains INTEGER DEFAULT 0,
        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Insere registro inicial zerado
    cursor.execute('INSERT OR REPLACE INTO stats (id, total_lines, valid_lines, brazilian_urls, unique_domains) VALUES (1, 0, 0, 0, 0)')
    conn.commit()
    conn.close()
    
    # Cria tabela de URLs brasileiras
    conn = sqlite3.connect(databases['brazilian'])
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS brazilian_urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        linha_completa TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    
    # Cria tabela de domínios
    conn = sqlite3.connect(databases['domains'])
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS domains (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE NOT NULL,
        count INTEGER DEFAULT 1,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    
    return databases

def get_user_session(ip):
    """Obtém ou cria sessão do usuário por IP real"""
    ip_hash = get_ip_hash(ip)
    
    if ip_hash not in IP_SESSIONS:
        databases = create_ip_databases(ip_hash, ip)
        IP_SESSIONS[ip_hash] = {
            'databases': databases,
            'last_activity': datetime.now(),
            'stats': {'total_lines': 0, 'valid_lines': 0, 'brazilian_urls': 0, 'domains': 0}
        }
        
        # Carrega estatísticas do banco
        try:
            conn = sqlite3.connect(databases['stats'])
            cursor = conn.cursor()
            cursor.execute('SELECT total_lines, valid_lines, brazilian_urls, unique_domains FROM stats WHERE id = 1')
            result = cursor.fetchone()
            if result:
                IP_SESSIONS[ip_hash]['stats'] = {
                    'total_lines': result[0],
                    'valid_lines': result[1], 
                    'brazilian_urls': result[2],
                    'domains': result[3]
                }
            conn.close()
        except:
            pass
    
    # Atualiza última atividade
    IP_SESSIONS[ip_hash]['last_activity'] = datetime.now()
    
    # Agenda limpeza automática (30 minutos de inatividade)
    schedule_cleanup(ip_hash)
    
    return IP_SESSIONS[ip_hash]

def schedule_cleanup(ip_hash):
    """Agenda limpeza automática dos SQLites temporários por IP"""
    # Cancela timer anterior se existir
    if ip_hash in CLEANUP_TIMERS:
        CLEANUP_TIMERS[ip_hash].cancel()
    
    def cleanup_ip_data():
        try:
            if ip_hash in IP_SESSIONS:
                # Remove todos os bancos SQLite temporários do IP
                db_dir = os.path.dirname(IP_SESSIONS[ip_hash]['databases']['main'])
                if os.path.exists(db_dir):
                    import shutil
                    shutil.rmtree(db_dir)
                    print(f"🗑️ Limpeza automática: SQLites temporários do IP {ip_hash} removidos")
                
                # Remove da memória
                del IP_SESSIONS[ip_hash]
                if ip_hash in CLEANUP_TIMERS:
                    del CLEANUP_TIMERS[ip_hash]
        except Exception as e:
            print(f"✗ Erro na limpeza automática do IP {ip_hash}: {e}")
    
    # Timer de 20 minutos para SQLites temporários (1200 segundos)
    timer = threading.Timer(1200.0, cleanup_ip_data)
    timer.daemon = True
    timer.start()
    CLEANUP_TIMERS[ip_hash] = timer
    print(f"⏰ Timer de limpeza agendado para IP {ip_hash} em 20 minutos")

def update_stats(ip_hash, new_lines_count):
    """Atualiza estatísticas no banco SQLite"""
    if ip_hash not in IP_SESSIONS:
        return
    
    session = IP_SESSIONS[ip_hash]
    session['stats']['total_lines'] += new_lines_count
    session['stats']['valid_lines'] += new_lines_count
    
    # Atualiza no banco
    try:
        conn = sqlite3.connect(session['databases']['stats'])
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE stats SET 
            total_lines = ?, 
            valid_lines = ?, 
            last_update = CURRENT_TIMESTAMP 
        WHERE id = 1
        ''', (session['stats']['total_lines'], session['stats']['valid_lines']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"✗ Erro ao atualizar stats: {e}")

# HTML da interface com estatísticas zeradas por padrão
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🚀 Central TXT Pro - Sistema por IP</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --warning: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%);
            --info: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            --danger: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f0f23 75%, #000000 100%);
            min-height: 100vh;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .main-header {
            background: var(--primary);
            padding: 2rem 0;
            text-align: center;
            border-radius: 0 0 30px 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 3rem;
        }
        
        .nav-tabs {
            border: none;
            justify-content: center;
            margin-bottom: 2rem;
        }
        
        .nav-tabs .nav-link {
            border: none;
            background: rgba(20, 20, 35, 0.8);
            color: #e0e0e0;
            margin: 0 0.5rem;
            border-radius: 15px;
            padding: 15px 25px;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .nav-tabs .nav-link:hover {
            background: rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .nav-tabs .nav-link.active {
            background: var(--primary);
            color: white;
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
        }
        
        .system-card {
            backdrop-filter: blur(15px);
            background: linear-gradient(145deg, rgba(20, 20, 35, 0.9) 0%, rgba(30, 30, 50, 0.8) 100%);
            border: 1px solid rgba(138, 43, 226, 0.3);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
            margin-bottom: 2rem;
        }
        
        .system-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(138, 43, 226, 0.3);
        }
        
        .dashboard-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(138, 43, 226, 0.2) 100%);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(138, 43, 226, 0.3);
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(138, 43, 226, 0.3);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        }
        
        .ip-info {
            background: rgba(138, 43, 226, 0.1);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            border: 1px solid rgba(138, 43, 226, 0.3);
        }
        
        .auto-cleanup-info {
            background: rgba(255, 193, 7, 0.1);
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 193, 7, 0.3);
            margin-bottom: 2rem;
        }
        
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        
        .menu-item {
            background: linear-gradient(135deg, rgba(20, 20, 35, 0.8) 0%, rgba(30, 30, 50, 0.8) 100%);
            border: 1px solid rgba(138, 43, 226, 0.3);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .menu-item:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 35px rgba(138, 43, 226, 0.4);
        }
        
        .menu-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: var(--primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .btn-system {
            border: none;
            border-radius: 12px;
            padding: 12px 30px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.3s ease;
            margin: 0.5rem;
        }
        
        .btn-system:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .btn-processing { background: var(--primary); }
        .btn-download { background: var(--success); }
        .btn-filter { background: var(--warning); }
        .btn-convert { background: var(--info); color: #333; }
        .btn-visualize { background: var(--danger); }
        
        .form-control {
            background: rgba(20, 20, 35, 0.8);
            border: 1px solid rgba(138, 43, 226, 0.3);
            border-radius: 12px;
            color: #e0e0e0;
        }
        
        .form-control:focus {
            background: rgba(30, 30, 50, 0.9);
            border-color: #8a2be2;
            box-shadow: 0 0 20px rgba(138, 43, 226, 0.5);
        }
        
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        
        .file-input-label {
            padding: 15px 20px;
            background: rgba(20, 20, 35, 0.6);
            border: 2px dashed rgba(138, 43, 226, 0.4);
            border-radius: 15px;
            cursor: pointer;
            display: block;
            text-align: center;
            transition: all 0.4s ease;
            color: #e0e0e0;
        }
        
        .file-input-label:hover {
            background: rgba(30, 30, 50, 0.8);
            border-color: #8a2be2;
            transform: translateY(-2px);
        }
        
        .tab-content {
            background: rgba(20, 20, 35, 0.6);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid rgba(138, 43, 226, 0.3);
            backdrop-filter: blur(10px);
        }
        
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay">
        <div style="text-align: center; color: white;">
            <div class="spinner"></div>
            <div style="font-size: 18px;">🔄 Processando...</div>
        </div>
    </div>

    <div class="main-header">
        <div class="container">
            <h1 class="text-white mb-2">
                <i class="fas fa-rocket me-3"></i>
                Central TXT Pro - Sistema Multi-SQLite
            </h1>
            <p class="text-white-50 mb-0">Sistema organizado por IP com auto-limpeza</p>
        </div>
    </div>

    <div class="container">
        <div class="ip-info">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <i class="fas fa-user-circle me-2"></i>
                    <strong>IP Real:</strong> <code class="text-warning">USER_REAL_IP</code>
                    <br><small class="text-muted">Hash Sessão: <code>USER_IP_HASH</code></small>
                </div>
                <div>
                    <i class="fas fa-database me-2"></i>
                    <span class="badge bg-success">4 SQLites Temporários</span>
                </div>
            </div>
        </div>
        
        <div class="auto-cleanup-info">
            <div class="d-flex align-items-center">
                <i class="fas fa-clock me-3 text-warning"></i>
                <div>
                    <strong>SQLites Temporários:</strong> Auto-limpeza após 20 minutos de inatividade
                    <br><small class="text-muted">Bancos SQLite específicos do seu IP real serão removidos automaticamente</small>
                </div>
            </div>
        </div></small>
        
        <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.1); border-radius: 10px; border: 1px solid rgba(23, 162, 184, 0.3);">
            <div class="d-flex align-items-center">
                <i class="fas fa-server me-3"></i>
                <div>
                    <strong>Sistema Multi-SQLite por IP:</strong> Cada IP real recebe 4 bancos SQLite isolados
                    <br><small class="text-muted">main.db • stats.db • brazilian.db • domains.db</small>
                </div>
            </div>
        </div>

        <div class="dashboard-stats">
            <div class="stat-card">
                <div class="stat-number">USER_TOTAL_LINES</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-chart-line me-2"></i>LINHAS PROCESSADAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">USER_VALID_LINES</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-check-circle me-2"></i>LINHAS VÁLIDAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">USER_BRAZILIAN_URLS</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-flag me-2"></i>URLs BRASILEIRAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">USER_DOMAINS</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-globe me-2"></i>DOMÍNIOS ÚNICOS</div>
            </div>
        </div>

        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="dashboard-tab" data-bs-toggle="tab" data-bs-target="#dashboard" type="button">
                    <i class="fas fa-tachometer-alt me-2"></i>Dashboard
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="processing-tab" data-bs-toggle="tab" data-bs-target="#processing" type="button">
                    <i class="fas fa-upload me-2"></i>Processamento
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="downloads-tab" data-bs-toggle="tab" data-bs-target="#downloads" type="button">
                    <i class="fas fa-download me-2"></i>Downloads
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="settings-tab" data-bs-toggle="tab" data-bs-target="#settings" type="button">
                    <i class="fas fa-cog me-2"></i>Configurações
                </button>
            </li>
        </ul>

        <div class="tab-content">
            <!-- Dashboard -->
            <div class="tab-pane fade show active" id="dashboard">
                <h2 class="text-white mb-4"><i class="fas fa-tachometer-alt me-3"></i>Painel de Controle</h2>
                
                <div class="menu-grid">
                    <div class="menu-item" onclick="switchTab('processing')">
                        <div class="menu-icon"><i class="fas fa-upload"></i></div>
                        <h4 class="text-white">Processamento</h4>
                        <p class="text-muted">Upload e processamento de arquivos TXT, ZIP e RAR</p>
                    </div>
                    
                    <div class="menu-item" onclick="switchTab('downloads')">
                        <div class="menu-icon"><i class="fas fa-download"></i></div>
                        <h4 class="text-white">Downloads</h4>
                        <p class="text-muted">Download completo e filtros especializados</p>
                    </div>
                    
                    <div class="menu-item" onclick="switchTab('settings')">
                        <div class="menu-icon"><i class="fas fa-cog"></i></div>
                        <h4 class="text-white">Configurações</h4>
                        <p class="text-muted">Gerenciamento de dados e SQLites</p>
                    </div>
                </div>
            </div>

            <!-- Processamento -->
            <div class="tab-pane fade" id="processing">
                <div class="system-card">
                    <div style="background: var(--primary); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-white mb-0"><i class="fas fa-upload me-3"></i>Sistema de Processamento Multi-SQLite</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="alert alert-info border-0 mb-4" style="background: rgba(102, 126, 234, 0.2); border-radius: 15px;">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-lightbulb me-3 fs-4" style="color: #ffd700;"></i>
                                <div>
                                    <strong>Formato:</strong> <code class="bg-dark px-2 py-1 rounded">url:user:pass</code>
                                    <br><small class="text-muted">Exemplo: <code class="bg-dark px-2 py-1 rounded">https://site.com:usuario:senha</code></small>
                                </div>
                            </div>
                        </div>

                        <form method="post" enctype="multipart/form-data" onsubmit="showLoading()">
                            <div class="mb-4">
                                <label class="form-label fw-bold text-white">
                                    <i class="fas fa-cloud-upload-alt me-2"></i>
                                    Selecionar Arquivos (.txt/.zip/.rar)
                                </label>
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file1" accept=".txt,.rar,.zip" id="file1">
                                            <label for="file1" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 1
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file2" accept=".txt,.rar,.zip" id="file2">
                                            <label for="file2" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 2
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file3" accept=".txt,.rar,.zip" id="file3">
                                            <label for="file3" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 3
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file4" accept=".txt,.rar,.zip" id="file4">
                                            <label for="file4" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 4
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <label for="filename" class="form-label fw-bold text-white">
                                    <i class="fas fa-tag me-2"></i>Nome do arquivo final
                                </label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="filename" name="filename" 
                                           placeholder="resultado_final" value="resultado_final">
                                    <span class="input-group-text bg-transparent" style="border-color: rgba(255,255,255,0.3);">
                                        .txt
                                    </span>
                                </div>
                            </div>

                            <div class="d-grid">
                                <button type="submit" class="btn btn-system btn-processing btn-lg py-3">
                                    <i class="fas fa-rocket me-3"></i>🚀 Processar Arquivos
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Downloads -->
            <div class="tab-pane fade" id="downloads">
                <div class="system-card">
                    <div style="background: var(--success); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-white mb-0"><i class="fas fa-download me-3"></i>Sistema de Downloads</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/download" class="btn btn-system btn-download btn-lg w-100 py-3">
                                        <i class="fas fa-download me-2"></i>💾 Download Completo
                                    </a>
                                    <small class="text-muted d-block mt-2">Todas as linhas do SQLite principal</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/filter-br" class="btn btn-system btn-filter btn-lg w-100 py-3">
                                        <i class="fas fa-flag me-2"></i>🇧🇷 Filtrar URLs .BR
                                    </a>
                                    <small class="text-muted d-block mt-2">Do SQLite brasileiro</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/download-all-dbs" class="btn btn-system btn-convert btn-lg w-100 py-3">
                                        <i class="fas fa-database me-2"></i>📦 Pack Completo SQLites
                                    </a>
                                    <small class="text-muted d-block mt-2">Todos os 4 bancos em ZIP</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/download-domains" class="btn btn-system btn-visualize btn-lg w-100 py-3">
                                        <i class="fas fa-globe me-2"></i>🌐 Relatório Domínios
                                    </a>
                                    <small class="text-muted d-block mt-2">Lista de domínios únicos</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Configurações -->
            <div class="tab-pane fade" id="settings">
                <div class="system-card">
                    <div style="background: var(--danger); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-white mb-0"><i class="fas fa-cog me-3"></i>Gerenciamento de SQLites</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/clear-data" class="btn btn-system btn-visualize btn-lg w-100 py-3" 
                                       onclick="return confirm('⚠️ Excluir TODOS os SQLites e dados deste IP?')">
                                        <i class="fas fa-trash-alt me-2"></i>🗑️ Limpar Todos SQLites
                                    </a>
                                    <small class="text-muted d-block mt-2">Remove todos os 4 bancos do seu IP</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-convert btn-lg w-100 py-3" onclick="showSystemInfo()">
                                        <i class="fas fa-info-circle me-2"></i>ℹ️ Info SQLites
                                    </button>
                                    <small class="text-muted d-block mt-2">Estrutura dos bancos</small>
                                </div>
                            </div>
                        </div>
                        
                        <div id="systemInfo" style="display: none;" class="alert alert-dark border-0 mt-4" style="background: rgba(52, 58, 64, 0.8); border-radius: 15px;">
                            <h5 class="text-light"><i class="fas fa-server me-2"></i>Sistema Multi-SQLite v4.0</h5>
                            <ul class="text-muted mb-0">
                                <li>🗄️ <strong>main.db:</strong> Todas as credenciais processadas</li>
                                <li>📊 <strong>stats.db:</strong> Estatísticas e contadores</li>
                                <li>🇧🇷 <strong>brazilian.db:</strong> URLs brasileiras filtradas</li>
                                <li>🌐 <strong>domains.db:</strong> Domínios únicos e contagens</li>
                                <li>⏰ <strong>Auto-limpeza:</strong> 30 min de inatividade</li>
                                <li>🔒 <strong>Isolamento:</strong> 1 IP = 1 conjunto de SQLites</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function showLoading() {
            document.getElementById('loadingOverlay').style.display = 'flex';
        }
        
        function switchTab(tabName) {
            const tabElement = document.querySelector('#' + tabName + '-tab');
            const tab = new bootstrap.Tab(tabElement);
            tab.show();
        }
        
        function showSystemInfo() {
            const infoElement = document.getElementById('systemInfo');
            infoElement.style.display = infoElement.style.display === 'none' ? 'block' : 'none';
        }

        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                const label = document.querySelector(`label[for="${this.id}"]`);
                if (this.files[0]) {
                    label.innerHTML = `<i class="fas fa-file-check mb-2 d-block" style="color: #28a745;"></i>${this.files[0].name}`;
                    label.style.borderColor = '#28a745';
                    label.style.background = 'rgba(40, 167, 69, 0.1)';
                } else {
                    const fileNumber = this.id.slice(-1);
                    label.innerHTML = `<i class="fas fa-file-plus mb-2 d-block"></i>Arquivo ${fileNumber}`;
                    label.style.borderColor = 'rgba(138, 43, 226, 0.4)';
                    label.style.background = 'rgba(20, 20, 35, 0.6)';
                }
            });
        });
    </script>
</body>
</html>
"""

def extrair_arquivo_comprimido(file):
    try:
        print(f"➤ Extraindo arquivo: {file.filename}")
        linhas = []
        
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(file.read()), 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith('.txt'):
                        with zip_ref.open(file_info) as txt_file:
                            content = txt_file.read().decode('utf-8', errors='ignore')
                            linhas.extend(content.splitlines())
        elif file.filename.lower().endswith('.rar'):
            try:
                content = file.read().decode('utf-8', errors='ignore')
                linhas.extend(content.splitlines())
            except:
                print(f"✗ Erro no arquivo RAR: {file.filename}")
                return []
        else:  # .txt
            content = file.read().decode('utf-8', errors='ignore')
            linhas.extend(content.splitlines())
        
        print(f"✓ Extraído: {len(linhas)} linhas de {file.filename}")
        return linhas
        
    except Exception as e:
        print(f"✗ Erro ao extrair {file.filename}: {str(e)[:50]}")
        return []

def linha_valida(linha):
    if not linha or len(linha.strip()) == 0:
        return False
    
    linha = linha.strip()
    
    if linha.startswith('"') and linha.endswith('"'):
        linha = linha[1:-1].strip()
    
    if len(linha) > 200 or len(linha) < 5:
        return False
    
    if any(c in linha for c in ['==', '++', '--', '&&', '||', 'Bearer ', 'Token ', 'JWT']):
        return False
    
    if any(linha.lower().startswith(s) for s in ['android://', 'content://', 'ftp://', 'file://', 'market://']):
        return False
    
    if ':' not in linha:
        return False
    
    partes = linha.split(':')
    
    if linha.startswith('https://') and len(partes) >= 4:
        url = ':'.join(partes[:-2])
        user, password = partes[-2].strip(), partes[-1].strip()
        return bool(url and user and password and '.' in url)
    
    elif linha.startswith('http://') and len(partes) >= 3:
        url = ':'.join(partes[:-2])
        user, password = partes[-2].strip(), partes[-1].strip()
        return bool(url and user and password and '.' in url)
    
    elif len(partes) == 3:
        url, user, password = partes[0].strip(), partes[1].strip(), partes[2].strip()
        return bool(url and user and password and '.' in url and not url.startswith('/') and '//' not in url)
    
    return False

def filtrar_urls_brasileiras(linhas):
    print("➤ Filtrando URLs brasileiras...")
    urls_brasileiras = []
    
    br_patterns = ['.br', '.com.br', '.org.br', '.gov.br', '.edu.br', 'uol.com', 'globo.com', 
                  'brasil', 'brazil', 'itau', 'bradesco', 'nubank', 'correios', 'detran']
    
    for linha in linhas:
        linha_limpa = linha.strip()
        url_parte = linha_limpa.split(':')[0] if ':' in linha_limpa else linha_limpa
        
        if any(pattern in url_parte.lower() for pattern in br_patterns):
            urls_brasileiras.append(linha_limpa)
    
    print(f"✓ Filtrado: {len(urls_brasileiras)} URLs brasileiras")
    return urls_brasileiras

@app.route("/", methods=["GET", "POST"])
def upload_file():
    user_ip = get_user_ip()
    session = get_user_session(user_ip)
    ip_hash = get_ip_hash(user_ip)
    
    if request.method == "POST":
        try:
            print(f"➤ Processamento iniciado para IP: {ip_hash}")
            
            filename = request.form.get("filename", "resultado_final").strip() or "resultado_final"
            
            arquivos_processados = []
            total_filtradas = 0
            
            for i in range(1, 5):
                file = request.files.get(f"file{i}")
                if file and file.filename and file.filename.lower().endswith((".txt", ".rar", ".zip")):
                    try:
                        content = extrair_arquivo_comprimido(file)
                        if not content:
                            continue
                            
                        print(f"➤ Validando linhas de {file.filename}...")
                        
                        # Processa em lotes para evitar sobrecarga de memória
                        batch_size = 1000
                        filtradas = []
                        total_valid = 0
                        
                        # Abre conexões SQLite uma vez
                        conn = sqlite3.connect(session['databases']['main'])
                        conn_domains = sqlite3.connect(session['databases']['domains'])
                        cursor = conn.cursor()
                        cursor_domains = conn_domains.cursor()
                        
                        for i in range(0, len(content), batch_size):
                            batch = content[i:i + batch_size]
                            batch_filtradas = []
                            
                            # Filtra batch atual
                            for linha in batch:
                                linha_limpa = linha.strip()
                                if linha_limpa and linha_valida(linha_limpa):
                                    batch_filtradas.append(linha_limpa)
                            
                            # Salva batch no SQLite
                            batch_data = []
                            domains_data = set()
                            
                            for linha in batch_filtradas:
                                try:
                                    partes = linha.split(':')
                                    if linha.startswith(('https://', 'http://')):
                                        url = ':'.join(partes[:-2])
                                        username, password = partes[-2], partes[-1]
                                    else:
                                        url, username, password = partes[0], partes[1], partes[2]

                                    batch_data.append((url, username, password, linha))
                                    
                                    # Extrai domínio
                                    try:
                                        if url.startswith(('http://', 'https://')):
                                            domain = urlparse(url).netloc
                                        else:
                                            domain = url.split('/')[0]
                                        domains_data.add(domain)
                                    except:
                                        pass
                                except:
                                    continue
                            
                            # Insert em lote para credenciais
                            if batch_data:
                                cursor.executemany('''
                                INSERT INTO credentials (url, username, password, linha_completa)
                                VALUES (?, ?, ?, ?)
                                ''', batch_data)
                            
                            # Insert em lote para domínios
                            for domain in domains_data:
                                cursor_domains.execute('''
                                INSERT OR IGNORE INTO domains (domain) VALUES (?)
                                ''', (domain,))
                                cursor_domains.execute('''
                                UPDATE domains SET count = count + 1 WHERE domain = ?
                                ''', (domain,))
                            
                            total_valid += len(batch_filtradas)
                            filtradas.extend(batch_filtradas)
                            
                            # Commit periodicamente
                            if i % (batch_size * 5) == 0:
                                conn.commit()
                                conn_domains.commit()
                                print(f"   ⚡ Processadas {i + len(batch):,}/{len(content):,} linhas...")
                        
                        # Commit final
                        conn.commit()
                        conn_domains.commit()
                        conn.close()
                        conn_domains.close()
                        
                        print(f"   ✅ Total válidas: {total_valid:,}")
                        
                        # Processa URLs brasileiras
                        urls_br = filtrar_urls_brasileiras(filtradas)
                        if urls_br:
                            conn_br = sqlite3.connect(session['databases']['brazilian'])
                            cursor_br = conn_br.cursor()
                            for url_br in urls_br:
                                cursor_br.execute('''
                                INSERT INTO brazilian_urls (url, linha_completa) VALUES (?, ?)
                                ''', (url_br.split(':')[0], url_br))
                            conn_br.commit()
                            conn_br.close()
                        
                        total_filtradas += total_valid
                        taxa = (total_valid / len(content) * 100) if content else 0
                        print(f"✓ {file.filename}: {total_valid} válidas ({taxa:.1f}%)")
                        arquivos_processados.append(f"{file.filename} ({total_valid} válidas)")
                        
                    except Exception as e:
                        print(f"✗ Erro em {file.filename}: {str(e)[:50]}")
                        arquivos_processados.append(f"{file.filename} (erro)")
            
            # Atualiza estatísticas
            update_stats(ip_hash, total_filtradas)
            
            # Conta domínios únicos
            try:
                conn = sqlite3.connect(session['databases']['domains'])
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM domains')
                unique_domains = cursor.fetchone()[0]
                session['stats']['domains'] = unique_domains
                
                # Atualiza URLs brasileiras
                conn_br = sqlite3.connect(session['databases']['brazilian'])
                cursor_br = conn_br.cursor()
                cursor_br.execute('SELECT COUNT(*) FROM brazilian_urls')
                br_count = cursor_br.fetchone()[0]
                session['stats']['brazilian_urls'] = br_count
                
                # Atualiza stats no banco
                conn_stats = sqlite3.connect(session['databases']['stats'])
                cursor_stats = conn_stats.cursor()
                cursor_stats.execute('''
                UPDATE stats SET unique_domains = ?, brazilian_urls = ? WHERE id = 1
                ''', (unique_domains, br_count))
                conn_stats.commit()
                conn_stats.close()
                conn_br.close()
                conn.close()
            except:
                pass
            
            print(f"✓ Processamento concluído para IP {ip_hash}: {total_filtradas} linhas")
            
            if not arquivos_processados:
                return """
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head><meta charset="utf-8"><title>Erro</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet"></head>
                <body><div class="container mt-5"><div class="alert alert-warning">
                <h4>❌ Nenhum Arquivo</h4><p>Selecione pelo menos um arquivo válido.</p>
                </div><a href="/" class="btn btn-secondary">← Voltar</a></div></body></html>
                """
            
            lista_arquivos = "<br>".join([f"✅ {arq}" for arq in arquivos_processados])
            return f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head><meta charset="utf-8"><title>✅ Concluído</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <style>body{{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;}}</style></head>
            <body><div class="container py-5"><div class="row justify-content-center"><div class="col-lg-8">
            <div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1); border-radius: 20px;">
            <div class="card-body text-center p-5">
            <i class="fas fa-rocket fs-1 mb-4" style="color: #38ef7d;"></i>
            <h2 class="text-white mb-4">🎉 Dados Salvos em SQLites!</h2>
            <div class="alert alert-success border-0" style="background: rgba(56, 239, 125, 0.2); border-radius: 15px;">
            <h5 class="text-white">📁 Arquivos Processados:</h5><div class="mt-3 text-start">{lista_arquivos}</div></div>
            <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2); border-radius: 15px;">
            <h5 class="text-white">🗄️ SQLites Criados:</h5>
            <ul class="text-start text-white">
                <li>main.db - {total_filtradas} credenciais</li>
                <li>stats.db - estatísticas atualizadas</li>
                <li>brazilian.db - URLs .br filtradas</li>
                <li>domains.db - domínios únicos</li>
            </ul></div>
            <div class="row g-3 my-4"><div class="col-md-6">
            <div class="p-3 rounded-3" style="background: rgba(56, 239, 125, 0.2);">
            <h6 class="text-white">Processadas</h6><h4 class="text-white">{total_filtradas:,}</h4></div></div>
            <div class="col-md-6"><div class="p-3 rounded-3" style="background: rgba(102, 126, 234, 0.2);">
            <h6 class="text-white">IP Session</h6><h4 class="text-white">{ip_hash}</h4></div></div></div>
            <div class="d-grid gap-3 d-md-flex justify-content-md-center">
            <a href="/" class="btn btn-success btn-lg">🏠 Página Principal</a>
            <a href="/download-all-dbs" class="btn btn-outline-light btn-lg">📦 Baixar Todos SQLites</a>
            </div></div></div></div></div></div></body></html>
            """
            
        except Exception as e:
            print(f"✗ Erro geral no processamento: {str(e)[:100]}")
            return "Erro interno no servidor", 500

    # Renderiza página principal com estatísticas do IP real
    stats = session['stats']
    page_content = html_form.replace('USER_REAL_IP', user_ip)
    page_content = page_content.replace('USER_IP_HASH', ip_hash)
    page_content = page_content.replace('USER_TOTAL_LINES', f"{stats['total_lines']:,}")
    page_content = page_content.replace('USER_VALID_LINES', f"{stats['valid_lines']:,}")
    page_content = page_content.replace('USER_BRAZILIAN_URLS', f"{stats['brazilian_urls']:,}")
    page_content = page_content.replace('USER_DOMAINS', f"{stats['domains']:,}")
    
    print(f"🌐 Renderizando página para IP real: {user_ip} (Hash: {ip_hash})")
    return page_content

@app.route("/download")
def download():
    user_ip = get_user_ip()
    session = get_user_session(user_ip)
    
    try:
        conn = sqlite3.connect(session['databases']['main'])
        cursor = conn.cursor()
        cursor.execute('SELECT linha_completa FROM credentials')
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return "❌ Nenhuma linha processada", 404
        
        linhas = [row[0] for row in results]
        file_content = "\n".join(linhas)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        print(f"✓ Download preparado: {len(linhas)} linhas do SQLite principal")
        
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
        
        threading.Timer(30.0, cleanup).start()
        return send_file(tmp_path, as_attachment=True, download_name="resultado_completo.txt")
        
    except Exception as e:
        print(f"✗ Erro no download: {e}")
        return "❌ Erro ao gerar download", 500

@app.route("/filter-br")
def filter_br():
    user_ip = get_user_ip()
    session = get_user_session(user_ip)
    ip_hash = get_ip_hash(user_ip)
    
    try:
        conn = sqlite3.connect(session['databases']['brazilian'])
        cursor = conn.cursor()
        cursor.execute('SELECT linha_completa FROM brazilian_urls')
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head><meta charset="utf-8"><title>Filtro BR</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet"></head>
            <body style="background: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%); min-height: 100vh;">
            <div class="container py-5"><div class="card text-center" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
            <div class="card-body p-5"><h2 class="text-white mb-4">🇧🇷 Filtro Brasileiro</h2>
            <div class="alert alert-warning"><strong>❌ Nenhuma URL brasileira no SQLite</strong></div>
            <a href="/" class="btn btn-light btn-lg">🏠 Página Principal</a></div></div></div></body></html>
            """

        linhas_br = [row[0] for row in results]
        file_content = "\n".join(linhas_br)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
        
        threading.Timer(30.0, cleanup).start()
        return send_file(tmp_path, as_attachment=True, download_name=f"urls_brasileiras_{ip_hash}.txt")

    except Exception as e:
        print(f"✗ Erro no filtro brasileiro: {e}")
        return "❌ Erro ao processar filtro", 500

@app.route("/download-all-dbs")
def download_all_dbs():
    user_ip = get_user_ip()
    session = get_user_session(user_ip)
    ip_hash = get_ip_hash(user_ip)
    
    try:
        # Cria ZIP com todos os SQLites
        zip_path = os.path.join(tempfile.gettempdir(), f"sqlites_{ip_hash}.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for db_name, db_path in session['databases'].items():
                if os.path.exists(db_path):
                    zip_file.write(db_path, f"{db_name}.db")
        
        print(f"✓ Pack SQLites criado para IP {ip_hash}")
        
        def cleanup():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except:
                pass
        
        threading.Timer(60.0, cleanup).start()
        return send_file(zip_path, as_attachment=True, download_name=f"pack_sqlites_{ip_hash}.zip")
        
    except Exception as e:
        print(f"✗ Erro ao criar pack SQLites: {e}")
        return "❌ Erro ao criar pack", 500

@app.route("/download-domains")
def download_domains():
    user_ip = get_user_ip()
    session = get_user_session(user_ip)
    
    try:
        conn = sqlite3.connect(session['databases']['domains'])
        cursor = conn.cursor()
        cursor.execute('SELECT domain, count FROM domains ORDER BY count DESC')
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return "❌ Nenhum domínio processado", 404
        
        content = "DOMÍNIO:QUANTIDADE\n"
        for domain, count in results:
            content += f"{domain}:{count}\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass
        
        threading.Timer(30.0, cleanup).start()
        return send_file(tmp_path, as_attachment=True, download_name="relatorio_dominios.txt")
        
    except Exception as e:
        print(f"✗ Erro no relatório de domínios: {e}")
        return "❌ Erro ao gerar relatório", 500

@app.route("/clear-data")
def clear_data():
    user_ip = get_user_ip()
    ip_hash = get_ip_hash(user_ip)
    
    try:
        # Remove todos os bancos SQLite do IP
        if ip_hash in IP_SESSIONS:
            db_dir = os.path.dirname(IP_SESSIONS[ip_hash]['databases']['main'])
            if os.path.exists(db_dir):
                import shutil
                shutil.rmtree(db_dir)
            
            # Cancela timer de limpeza
            if ip_hash in CLEANUP_TIMERS:
                CLEANUP_TIMERS[ip_hash].cancel()
                del CLEANUP_TIMERS[ip_hash]
            
            # Remove da memória
            del IP_SESSIONS[ip_hash]
        
        print(f"✓ Limpeza manual realizada para IP {ip_hash}")
        
        return f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head><meta charset="utf-8"><title>🗑️ Limpo</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>body{{background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); min-height: 100vh;}}</style></head>
        <body><div class="container py-5"><div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
        <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ff6b6b 0%, #ee5a52 100%);">
        <h1 class="text-white"><i class="fas fa-trash-alt me-3"></i>🗑️ SQLites Limpos</h1></div>
        <div class="card-body text-center p-4">
        <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2);">
        <strong>✅ Todos os 4 SQLites removidos</strong><br>
        <small>main.db • stats.db • brazilian.db • domains.db</small></div>
        <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2);">
        <strong>🔄 IP {ip_hash}:</strong> Pronto para novos dados</div>
        <a href="/" class="btn btn-success btn-lg">🏠 Reiniciar Sistema</a>
        </div></div></div></body></html>
        """
        
    except Exception as e:
        print(f"✗ Erro na limpeza: {e}")
        return "❌ Erro ao limpar dados", 500

# Limpeza periódica de IPs inativos
def cleanup_inactive_ips():
    """Remove IPs inativos periodicamente"""
    while True:
        try:
            now = datetime.now()
            inactive_ips = []
            
            for ip_hash, session_data in IP_SESSIONS.items():
                if now - session_data['last_activity'] > timedelta(minutes=30):
                    inactive_ips.append(ip_hash)
            
            for ip_hash in inactive_ips:
                try:
                    db_dir = os.path.dirname(IP_SESSIONS[ip_hash]['databases']['main'])
                    if os.path.exists(db_dir):
                        import shutil
                        shutil.rmtree(db_dir)
                    
                    if ip_hash in CLEANUP_TIMERS:
                        CLEANUP_TIMERS[ip_hash].cancel()
                        del CLEANUP_TIMERS[ip_hash]
                    
                    del IP_SESSIONS[ip_hash]
                    print(f"✓ Limpeza automática: IP {ip_hash} removido por inatividade")
                except:
                    pass
                    
        except:
            pass
        
        time.sleep(600)  # Verifica a cada 10 minutos

# Inicia thread de limpeza
cleanup_thread = threading.Thread(target=cleanup_inactive_ips, daemon=True)
cleanup_thread.start()

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
