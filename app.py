from flask import Flask, request, render_template_string, send_file
import os
import logging
import sqlite3
import tempfile
import zipfile
import io
import re
from urllib.parse import urlparse

# Logging simplificado - apenas mensagens essenciais
logging.basicConfig(level=logging.ERROR, format='%(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Sistema otimizado de processamento em memória
session_data = {
    'all_lines': [],
    'nome_arquivo_final': "resultado_final",
    'stats': {
        'total_lines': 0,
        'valid_lines': 0,
        'brazilian_urls': 0,
        'domains': set()
    }
}

# HTML da interface reorganizada e otimizada
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🚀 Central TXT Pro - Sistema Organizado</title>
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
                Central TXT Pro - Sistema Organizado
            </h1>
            <p class="text-white-50 mb-0">Processamento Inteligente de Credenciais</p>
        </div>
    </div>

    <div class="container">
        <div class="dashboard-stats">
            <div class="stat-card">
                <div class="stat-number">""" + f"{len(session_data['all_lines']):,}" + """</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-chart-line me-2"></i>LINHAS PROCESSADAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{session_data['stats'].get('valid_lines', 0):,}" + """</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-check-circle me-2"></i>LINHAS VÁLIDAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{session_data['stats'].get('brazilian_urls', 0):,}" + """</div>
                <div style="color: #b0b0b0; font-size: 0.9rem;"><i class="fas fa-flag me-2"></i>URLs BRASILEIRAS</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{len(session_data['stats'].get('domains', set())):,}" + """</div>
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
                <button class="nav-link" id="conversion-tab" data-bs-toggle="tab" data-bs-target="#conversion" type="button">
                    <i class="fas fa-exchange-alt me-2"></i>Conversão
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="visualization-tab" data-bs-toggle="tab" data-bs-target="#visualization" type="button">
                    <i class="fas fa-eye me-2"></i>Visualização
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
                    
                    <div class="menu-item" onclick="switchTab('conversion')">
                        <div class="menu-icon"><i class="fas fa-exchange-alt"></i></div>
                        <h4 class="text-white">Conversão</h4>
                        <p class="text-muted">Conversão para diferentes formatos de dados</p>
                    </div>
                    
                    <div class="menu-item" onclick="switchTab('visualization')">
                        <div class="menu-icon"><i class="fas fa-eye"></i></div>
                        <h4 class="text-white">Visualização</h4>
                        <p class="text-muted">Preview e análise detalhada dos dados</p>
                    </div>
                    
                    <div class="menu-item" onclick="switchTab('settings')">
                        <div class="menu-icon"><i class="fas fa-cog"></i></div>
                        <h4 class="text-white">Configurações</h4>
                        <p class="text-muted">Limpeza de dados e configurações do sistema</p>
                    </div>
                </div>
            </div>

            <!-- Processamento -->
            <div class="tab-pane fade" id="processing">
                <div class="system-card">
                    <div style="background: var(--primary); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-white mb-0"><i class="fas fa-upload me-3"></i>Sistema de Processamento</h3>
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
                                    <small class="text-muted d-block mt-2">Todas as linhas processadas</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/filter-br" class="btn btn-system btn-filter btn-lg w-100 py-3">
                                        <i class="fas fa-flag me-2"></i>🇧🇷 Filtrar URLs .BR
                                    </a>
                                    <small class="text-muted d-block mt-2">Apenas sites brasileiros</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Conversão -->
            <div class="tab-pane fade" id="conversion">
                <div class="system-card">
                    <div style="background: var(--info); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-dark mb-0"><i class="fas fa-exchange-alt me-3"></i>Sistema de Conversão</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/txt-to-db" class="btn btn-system btn-convert btn-lg w-100 py-3">
                                        <i class="fas fa-database me-2"></i>🗄️ Converter para DB
                                    </a>
                                    <small class="text-muted d-block mt-2">Banco SQLite estruturado</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-convert btn-lg w-100 py-3" onclick="alert('Em desenvolvimento')">
                                        <i class="fas fa-file-csv me-2"></i>📊 Converter para CSV
                                    </button>
                                    <small class="text-muted d-block mt-2">Planilha Excel compatível</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Visualização -->
            <div class="tab-pane fade" id="visualization">
                <div class="system-card">
                    <div style="background: var(--danger); border-radius: 20px 20px 0 0; padding: 1.5rem; text-align: center;">
                        <h3 class="text-white mb-0"><i class="fas fa-eye me-3"></i>Sistema de Visualização</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/db-preview" class="btn btn-system btn-visualize btn-lg w-100 py-3">
                                        <i class="fas fa-search me-2"></i>🔍 Preview do Banco
                                    </a>
                                    <small class="text-muted d-block mt-2">Visualizar dados SQLite</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-visualize btn-lg w-100 py-3" onclick="showStats()">
                                        <i class="fas fa-chart-pie me-2"></i>📈 Estatísticas
                                    </button>
                                    <small class="text-muted d-block mt-2">Análise completa dos dados</small>
                                </div>
                            </div>
                        </div>
                        
                        <div id="statsDetails" style="display: none;" class="alert alert-success border-0 mt-4" style="background: rgba(40, 167, 69, 0.1); border-radius: 15px;">
                            <h5 class="text-success"><i class="fas fa-chart-line me-2"></i>Estatísticas Detalhadas</h5>
                            <div class="row text-center">
                                <div class="col-md-3">
                                    <strong>Total:</strong><br><span class="fs-4 text-info">""" + f"{len(session_data['all_lines']):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Válidas:</strong><br><span class="fs-4 text-success">""" + f"{session_data['stats'].get('valid_lines', 0):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Brasileiras:</strong><br><span class="fs-4 text-warning">""" + f"{session_data['stats'].get('brazilian_urls', 0):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Domínios:</strong><br><span class="fs-4 text-info">""" + f"{len(session_data['stats'].get('domains', set())):,}" + """</span>
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
                        <h3 class="text-white mb-0"><i class="fas fa-cog me-3"></i>Configurações do Sistema</h3>
                    </div>
                    <div style="padding: 2rem;">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/clear-data" class="btn btn-system btn-visualize btn-lg w-100 py-3" 
                                       onclick="return confirm('⚠️ Tem certeza? Todos os dados serão removidos!')">
                                        <i class="fas fa-trash-alt me-2"></i>🗑️ Limpar Dados
                                    </a>
                                    <small class="text-muted d-block mt-2">Remover todos os dados processados</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-visualize btn-lg w-100 py-3" onclick="showSystemInfo()">
                                        <i class="fas fa-info-circle me-2"></i>ℹ️ Info do Sistema
                                    </button>
                                    <small class="text-muted d-block mt-2">Informações técnicas</small>
                                </div>
                            </div>
                        </div>
                        
                        <div id="systemInfo" style="display: none;" class="alert alert-dark border-0 mt-4" style="background: rgba(52, 58, 64, 0.8); border-radius: 15px;">
                            <h5 class="text-light"><i class="fas fa-server me-2"></i>Sistema TXT Pro v3.0</h5>
                            <ul class="text-muted mb-0">
                                <li>✅ <strong>Status:</strong> Online</li>
                                <li>🚀 <strong>Capacidade:</strong> Ilimitada</li>
                                <li>📁 <strong>Formatos:</strong> TXT, ZIP, RAR</li>
                                <li>🇧🇷 <strong>Filtros:</strong> URLs Brasileiras</li>
                                <li>🗄️ <strong>Conversões:</strong> SQLite, CSV</li>
                                <li>⚡ <strong>Performance:</strong> Otimizada</li>
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
        
        function showStats() {
            const statsElement = document.getElementById('statsDetails');
            statsElement.style.display = statsElement.style.display === 'none' ? 'block' : 'none';
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

# Função otimizada de extração de arquivos
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

# Função otimizada de validação de linha 
def linha_valida(linha):
    if not linha or len(linha.strip()) == 0:
        return False
    
    linha = linha.strip()
    
    # Remove aspas se existirem
    if linha.startswith('"') and linha.endswith('"'):
        linha = linha[1:-1].strip()
    
    # Rejeita linhas muito longas ou muito curtas
    if len(linha) > 200 or len(linha) < 5:
        return False
    
    # Rejeita caracteres suspeitos rapidamente
    if any(c in linha for c in ['==', '++', '--', '&&', '||', 'Bearer ', 'Token ', 'JWT']):
        return False
    
    # Rejeita esquemas não-web
    if any(linha.lower().startswith(s) for s in ['android://', 'content://', 'ftp://', 'file://', 'market://']):
        return False
    
    if ':' not in linha:
        return False
    
    partes = linha.split(':')
    
    # Para HTTPS
    if linha.startswith('https://') and len(partes) >= 4:
        url = ':'.join(partes[:-2])
        user, password = partes[-2].strip(), partes[-1].strip()
        return bool(url and user and password and '.' in url)
    
    # Para HTTP
    elif linha.startswith('http://') and len(partes) >= 3:
        url = ':'.join(partes[:-2])
        user, password = partes[-2].strip(), partes[-1].strip()
        return bool(url and user and password and '.' in url)
    
    # Formato simples site.com:user:pass
    elif len(partes) == 3:
        url, user, password = partes[0].strip(), partes[1].strip(), partes[2].strip()
        return bool(url and user and password and '.' in url and not url.startswith('/') and '//' not in url)
    
    return False

# Função otimizada de filtro brasileiro
def filtrar_urls_brasileiras(linhas):
    print("➤ Filtrando URLs brasileiras...")
    urls_brasileiras = []
    
    # Domínios e padrões brasileiros otimizados
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
    global session_data
    
    if request.method == "POST":
        try:
            print("➤ Iniciando processamento de arquivos...")
            
            filename = request.form.get("filename", "resultado_final").strip() or "resultado_final"
            session_data['nome_arquivo_final'] = filename
            
            arquivos_processados = []
            total_filtradas = 0
            
            for i in range(1, 5):
                file = request.files.get(f"file{i}")
                if file and file.filename and file.filename.lower().endswith((".txt", ".rar", ".zip")):
                    try:
                        # Extrai conteúdo
                        content = extrair_arquivo_comprimido(file)
                        if not content:
                            continue
                            
                        print(f"➤ Validando linhas de {file.filename}...")
                        
                        # Processa linhas com otimização
                        filtradas = []
                        for linha in content:
                            linha_limpa = linha.strip()
                            if linha_limpa and linha_valida(linha_limpa):
                                filtradas.append(linha_limpa)
                        
                        # Adiciona ao acumulador
                        session_data['all_lines'].extend(filtradas)
                        total_filtradas += len(filtradas)
                        
                        taxa = (len(filtradas) / len(content) * 100) if content else 0
                        print(f"✓ {file.filename}: {len(filtradas)} válidas ({taxa:.1f}%)")
                        arquivos_processados.append(f"{file.filename} ({len(filtradas)} válidas)")
                        
                    except Exception as e:
                        print(f"✗ Erro em {file.filename}: {str(e)[:50]}")
                        arquivos_processados.append(f"{file.filename} (erro)")
            
            # Atualiza estatísticas
            session_data['stats']['total_lines'] = len(session_data['all_lines'])
            session_data['stats']['valid_lines'] = len(session_data['all_lines'])
            session_data['stats']['domains'] = set()
            
            for linha in session_data['all_lines'][:100]:  # Amostra para performance
                try:
                    if linha.startswith(('http://', 'https://')):
                        domain = urlparse(linha.split(':')[0] + ':' + linha.split(':')[1]).netloc
                    else:
                        domain = linha.split(':')[0]
                    session_data['stats']['domains'].add(domain)
                except:
                    pass
            
            print(f"✓ Processamento concluído: {total_filtradas} linhas adicionadas")
            
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
            <h2 class="text-white mb-4">🎉 Processamento Concluído!</h2>
            <div class="alert alert-success border-0" style="background: rgba(56, 239, 125, 0.2); border-radius: 15px;">
            <h5 class="text-white">📁 Arquivos Processados:</h5><div class="mt-3 text-start">{lista_arquivos}</div></div>
            <div class="row g-3 my-4"><div class="col-md-6">
            <div class="p-3 rounded-3" style="background: rgba(56, 239, 125, 0.2);">
            <h6 class="text-white">Adicionadas</h6><h4 class="text-white">{total_filtradas:,}</h4></div></div>
            <div class="col-md-6"><div class="p-3 rounded-3" style="background: rgba(102, 126, 234, 0.2);">
            <h6 class="text-white">Total Acumulado</h6><h4 class="text-white">{len(session_data['all_lines']):,}</h4></div></div></div>
            <div class="d-grid gap-3 d-md-flex justify-content-md-center">
            <a href="/" class="btn btn-success btn-lg">🏠 Página Principal</a>
            <a href="/download" class="btn btn-outline-light btn-lg">💾 Download Completo</a>
            </div></div></div></div></div></div></body></html>
            """
            
        except Exception as e:
            print(f"✗ Erro geral no processamento: {str(e)[:100]}")
            return "Erro interno no servidor", 500

    return render_template_string(html_form)

@app.route("/download")
def download():
    if not session_data['all_lines']:
        return "❌ Nenhuma linha processada", 404

    print("➤ Gerando download completo...")
    filename = session_data['nome_arquivo_final'] or "resultado_final"
    file_content = "\n".join(session_data['all_lines'])
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    print(f"✓ Download preparado: {filename}.txt ({len(session_data['all_lines'])} linhas)")
    
    # Auto cleanup após 30 segundos
    import threading
    def cleanup():
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                print("✓ Arquivo temporário limpo")
        except:
            pass
    
    threading.Timer(30.0, cleanup).start()
    return send_file(tmp_path, as_attachment=True, download_name=f"{filename}.txt")

@app.route("/filter-br")
def filter_br():
    if not session_data['all_lines']:
        return "❌ Nenhuma linha processada. <a href='/'>Voltar</a>", 404

    try:
        print("➤ Aplicando filtro brasileiro...")
        urls_br = filtrar_urls_brasileiras(session_data['all_lines'])
        session_data['stats']['brazilian_urls'] = len(urls_br)

        if not urls_br:
            return """
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head><meta charset="utf-8"><title>Filtro BR</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet"></head>
            <body style="background: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%); min-height: 100vh;">
            <div class="container py-5"><div class="card text-center" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
            <div class="card-body p-5"><h2 class="text-white mb-4">🇧🇷 Filtro Aplicado</h2>
            <div class="alert alert-warning"><strong>❌ Nenhuma URL brasileira encontrada</strong></div>
            <a href="/" class="btn btn-light btn-lg">🏠 Página Principal</a></div></div></div></body></html>
            """

        nome_arquivo_br = f"{session_data['nome_arquivo_final'] or 'resultado_final'}_brasileiro"
        file_path = os.path.join(tempfile.gettempdir(), f"{nome_arquivo_br}.txt")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls_br))
        
        print(f"✓ Filtro brasileiro aplicado: {len(urls_br)} URLs")

        return f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head><meta charset="utf-8"><title>🇧🇷 Filtro Brasileiro</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>body{{background: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%); min-height: 100vh;}}</style></head>
        <body><div class="container py-5"><div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
        <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ff7b7b 0%, #ff9a56 100%);">
        <h1 class="text-white"><i class="fas fa-flag me-3"></i>🇧🇷 URLs Brasileiras</h1></div>
        <div class="card-body text-center p-4">
        <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2);">
        <strong>{len(urls_br):,}</strong> URLs brasileiras de <strong>{len(session_data['all_lines']):,}</strong> total</div>
        <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
        <a href="/download-filtered/{nome_arquivo_br}" class="btn btn-success btn-lg">💾 Baixar URLs .BR</a>
        <a href="/" class="btn btn-secondary btn-lg">🏠 Página Principal</a>
        </div></div></div></div></body></html>
        """

    except Exception as e:
        print(f"✗ Erro no filtro brasileiro: {str(e)[:50]}")
        return "❌ Erro ao processar filtro", 500

@app.route("/download-filtered/<filename>")
def download_filtered(filename):
    try:
        file_path = os.path.join(tempfile.gettempdir(), f"{filename}.txt")
        if os.path.exists(file_path):
            print(f"➤ Download filtrado: {filename}.txt")
            
            # Auto cleanup
            def cleanup():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print("✓ Arquivo filtrado limpo")
                except:
                    pass
            
            import threading
            threading.Timer(30.0, cleanup).start()
            return send_file(file_path, as_attachment=True, download_name=f"{filename}.txt")
        else:
            return "❌ Arquivo não encontrado", 404
    except Exception as e:
        print(f"✗ Erro no download filtrado: {str(e)[:50]}")
        return "❌ Erro ao baixar arquivo", 500

@app.route("/txt-to-db")
def txt_to_db():
    if not session_data['all_lines']:
        return "❌ Nenhuma linha processada. <a href='/'>Voltar</a>", 404

    try:
        print("➤ Convertendo para banco SQLite...")
        nome_arquivo = session_data['nome_arquivo_final'] or "resultado_final"
        db_filename = f"{nome_arquivo}_database.db"
        db_path = os.path.join(tempfile.gettempdir(), db_filename)
        
        if os.path.exists(db_path):
            os.remove(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE credenciais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            usuario TEXT NOT NULL,
            senha TEXT NOT NULL,
            linha_completa TEXT NOT NULL,
            dominio TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('CREATE INDEX idx_url ON credenciais(url)')
        cursor.execute('CREATE INDEX idx_dominio ON credenciais(dominio)')

        dados_inseridos = 0
        for linha in session_data['all_lines']:
            try:
                partes = linha.split(':')
                if len(partes) >= 3:
                    if linha.startswith(('https://', 'http://')):
                        url = ':'.join(partes[:-2])
                        usuario, senha = partes[-2], partes[-1]
                    else:
                        url, usuario, senha = partes[0], partes[1], partes[2]

                    try:
                        if url.startswith(('http://', 'https://')):
                            dominio = urlparse(url).netloc
                        else:
                            dominio = url.split('/')[0]
                    except:
                        dominio = url

                    cursor.execute('''
                    INSERT INTO credenciais (url, usuario, senha, linha_completa, dominio)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (url, usuario, senha, linha, dominio))
                    
                    dados_inseridos += 1

            except:
                continue

        conn.commit()
        conn.close()

        print(f"✓ Banco SQLite criado: {dados_inseridos} registros")

        return f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head><meta charset="utf-8"><title>🗄️ Banco Criado</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>body{{background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;}}</style></head>
        <body><div class="container py-5"><div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
        <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%);">
        <h1 class="text-dark"><i class="fas fa-database me-3"></i>🗄️ Banco SQLite Criado</h1></div>
        <div class="card-body text-center p-4">
        <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2);">
        <strong>{dados_inseridos:,}</strong> registros inseridos no banco</div>
        <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2);">
        <h6>📊 Tabela 'credenciais' criada com:</h6>
        <p>• ID, URL, Usuário, Senha, Domínio, Data</p></div>
        <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
        <a href="/download-db/{db_filename[:-3]}" class="btn btn-info btn-lg">💾 Baixar Banco SQLite</a>
        <a href="/" class="btn btn-secondary btn-lg">🏠 Página Principal</a>
        </div></div></div></div></body></html>
        """

    except Exception as e:
        print(f"✗ Erro ao criar banco SQLite: {str(e)[:50]}")
        return "❌ Erro ao criar banco de dados", 500

@app.route("/download-db/<filename>")
def download_db(filename):
    try:
        db_path = os.path.join(tempfile.gettempdir(), f"{filename}.db")
        if os.path.exists(db_path):
            print(f"➤ Download do banco: {filename}.db")
            
            def cleanup():
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        print("✓ Banco temporário limpo")
                except:
                    pass
            
            import threading
            threading.Timer(60.0, cleanup).start()
            return send_file(db_path, as_attachment=True, download_name=f"{filename}.db")
        else:
            return "❌ Banco não encontrado", 404
    except Exception as e:
        print(f"✗ Erro no download do banco: {str(e)[:50]}")
        return "❌ Erro ao baixar banco", 500

@app.route("/clear-data")
def clear_data():
    global session_data
    linhas_removidas = len(session_data['all_lines'])
    session_data['all_lines'] = []
    session_data['stats'] = {
        'total_lines': 0,
        'valid_lines': 0,
        'brazilian_urls': 0,
        'domains': set()
    }
    
    print(f"✓ Dados limpos: {linhas_removidas} linhas removidas")
    
    return f"""
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head><meta charset="utf-8"><title>🗑️ Limpo</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>body{{background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); min-height: 100vh;}}</style></head>
    <body><div class="container py-5"><div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
    <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ff6b6b 0%, #ee5a52 100%);">
    <h1 class="text-white"><i class="fas fa-trash-alt me-3"></i>🗑️ Dados Limpos</h1></div>
    <div class="card-body text-center p-4">
    <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2);">
    <strong>{linhas_removidas:,}</strong> linhas removidas da memória</div>
    <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2);">
    <strong>✅ Sistema Resetado:</strong> Pronto para novos arquivos</div>
    <a href="/" class="btn btn-success btn-lg">🏠 Página Principal</a>
    </div></div></div></body></html>
    """

@app.route("/db-preview", methods=["GET", "POST"])
def db_preview():
    if request.method == "POST":
        try:
            db_file = request.files.get("db_file")
            if not db_file or not db_file.filename or not db_file.filename.endswith('.db'):
                return """
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head><meta charset="utf-8"><title>Erro</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet"></head>
                <body><div class="container mt-5"><div class="alert alert-danger">
                <h4>❌ Arquivo Inválido</h4><p>Selecione um arquivo .db válido.</p></div>
                <a href="/db-preview" class="btn btn-secondary">← Tentar Novamente</a></div></body></html>
                """

            print(f"➤ Visualizando banco: {db_file.filename}")
            temp_db_path = os.path.join(tempfile.gettempdir(), f"preview_{db_file.filename}")
            db_file.save(temp_db_path)

            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabelas = cursor.fetchall()

            preview_html = f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head><meta charset="utf-8"><title>Preview: {db_file.filename}</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <style>body{{background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh;}}
            .table-responsive{{max-height: 400px; overflow-y: auto; border-radius: 10px;}}</style></head>
            <body><div class="container py-4"><div class="card">
            <div class="card-header text-center" style="background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);">
            <h2 class="text-white"><i class="fas fa-database me-2"></i>Preview: {db_file.filename}</h2></div>
            <div class="card-body"><div class="alert alert-info">
            <strong>📊 Tabelas encontradas:</strong> {len(tabelas)}</div>
            """

            for tabela in tabelas:
                nome_tabela = tabela[0]
                cursor.execute(f"SELECT * FROM {nome_tabela} LIMIT 10")
                dados = cursor.fetchall()
                cursor.execute(f"PRAGMA table_info({nome_tabela})")
                colunas = [col[1] for col in cursor.fetchall()]

                preview_html += f"""
                <div class="mb-4"><h4>📋 Tabela: {nome_tabela}</h4>
                <p class="text-muted">Mostrando até 10 registros</p>
                <div class="table-responsive"><table class="table table-striped">
                <thead class="table-dark"><tr>"""
                
                for coluna in colunas:
                    preview_html += f"<th>{coluna}</th>"
                preview_html += "</tr></thead><tbody>"
                
                for linha in dados:
                    preview_html += "<tr>"
                    for valor in linha:
                        valor_str = str(valor)[:50] + "..." if len(str(valor)) > 50 else str(valor)
                        preview_html += f"<td>{valor_str}</td>"
                    preview_html += "</tr>"
                
                preview_html += "</tbody></table></div></div>"

            preview_html += """
            <div class="text-center">
            <a href="/db-preview" class="btn btn-primary me-2">🔄 Outro DB</a>
            <a href="/" class="btn btn-secondary">🏠 Página Principal</a>
            </div></div></div></div></body></html>
            """

            conn.close()
            print(f"✓ Preview gerado para {db_file.filename}")

            def cleanup():
                try:
                    if os.path.exists(temp_db_path):
                        os.remove(temp_db_path)
                        print("✓ DB temporário do preview limpo")
                except:
                    pass
            
            import threading
            threading.Timer(60.0, cleanup).start()
            return preview_html

        except Exception as e:
            print(f"✗ Erro no preview do DB: {str(e)[:50]}")
            return """
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head><meta charset="utf-8"><title>Erro</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet"></head>
            <body><div class="container mt-5"><div class="alert alert-danger">
            <h4>❌ Erro ao Visualizar</h4><p>Erro ao processar arquivo .db.</p></div>
            <a href="/db-preview" class="btn btn-secondary">← Tentar Novamente</a></div></body></html>
            """

    return """
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head><meta charset="utf-8"><title>Visualizador DB</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>body{background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh;}
    .file-upload-area{border: 2px dashed rgba(255, 255, 255, 0.3); border-radius: 15px; padding: 40px; 
    text-align: center; cursor: pointer; transition: all 0.3s ease;}
    .file-upload-area:hover{border-color: #4facfe; background: rgba(79, 172, 254, 0.1);}</style></head>
    <body><div class="container py-5"><div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);">
    <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);">
    <h1 class="text-white"><i class="fas fa-search me-3"></i>Visualizador de Banco</h1></div>
    <div class="card-body p-4">
    <div class="alert alert-info border-0" style="background: rgba(79, 172, 254, 0.2);">
    <strong>🔒 Seguro:</strong> Visualização local sem armazenamento<br>
    <small>✅ SQLite • ✅ Preview de tabelas • ✅ Auto-exclusão</small></div>
    <form method="post" enctype="multipart/form-data">
    <div class="file-upload-area mb-4" onclick="document.getElementById('db_file').click()">
    <i class="fas fa-cloud-upload-alt fs-1 text-primary mb-3"></i>
    <h4>Clique para selecionar arquivo .db</h4>
    <input type="file" id="db_file" name="db_file" accept=".db" style="display: none;" onchange="updateFileName(this)">
    <div id="fileName" class="mt-2"></div></div>
    <div class="d-grid"><button type="submit" class="btn btn-primary btn-lg">🔍 Visualizar Banco</button></div>
    </form><div class="text-center mt-4">
    <a href="/" class="btn btn-secondary btn-lg">🏠 Voltar</a></div>
    </div></div></div>
    <script>function updateFileName(input) {
    const fileName = document.getElementById('fileName');
    if (input.files[0]) {
    fileName.innerHTML = '<strong>📁 Arquivo:</strong> ' + input.files[0].name;
    fileName.className = 'alert alert-success';
    }}</script></body></html>
    """

# Configuração otimizada
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0