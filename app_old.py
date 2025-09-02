from flask import Flask, request, render_template_string, send_file, jsonify, Response
import os
import logging
import sqlite3
import tempfile
import zipfile
import io
import re
import time # Import time for cleanup_old_temp_files
from collections import Counter

# Configure logging reduzido
logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Sistema de processamento em memória - sem arquivos salvos
session_data = {
    'all_lines': [],
    'nome_arquivo_final': "resultado_final",
    'last_processed': None,
    'stats': {
        'total_lines': 0,
        'valid_lines': 0,
        'brazilian_urls': 0,
        'domains': {}
    }
}

# HTML da interface com sistema de menus organizados
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🚀 Central de Processamento TXT Pro</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --warning-gradient: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%);
            --info-gradient: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            --danger-gradient: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        }
        
        body {
            background: 
                radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 119, 198, 0.2) 0%, transparent 50%),
                linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f0f23 75%, #000000 100%);
            min-height: 100vh;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                repeating-linear-gradient(
                    90deg,
                    transparent 0,
                    transparent 98px,
                    rgba(68, 68, 68, 0.03) 100px
                ),
                repeating-linear-gradient(
                    0deg,
                    transparent 0,
                    transparent 98px,
                    rgba(68, 68, 68, 0.03) 100px
                );
            pointer-events: none;
            z-index: -1;
        }
        
        .main-header {
            background: var(--primary-gradient);
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
            position: relative;
            overflow: hidden;
        }
        
        .nav-tabs .nav-link:hover {
            background: rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .nav-tabs .nav-link.active {
            background: var(--primary-gradient);
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
        
        .system-card-header {
            background: var(--primary-gradient);
            border-radius: 20px 20px 0 0;
            padding: 1.5rem;
            text-align: center;
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
        
        .stat-label {
            font-size: 0.9rem;
            color: #b0b0b0;
            text-transform: uppercase;
            letter-spacing: 1px;
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
            position: relative;
            overflow: hidden;
        }
        
        .menu-item:before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: var(--primary-gradient);
            opacity: 0;
            transform: rotate(45deg);
            transition: all 0.3s ease;
            z-index: -1;
        }
        
        .menu-item:hover:before {
            opacity: 0.1;
        }
        
        .menu-item:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 35px rgba(138, 43, 226, 0.4);
            border-color: rgba(138, 43, 226, 0.6);
        }
        
        .menu-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: var(--primary-gradient);
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
            position: relative;
            overflow: hidden;
            margin: 0.5rem;
        }
        
        .btn-system:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .btn-processing { background: var(--primary-gradient); }
        .btn-download { background: var(--success-gradient); }
        .btn-filter { background: var(--warning-gradient); }
        .btn-convert { background: var(--info-gradient); color: #333; }
        .btn-visualize { background: var(--secondary-gradient); }
        .btn-settings { background: var(--danger-gradient); }
        
        .form-control {
            background: rgba(20, 20, 35, 0.8);
            border: 1px solid rgba(138, 43, 226, 0.3);
            border-radius: 12px;
            transition: all 0.3s ease;
            color: #e0e0e0;
        }
        
        .form-control:focus {
            background: rgba(30, 30, 50, 0.9);
            border-color: #8a2be2;
            box-shadow: 0 0 20px rgba(138, 43, 226, 0.5);
        }
        
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
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
            box-shadow: 0 5px 15px rgba(138, 43, 226, 0.3);
            transform: translateY(-2px);
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
        
        .loading-content {
            text-align: center;
            color: white;
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
        
        .tab-content {
            background: rgba(20, 20, 35, 0.6);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid rgba(138, 43, 226, 0.3);
            backdrop-filter: blur(10px);
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div class="progress-text">🔄 Processando...</div>
            <div class="progress-detail">Aguarde enquanto processamos seus dados</div>
        </div>
    </div>

    <!-- Header Principal -->
    <div class="main-header">
        <div class="container">
            <h1 class="text-white mb-2">
                <i class="fas fa-rocket me-3"></i>
                Central de Processamento TXT Pro
            </h1>
            <p class="text-white-50 mb-0">Sistema Completo de Processamento Inteligente de Credenciais</p>
        </div>
    </div>

    <div class="container">
        <!-- Dashboard de Estatísticas -->
        <div class="dashboard-stats">
            <div class="stat-card">
                <div class="stat-number">""" + f"{len(session_data['all_lines']):,}" + """</div>
                <div class="stat-label"><i class="fas fa-chart-line me-2"></i>Linhas Processadas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{session_data['stats'].get('valid_lines', 0):,}" + """</div>
                <div class="stat-label"><i class="fas fa-check-circle me-2"></i>Linhas Válidas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{session_data['stats'].get('brazilian_urls', 0):,}" + """</div>
                <div class="stat-label"><i class="fas fa-flag me-2"></i>URLs Brasileiras</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{len(session_data['stats'].get('domains', {})):,}" + """</div>
                <div class="stat-label"><i class="fas fa-globe me-2"></i>Domínios Únicos</div>
            </div>
        </div>

        <!-- Sistema de Navegação por Abas -->
        <ul class="nav nav-tabs" id="systemTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="dashboard-tab" data-bs-toggle="tab" data-bs-target="#dashboard" type="button">
                    <i class="fas fa-tachometer-alt me-2"></i>Dashboard
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="processing-tab" data-bs-toggle="tab" data-bs-target="#processing" type="button">
                    <i class="fas fa-upload me-2"></i>Processamento
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="downloads-tab" data-bs-toggle="tab" data-bs-target="#downloads" type="button">
                    <i class="fas fa-download me-2"></i>Downloads
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="conversion-tab" data-bs-toggle="tab" data-bs-target="#conversion" type="button">
                    <i class="fas fa-exchange-alt me-2"></i>Conversão
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="visualization-tab" data-bs-toggle="tab" data-bs-target="#visualization" type="button">
                    <i class="fas fa-eye me-2"></i>Visualização
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="settings-tab" data-bs-toggle="tab" data-bs-target="#settings" type="button">
                    <i class="fas fa-cog me-2"></i>Configurações
                </button>
            </li>
        </ul>

        <!-- Conteúdo das Abas -->
        <div class="tab-content" id="systemTabContent">
            
            <!-- Dashboard -->
            <div class="tab-pane fade show active" id="dashboard">
                <div class="row">
                    <div class="col-12">
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
                </div>
            </div>

            <!-- Processamento de Arquivos -->
            <div class="tab-pane fade" id="processing">
                <div class="system-card">
                    <div class="system-card-header">
                        <h3 class="text-white mb-0"><i class="fas fa-upload me-3"></i>Sistema de Processamento de Arquivos</h3>
                    </div>
                    <div class="card-body p-4">
                        <div class="alert alert-info border-0 mb-4" style="background: rgba(102, 126, 234, 0.2); border-radius: 15px;">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-lightbulb me-3 fs-4" style="color: #ffd700;"></i>
                                <div>
                                    <strong>Formato esperado:</strong> <code class="bg-dark px-2 py-1 rounded">url:user:pass</code>
                                    <br><small class="text-muted">
                                        <i class="fas fa-arrow-right me-1"></i> Exemplo: <code class="bg-dark px-2 py-1 rounded">https://site.com/login:usuario:senha</code>
                                    </small>
                                </div>
                            </div>
                        </div>

                        <form method="post" enctype="multipart/form-data" onsubmit="showLoading()">
                            <div class="mb-4">
                                <label class="form-label fw-bold text-white">
                                    <i class="fas fa-cloud-upload-alt me-2" style="color: #667eea;"></i>
                                    Selecione até 4 arquivos (.txt/.rar/.zip)
                                </label>
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file1" accept=".txt,.rar,.zip" id="file1">
                                            <label for="file1" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 1 (.txt/.rar/.zip)
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file2" accept=".txt,.rar,.zip" id="file2">
                                            <label for="file2" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 2 (.txt/.rar/.zip)
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file3" accept=".txt,.rar,.zip" id="file3">
                                            <label for="file3" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 3 (.txt/.rar/.zip)
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file4" accept=".txt,.rar,.zip" id="file4">
                                            <label for="file4" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 4 (.txt/.rar/.zip)
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <label for="filename" class="form-label fw-bold text-white">
                                    <i class="fas fa-tag me-2" style="color: #667eea;"></i>
                                    Nome do arquivo final
                                </label>
                                <div class="input-group">
                                    <span class="input-group-text bg-transparent border-end-0" style="border-color: rgba(255,255,255,0.3);">
                                        <i class="fas fa-file-signature"></i>
                                    </span>
                                    <input type="text" class="form-control border-start-0" id="filename" name="filename" 
                                           placeholder="resultado_final" value="resultado_final"
                                           style="border-color: rgba(255,255,255,0.3);">
                                    <span class="input-group-text bg-transparent border-start-0" style="border-color: rgba(255,255,255,0.3);">
                                        .txt
                                    </span>
                                </div>
                                <small class="text-muted">💡 Arquivo manterá TODAS as linhas válidas processadas</small>
                            </div>

                            <div class="d-grid">
                                <button type="submit" class="btn btn-system btn-processing btn-lg py-3">
                                    <i class="fas fa-rocket me-3"></i>
                                    🚀 Processar Arquivos
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Downloads e Filtros -->
            <div class="tab-pane fade" id="downloads">
                <div class="system-card">
                    <div class="system-card-header">
                        <h3 class="text-white mb-0"><i class="fas fa-download me-3"></i>Sistema de Downloads e Filtros</h3>
                    </div>
                    <div class="card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/download" class="btn btn-system btn-download btn-lg w-100 py-3">
                                        <i class="fas fa-download me-2"></i>
                                        💾 Download Completo
                                    </a>
                                    <small class="text-muted d-block mt-2">Baixar todas as linhas processadas</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/filter-br" class="btn btn-system btn-filter btn-lg w-100 py-3">
                                        <i class="fas fa-flag me-2"></i>
                                        🇧🇷 Filtrar URLs .BR
                                    </a>
                                    <small class="text-muted d-block mt-2">Apenas credenciais de sites brasileiros</small>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4" style="border-color: rgba(138, 43, 226, 0.3);">
                        
                        <div class="alert alert-warning border-0" style="background: rgba(255, 193, 7, 0.1); border-radius: 15px;">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-info-circle me-3 fs-4" style="color: #ffc107;"></i>
                                <div>
                                    <strong>Filtros Disponíveis:</strong>
                                    <ul class="mb-0 mt-2">
                                        <li>Download Completo: Todas as linhas válidas processadas</li>
                                        <li>Filtro .BR: URLs com domínios brasileiros (.br, .com.br, etc)</li>
                                        <li>Detecção Inteligente: Sites brasileiros populares sem domínio .br</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Conversão de Dados -->
            <div class="tab-pane fade" id="conversion">
                <div class="system-card">
                    <div class="system-card-header">
                        <h3 class="text-white mb-0"><i class="fas fa-exchange-alt me-3"></i>Sistema de Conversão de Dados</h3>
                    </div>
                    <div class="card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/txt-to-db" class="btn btn-system btn-convert btn-lg w-100 py-3">
                                        <i class="fas fa-database me-2"></i>
                                        🗄️ Converter para DB
                                    </a>
                                    <small class="text-muted d-block mt-2">Converter dados para banco SQLite</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-convert btn-lg w-100 py-3" onclick="alert('Em breve: Conversão para CSV')">
                                        <i class="fas fa-file-csv me-2"></i>
                                        📊 Converter para CSV
                                    </button>
                                    <small class="text-muted d-block mt-2">Exportar dados em formato CSV</small>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4" style="border-color: rgba(138, 43, 226, 0.3);">
                        
                        <div class="alert alert-info border-0" style="background: rgba(102, 126, 234, 0.1); border-radius: 15px;">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-magic me-3 fs-4" style="color: #667eea;"></i>
                                <div>
                                    <strong>Formatos de Conversão:</strong>
                                    <ul class="mb-0 mt-2">
                                        <li><strong>SQLite DB:</strong> Banco de dados estruturado para consultas avançadas</li>
                                        <li><strong>CSV:</strong> Planilha compatível com Excel e outros editores</li>
                                        <li><strong>JSON:</strong> Formato para APIs e desenvolvimento web</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Visualização -->
            <div class="tab-pane fade" id="visualization">
                <div class="system-card">
                    <div class="system-card-header">
                        <h3 class="text-white mb-0"><i class="fas fa-eye me-3"></i>Sistema de Visualização e Análise</h3>
                    </div>
                    <div class="card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/db-preview" class="btn btn-system btn-visualize btn-lg w-100 py-3">
                                        <i class="fas fa-search me-2"></i>
                                        🔍 Preview do Banco
                                    </a>
                                    <small class="text-muted d-block mt-2">Visualizar dados do banco SQLite</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-visualize btn-lg w-100 py-3" onclick="showStats()">
                                        <i class="fas fa-chart-pie me-2"></i>
                                        📈 Estatísticas Detalhadas
                                    </button>
                                    <small class="text-muted d-block mt-2">Análise completa dos dados processados</small>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4" style="border-color: rgba(138, 43, 226, 0.3);">
                        
                        <div id="statsDetails" style="display: none;" class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.1); border-radius: 15px;">
                            <h5 class="text-success"><i class="fas fa-chart-line me-2"></i>Estatísticas Detalhadas</h5>
                            <div class="row">
                                <div class="col-md-3">
                                    <strong>Total de Linhas:</strong><br>
                                    <span class="fs-4 text-info">""" + f"{len(session_data['all_lines']):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Linhas Válidas:</strong><br>
                                    <span class="fs-4 text-success">""" + f"{session_data['stats'].get('valid_lines', 0):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>URLs Brasileiras:</strong><br>
                                    <span class="fs-4 text-warning">""" + f"{session_data['stats'].get('brazilian_urls', 0):,}" + """</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Domínios Únicos:</strong><br>
                                    <span class="fs-4 text-info">""" + f"{len(session_data['stats'].get('domains', {})):,}" + """</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Configurações -->
            <div class="tab-pane fade" id="settings">
                <div class="system-card">
                    <div class="system-card-header">
                        <h3 class="text-white mb-0"><i class="fas fa-cog me-3"></i>Configurações do Sistema</h3>
                    </div>
                    <div class="card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="text-center">
                                    <a href="/clear-data" class="btn btn-system btn-settings btn-lg w-100 py-3" 
                                       onclick="return confirm('⚠️ Tem certeza que deseja limpar todos os dados processados?')">
                                        <i class="fas fa-trash-alt me-2"></i>
                                        🗑️ Limpar Dados
                                    </a>
                                    <small class="text-muted d-block mt-2">Remover todas as linhas processadas</small>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="text-center">
                                    <button class="btn btn-system btn-settings btn-lg w-100 py-3" onclick="showSystemInfo()">
                                        <i class="fas fa-info-circle me-2"></i>
                                        ℹ️ Informações do Sistema
                                    </button>
                                    <small class="text-muted d-block mt-2">Detalhes técnicos do sistema</small>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4" style="border-color: rgba(138, 43, 226, 0.3);">
                        
                        <div id="systemInfo" style="display: none;" class="alert alert-dark border-0" style="background: rgba(52, 58, 64, 0.8); border-radius: 15px;">
                            <h5 class="text-light"><i class="fas fa-server me-2"></i>Informações do Sistema</h5>
                            <ul class="text-muted mb-0">
                                <li><strong>Versão:</strong> TXT Pro v2.0</li>
                                <li><strong>Capacidade:</strong> Sem limite de linhas</li>
                                <li><strong>Formatos Suportados:</strong> TXT, ZIP, RAR</li>
                                <li><strong>Filtros:</strong> URLs Brasileiras</li>
                                <li><strong>Conversões:</strong> SQLite, CSV, JSON</li>
                                <li><strong>Status:</strong> <span class="text-success">Online ✅</span></li>
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
            if (statsElement.style.display === 'none') {
                statsElement.style.display = 'block';
            } else {
                statsElement.style.display = 'none';
            }
        }
        
        function showSystemInfo() {
            const infoElement = document.getElementById('systemInfo');
            if (infoElement.style.display === 'none') {
                infoElement.style.display = 'block';
            } else {
                infoElement.style.display = 'none';
            }
        }

        // Atualiza labels dos arquivos quando selecionados
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                const label = document.querySelector(`label[for="${this.id}"]`);
                if (this.files[0]) {
                    label.innerHTML = `<i class="fas fa-file-check mb-2 d-block" style="color: #28a745;"></i>${this.files[0].name}`;
                    label.style.borderColor = '#28a745';
                    label.style.background = 'rgba(40, 167, 69, 0.1)';
                } else {
                    const fileNumber = this.id.slice(-1);
                    label.innerHTML = `<i class="fas fa-file-plus mb-2 d-block"></i>Arquivo ${fileNumber} (.txt/.rar/.zip)`;
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
    """Extrai conteúdo de arquivos .zip (simples implementação)"""
    linhas = []
    try:
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(file.read()), 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith('.txt'):
                        with zip_ref.open(file_info) as txt_file:
                            content = txt_file.read().decode('utf-8', errors='ignore')
                            linhas.extend(content.splitlines())
        elif file.filename.lower().endswith('.rar'):
            # Para .rar, vamos tentar ler como se fosse texto (fallback)
            try:
                content = file.read().decode('utf-8', errors='ignore')
                linhas.extend(content.splitlines())
            except:
                app.logger.warning(f"Não foi possível processar arquivo RAR: {file.filename}")
                return []
        else:  # .txt
            content = file.read().decode('utf-8', errors='ignore')
            linhas.extend(content.splitlines())
    except Exception as e:
        app.logger.error(f"Erro ao extrair arquivo {file.filename}: {e}")
        return []

    return linhas

def filtrar_urls_brasileiras(linhas):
    """Filtra URLs brasileiras usando detecção avançada"""
    urls_brasileiras = []

    # Domínios brasileiros conhecidos
    dominios_br = [
        '.br', '.com.br', '.org.br', '.net.br', '.gov.br', '.edu.br',
        '.mil.br', '.art.br', '.rec.br', '.esp.br', '.etc.br'
    ]

    # Sites/empresas brasileiros populares (sem .br)
    sites_brasileiros = [
        'uol.com', 'globo.com', 'terra.com.br', 'ig.com.br', 'bol.com.br',
        'abril.com.br', 'estadao.com.br', 'folha.uol.com.br', 'g1.globo.com',
        'mercadolivre.com.br', 'mercadolibre.com.br', 'americanas.com.br',
        'magazineluiza.com.br', 'casasbahia.com.br', 'pontofrio.com.br',
        'submarino.com.br', 'shoptime.com.br', 'extra.com.br',
        'itau.com.br', 'bradesco.com.br', 'bb.com.br', 'santander.com.br',
        'caixa.gov.br', 'nubank.com.br', 'inter.co', 'picpay.com',
        'correios.com.br', 'cep.com.br', 'viacep.com.br',
        'globoplay.globo.com', 'netflix.com/br', 'primevideo.com',
        'spotify.com/br', 'deezer.com/br',
        'facebook.com/br', 'instagram.com/br', 'whatsapp.com/br',
        'twitter.com/br', 'youtube.com/br', 'tiktok.com/br',
        'linkedin.com/br', 'pinterest.com/br',
        'olx.com.br', 'webmotors.com.br', 'imovelweb.com.br',
        'trivago.com.br', 'booking.com/br', 'decolar.com',
        'latam.com', 'gol.com.br', 'azul.com.br',
        'cpf.receita.fazenda.gov.br', 'detran', 'tse.jus.br',
        'inss.gov.br', 'gov.br', 'receita.fazenda.gov.br'
    ]

    # Palavras-chave brasileiras em URLs/domínios
    palavras_br = [
        'brasil', 'brazil', 'br_', '_br', 'saopaulo', 'riodejaneiro',
        'minasgerais', 'parana', 'bahia', 'goias', 'ceara',
        'pernambuco', 'maranhao', 'paraiba', 'alagoas', 'sergipe',
        'rondonia', 'acre', 'amazonas', 'roraima', 'para', 'amapa',
        'tocantins', 'mato', 'grosso', 'distrito', 'federal',
        'rio_grande', 'santa_catarina', 'espirito_santo'
    ]

    # Bancos e empresas brasileiras (sem domínio específico)
    empresas_br = [
        'itau', 'bradesco', 'santander', 'nubank', 'inter', 'picpay',
        'caixa', 'bb', 'sicoob', 'sicredi', 'banrisul', 'banese',
        'banpara', 'brb', 'banese', 'banestes',
        'petrobras', 'vale', 'embraer', 'ambev', 'jbs', 'brf',
        'magazine', 'luiza', 'americanas', 'submarino', 'casas', 'bahia',
        'ponto', 'frio', 'extra', 'carrefour', 'walmart',
        'globo', 'record', 'sbt', 'band', 'cultura',
        'correios', 'detran', 'receita', 'inss', 'tse', 'trf',
        'tj', 'mp', 'oab', 'crea', 'crc', 'crm'
    ]

    # Códigos DDD brasileiros comuns em URLs (para identificar contatos locais)
    ddd_brasileiros = [
        '011', '012', '013', '014', '015', '016', '017', '018', '019',
        '021', '022', '024', '027', '028',
        '031', '032', '033', '034', '035', '037', '038',
        '041', '042', '043', '044', '045', '046',
        '047', '048', '049',
        '051', '053', '054', '055',
        '061', '062', '064',
        '065', '066',
        '067',
        '068',
        '069',
        '071', '073', '074', '075', '077',
        '079',
        '081', '087',
        '082',
        '083',
        '084',
        '085', '088',
        '086',
        '089',
        '091', '093', '094',
        '092', '097',
        '095',
        '096',
        '098', '099'
    ]

    for linha in linhas:
        linha_limpa = linha.strip()
        url_parte = linha_limpa.split(':')[0] if ':' in linha_limpa else linha_limpa

        eh_brasileiro = False

        # 1. Verifica domínios .br
        if any(dominio in url_parte for dominio in dominios_br):
            eh_brasileiro = True

        # 2. Verifica sites brasileiros conhecidos
        elif any(site in url_parte for site in sites_brasileiros):
            eh_brasileiro = True

        # 3. Verifica palavras-chave brasileiras
        elif any(palavra in url_parte for palavra in palavras_br):
            eh_brasileiro = True

        # 4. Verifica nomes de empresas brasileiras
        elif any(empresa in url_parte for empresa in empresas_br):
            eh_brasileiro = True

        # 5. Padrões específicos brasileiros
        elif any(padrao in url_parte for padrao in [
            'cpf', 'cnpj', 'rg', 'cep', 'pix', 'boleto',
            'cartorio', 'tabeliao', 'delegacia', 'prefeitura',
            'camara', 'assembleia', 'senado', 'congresso',
            'ministerio', 'secretaria', 'anvisa', 'anatel',
            'cvm', 'bacen', 'banco_central', 'susep'
        ]):
            eh_brasileiro = True

        # 6. Códigos DDD brasileiros na URL
        elif any(ddd in url_parte for ddd in ddd_brasileiros):
            eh_brasileiro = True

        if eh_brasileiro:
            urls_brasileiras.append(linha_limpa)  # Adiciona a linha limpa

    return urls_brasileiras

def linha_valida(linha: str) -> bool:
    """Verifica se a linha segue EXATAMENTE o padrão url:user:pass - apenas HTTP/HTTPS"""
    if not linha or not linha.strip():
        return False

    linha = linha.strip()

    # Remove aspas duplas no início e fim se existirem
    if linha.startswith('"') and linha.endswith('"'):
        linha = linha[1:-1]

    # Remove espaços extras
    linha = linha.strip()

    # ❌ REJEITA URLs muito longas (>200 caracteres)
    if len(linha) > 200:
        return False

    # ❌ REJEITA linhas com == ou outros caracteres de token/hash
    caracteres_suspeitos = ['==', '===', '!=', '++', '--', '<<', '>>', '&&', '||', 
                           '#{', '}#', '${', '}$', '[[', ']]', '((', '))', 
                           'Bearer ', 'Token ', 'JWT ', 'OAuth', 'API_KEY',
                           'SECRET_', '_TOKEN', '_KEY', '_HASH']
    
    for suspeito in caracteres_suspeitos:
        if suspeito in linha:
            return False

    # ❌ REJEITA package names (com.algo.app)
    if re.match(r'^[a-z]+\.[a-z]+\.[a-z]+', linha.lower()):
        return False

    # ❌ REJEITA esquemas não-web (android://, content://, etc.)
    esquemas_rejeitados = [
        'android://', 'content://', 'ftp://', 'file://', 'ssh://', 'telnet://', 
        'ldap://', 'ldaps://', 'smtp://', 'pop3://', 'imap://',
        'bluetooth://', 'nfc://', 'sms://', 'tel://', 'mailto:',
        'market://', 'intent://', 'package:', 'app://', 'chrome://',
        'moz-extension://', 'chrome-extension://', 'edge://', 'safari://',
        'data:', 'blob:', 'filesystem:', 'ws://', 'wss://',
        'rtmp://', 'rtsp://', 'magnet:', 'torrent:', 'bitcoin:',
        'ethereum:', 'ipfs://', 'jar:', 'resource:'
    ]

    for esquema in esquemas_rejeitados:
        if linha.lower().startswith(esquema):
            return False

    # ❌ REJEITA linhas que parecem ser tokens/chaves/hashes
    # Detecta sequências muito longas de caracteres alfanuméricos (típico de tokens)
    palavras = linha.split(':')
    for palavra in palavras:
        palavra_limpa = palavra.strip()
        # Se tem mais de 32 caracteres consecutivos sem espaços/pontos, pode ser token
        if len(palavra_limpa) > 32 and palavra_limpa.isalnum():
            return False
        # Se contém base64 típico (termina com = ou ==)
        if palavra_limpa.endswith('=') and len(palavra_limpa) > 20:
            return False

    # Deve conter exatamente 2 dois pontos (:) para formato simples url:user:pass
    # OU começar com http:// ou https:// (que terão mais dois pontos)
    if not ':' in linha:
        return False

    partes = linha.split(':')

    # Para URLs HTTPS (https://site.com:user:pass = 4 partes)
    if linha.startswith('https://'):
        if len(partes) >= 4:
            url = ':'.join(partes[:-2])  # https://site.com
            user = partes[-2].strip()
            password = partes[-1].strip()

            # Valida se URL é web válida E simples
            if (url.startswith('https://') and len(url) > 8 and 
                '.' in url):
                return bool(user and password and len(user) > 0 and len(password) > 0)

    # Para URLs HTTP (http://site.com:user:pass = 3 partes)
    elif linha.startswith('http://'):
        if len(partes) >= 3:
            url = ':'.join(partes[:-2])  # http://site.com
            user = partes[-2].strip()
            password = partes[-1].strip()

            # Valida se URL é web válida E simples
            if (url.startswith('http://') and len(url) > 7 and 
                '.' in url):
                return bool(user and password and len(user) > 0 and len(password) > 0)

    # Para formato simples sem protocolo (site.com:user:pass = 3 partes)
    elif len(partes) == 3:
        url, user, password = partes[0].strip(), partes[1].strip(), partes[2].strip()

        # Valida se todas as partes têm conteúdo
        if url and user and password and len(url) > 0 and len(user) > 0 and len(password) > 0:
            # URL deve ter pelo menos um ponto (domínio) E não começar com /
            # E não conter caracteres especiais de esquemas complexos
            if ('.' in url and not url.startswith('/') and 
                not '//' in url and
                not ':' in url[url.find('.')+1:]): # Evita : dentro do domínio ou user/pass escapados
                return True

    return False

@app.route("/", methods=["GET", "POST"])
def upload_file():
    global session_data
    if request.method == "POST":
        try:
            # Pega o nome do arquivo final e salva na sessão
            filename = request.form.get("filename", "resultado_final").strip()
            if not filename:
                filename = "resultado_final"
            session_data['nome_arquivo_final'] = filename

            # Processa múltiplos arquivos
            arquivos_processados = []
            total_filtradas = 0

            for i in range(1, 5):  # file1, file2, file3, file4
                file = request.files.get(f"file{i}")
                if file and file.filename and (file.filename.lower().endswith((".txt", ".rar", ".zip"))):
                    try:
                        # Extrai conteúdo do arquivo (txt, zip ou rar)
                        content = extrair_arquivo_comprimido(file)
                        app.logger.info(f"Arquivo {file.filename} processado com {len(content)} linhas")

                        # filtra linhas válidas
                        filtradas = []
                        linhas_processadas = 0
                        linhas_rejeitadas = 0
                        amostras_rejeitadas = []

                        for linha in content:
                            linha_limpa = linha.strip()
                            if linha_limpa:  # ignora linhas vazias
                                linhas_processadas += 1
                                if linha_valida(linha_limpa):
                                    filtradas.append(linha_limpa)

                                    # Força garbage collection a cada 50k linhas para economizar memória
                                    if len(filtradas) % 50000 == 0:
                                        import gc
                                        gc.collect()
                                    # Log apenas a cada 100k linhas válidas para reduzir spam
                                    if len(filtradas) % 100000 == 0:
                                        app.logger.info(f"Processadas {len(filtradas)} linhas válidas...")
                                else:
                                    linhas_rejeitadas += 1
                                    # Coleta amostras de linhas rejeitadas para debug
                                    if len(amostras_rejeitadas) < 10:
                                        amostras_rejeitadas.append(linha_limpa[:100])  # Primeiros 100 chars

                        # Log detalhado com estatísticas
                        taxa_validacao = (len(filtradas) / linhas_processadas * 100) if linhas_processadas > 0 else 0
                        app.logger.info(f"📁 {file.filename}:")
                        app.logger.info(f"   📊 Total lidas: {len(content):,}")
                        app.logger.info(f"   ✅ Válidas: {len(filtradas):,} ({taxa_validacao:.1f}%)")
                        app.logger.info(f"   ❌ Rejeitadas: {linhas_rejeitadas:,}")

                        # Log amostras de linhas rejeitadas para debug
                        if amostras_rejeitadas:
                            app.logger.info(f"   🔍 Amostras rejeitadas:")
                            for i, amostra in enumerate(amostras_rejeitadas[:5], 1):
                                app.logger.info(f"      {i}. {amostra}")

                        # Se a taxa de validação estiver muito baixa, alerta
                        if taxa_validacao < 5 and len(content) > 10000:
                            app.logger.warning(f"⚠️ Taxa de validação baixa ({taxa_validacao:.1f}%) para {file.filename}")
                            app.logger.warning(f"   Possível formato não suportado ou dados corrompidos")

                        # adiciona ao acumulador
                        linhas_antes = len(session_data['all_lines'])
                        session_data['all_lines'].extend(filtradas)
                        total_filtradas += len(filtradas)
                        arquivos_processados.append(f"{file.filename} ({len(filtradas)} válidas)")

                    except Exception as e:
                        app.logger.error(f"Erro ao processar arquivo {file.filename}: {e}")
                        arquivos_processados.append(f"{file.filename} (erro)")

            app.logger.info(f"Total acumulado: {len(session_data['all_lines'])}")

            if not arquivos_processados:
                # Nenhum arquivo foi enviado
                error_html = """
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Erro no Upload</title>
                    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
                </head>
                <body>
                    <div class="container mt-5">
                        <div class="row justify-content-center">
                            <div class="col-md-8 col-lg-6">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <div class="alert alert-warning" role="alert">
                                            <i class="fas fa-exclamation-triangle me-2 fs-4"></i>
                                            <h4 class="alert-heading">Nenhum Arquivo</h4>
                                            <p class="mb-0">Selecione pelo menos um arquivo .txt para processar</p>
                                        </div>

                                        <a href="/" class="btn btn-secondary">
                                            <i class="fas fa-arrow-left me-2"></i>
                                            Tentar Novamente
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                return error_html

            # Armazena o nome do arquivo escolhido para usar no download
            global nome_arquivo_final
            nome_arquivo_final = filename

            # Atualiza estatísticas
            session_data['stats']['total_lines'] = len(session_data['all_lines'])
            session_data['stats']['valid_lines'] = len(session_data['all_lines'])

            # Mensagem de sucesso
            lista_arquivos = "<br>".join([f"✅ {arq}" for arq in arquivos_processados])
            success_html = f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>🎉 Processamento Concluído!</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
                <style>
                    body {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }}
                    .success-card {{
                        backdrop-filter: blur(10px);
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 20px;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                        animation: slideUp 0.5s ease-out;
                    }}
                    @keyframes slideUp {{
                        from {{ transform: translateY(30px); opacity: 0; }}
                        to {{ transform: translateY(0); opacity: 1; }}
                    }}
                    .btn-gradient {{
                        background: linear-gradient(45deg, #11998e 0%, #38ef7d 100%);
                        border: none;
                        transition: all 0.3s ease;
                    }}
                    .btn-gradient:hover {{
                        transform: scale(1.05);
                        box-shadow: 0 8px 25px rgba(17, 153, 142, 0.4);
                    }}
                    .success-icon {{
                        animation: bounce 2s infinite;
                    }}
                    @keyframes bounce {{
                        0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                        40% {{ transform: translateY(-10px); }}
                        60% {{ transform: translateY(-5px); }}
                    }}
                </style>
            </head>
            <body>
                <div class="loading-overlay" id="loadingOverlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 9999;">
                    <div style="text-align: center; color: white;">
                        <div style="width: 60px; height: 60px; border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
                        <div style="font-size: 18px; margin-bottom: 10px;">🔄 Preparando download completo...</div>
                        <div style="font-size: 14px; opacity: 0.8;">Compilando todas as linhas processadas</div>
                    </div>
                </div>
                <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>

                <div class="container py-5">
                    <div class="row justify-content-center">
                        <div class="col-lg-8">
                            <div class="card success-card">
                                <div class="card-body text-center p-5">
                                    <div class="success-icon mb-4">
                                        <i class="fas fa-rocket fs-1" style="color: #38ef7d;"></i>
                                    </div>
                                    <h2 class="text-white mb-4">🎉 Processamento Concluído!</h2>

                                    <div class="alert alert-success border-0" style="background: rgba(56, 239, 125, 0.2); border-radius: 15px;">
                                        <h5 class="text-white">📁 Arquivos Processados:</h5>
                                        <div class="mt-3 text-start">
                                            {lista_arquivos}
                                        </div>
                                    </div>

                                    <div class="row g-3 my-4">
                                        <div class="col-md-6">
                                            <div class="p-3 rounded-3" style="background: rgba(56, 239, 125, 0.2);">
                                                <i class="fas fa-plus-circle mb-2" style="color: #38ef7d;"></i>
                                                <h6 class="text-white">Adicionadas</h6>
                                                <h4 class="text-white">{total_filtradas:,}</h4>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="p-3 rounded-3" style="background: rgba(102, 126, 234, 0.2);">
                                                <i class="fas fa-database mb-2" style="color: #667eea;"></i>
                                                <h6 class="text-white">Total Acumulado</h6>
                                                <h4 class="text-white">{len(session_data['all_lines']):,}</h4>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="d-grid gap-3 d-md-flex justify-content-md-center">
                                        <a href="/" class="btn btn-gradient btn-lg">
                                            <i class="fas fa-home me-2"></i>
                                            Página Principal
                                        </a>
                                        <a href="/download" class="btn btn-outline-light btn-lg" onclick="showLoading()">
                                            <i class="fas fa-download me-2"></i>
                                            💾 Download Completo
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <script>
                    function showLoading() {{
                        document.getElementById('loadingOverlay').style.display = 'flex';
                    }}
                </script>
            </body>
            </html>
            """
            return success_html

        except Exception as e:
            app.logger.error(f"Erro no processamento: {e}")
            return "Erro interno no servidor", 500

    return render_template_string(html_form)

@app.route("/download")
def download():
    """Download do arquivo final compilado"""
    global session_data

    if not session_data['all_lines']:
        return "Nenhuma linha processada ainda", 404

    filename = session_data['nome_arquivo_final'] or "resultado_final"
    
    # Cria arquivo em memória
    file_content = "\n".join(session_data['all_lines'])
    
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    # Agenda limpeza do arquivo após o download
    def cleanup_file():
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                app.logger.info(f"Arquivo temporário removido: {filename}.txt")
        except Exception as cleanup_error:
            app.logger.error(f"Erro ao limpar arquivo temporário: {cleanup_error}")

    import threading
    timer = threading.Timer(30.0, cleanup_file)
    timer.start()

    return send_file(tmp_path, as_attachment=True, download_name=f"{filename}.txt")

@app.route("/filter-br")
def filter_br():
    """Filtro para URLs brasileiras"""
    global session_data
    
    if not session_data['all_lines']:
        return "Nenhuma linha processada ainda. <a href='/'>Voltar</a>", 404

    try:
        # Aplica filtro brasileiro
        urls_br = filtrar_urls_brasileiras(session_data['all_lines'])
        
        # Atualiza estatísticas
        session_data['stats']['brazilian_urls'] = len(urls_br)

        if not urls_br:
            return render_template_string("""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Filtro .BR</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            </head>
            <body style="background: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%); min-height: 100vh;">
                <div class="container py-5">
                    <div class="row justify-content-center">
                        <div class="col-lg-8">
                            <div class="card" style="backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1); border-radius: 20px;">
                                <div class="card-body text-center p-5">
                                    <i class="fas fa-flag fs-1 mb-4" style="color: #28a745;"></i>
                                    <h2 class="text-white mb-4">🇧🇷 Filtro Aplicado</h2>
                                    <div class="alert alert-warning">
                                        <i class="fas fa-info-circle me-2"></i>
                                        <strong>Nenhuma URL brasileira encontrada</strong> nos dados processados
                                    </div>
                                    <a href="/" class="btn btn-light btn-lg">
                                        <i class="fas fa-home me-2"></i>
                                        Página Principal
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """)

        # Salva URLs brasileiras em arquivo temporário
        nome_arquivo = session_data['nome_arquivo_final'] or "resultado_final"
        nome_arquivo_br = f"{nome_arquivo}_brasileiro"
        
        file_path = os.path.join(tempfile.gettempdir(), f"{nome_arquivo_br}.txt")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls_br))
        
        app.logger.info(f"Arquivo brasileiro criado: {nome_arquivo_br}.txt com {len(urls_br)} URLs")

        return render_template_string(f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>🇧🇷 Filtro Brasileiro</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{
                    background: linear-gradient(135deg, #ff7b7b 0%, #ff9a56 100%);
                    min-height: 100vh;
                }}
                .main-card {{
                    backdrop-filter: blur(10px);
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container py-5">
                <div class="row justify-content-center">
                    <div class="col-lg-8">
                        <div class="card main-card">
                            <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ff7b7b 0%, #ff9a56 100%);">
                                <h1 class="card-title mb-2 text-white">
                                    <i class="fas fa-flag me-3"></i>🇧🇷 URLs Brasileiras
                                </h1>
                                <p class="mb-0 text-white-50">Filtro aplicado com sucesso</p>
                            </div>
                            <div class="card-body p-4 text-center">
                                <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2); border-radius: 15px;">
                                    <i class="fas fa-check-circle me-2 fs-4"></i>
                                    <strong>{len(urls_br):,}</strong> URLs brasileiras encontradas de <strong>{len(session_data['all_lines']):,}</strong> total
                                </div>

                                <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
                                    <a href="/download-filtered/{nome_arquivo_br}" class="btn btn-success btn-lg">
                                        <i class="fas fa-download me-2"></i>
                                        Baixar URLs .BR
                                    </a>
                                    <a href="/" class="btn btn-secondary btn-lg">
                                        <i class="fas fa-home me-2"></i>
                                        Página Principal
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)

    except Exception as e:
        app.logger.error(f"Erro ao criar arquivo de URLs brasileiras: {e}")
        return "Erro ao processar filtro", 500

@app.route("/download-filtered/<filename>")
def download_filtered(filename):
    """Download do arquivo de URLs filtradas"""
    try:
        file_path = os.path.join(tempfile.gettempdir(), f"{filename}.txt")
        if os.path.exists(file_path):
            # Agenda limpeza do arquivo após o download
            def cleanup_file():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        app.logger.info(f"Arquivo filtrado temporário removido: {filename}.txt")
                except Exception as cleanup_error:
                    app.logger.error(f"Erro ao limpar arquivo filtrado: {cleanup_error}")

            import threading
            timer = threading.Timer(30.0, cleanup_file)
            timer.start()

            return send_file(file_path, as_attachment=True, download_name=f"{filename}.txt")
        else:
            return "Arquivo não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar arquivo filtrado: {e}")
        return "Erro ao baixar arquivo", 500

@app.route("/txt-to-db")
def txt_to_db():
    """Converte dados processados para SQLite"""
    global session_data
    
    if not session_data['all_lines']:
        return "Nenhuma linha processada ainda. <a href='/'>Voltar</a>", 404

    try:
        # Cria arquivo de banco temporário
        nome_arquivo = session_data['nome_arquivo_final'] or "resultado_final"
        db_filename = f"{nome_arquivo}_database.db"
        db_path = os.path.join(tempfile.gettempdir(), db_filename)
        
        # Remove arquivo existente se houver
        if os.path.exists(db_path):
            os.remove(db_path)

        # Cria banco SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Cria tabela de credenciais
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

        # Cria índices para melhor performance
        cursor.execute('CREATE INDEX idx_url ON credenciais(url)')
        cursor.execute('CREATE INDEX idx_dominio ON credenciais(dominio)')

        # Insere dados
        dados_inseridos = 0
        for linha in session_data['all_lines']:
            try:
                # Parse da linha
                partes = linha.split(':')
                if len(partes) >= 3:
                    if linha.startswith('https://'):
                        url = ':'.join(partes[:-2])
                        usuario = partes[-2]
                        senha = partes[-1]
                    elif linha.startswith('http://'):
                        url = ':'.join(partes[:-2])
                        usuario = partes[-2]
                        senha = partes[-1]
                    else:
                        url, usuario, senha = partes[0], partes[1], partes[2]

                    # Extrai domínio
                    dominio = ""
                    try:
                        if url.startswith(('http://', 'https://')):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            dominio = parsed.netloc
                        else:
                            dominio = url.split('/')[0]
                    except:
                        dominio = url

                    cursor.execute('''
                    INSERT INTO credenciais (url, usuario, senha, linha_completa, dominio)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (url, usuario, senha, linha, dominio))
                    
                    dados_inseridos += 1

            except Exception as parse_error:
                app.logger.warning(f"Erro ao processar linha: {linha[:50]}... - {parse_error}")

        conn.commit()
        conn.close()

        app.logger.info(f"Banco SQLite criado: {db_filename} com {dados_inseridos} registros")

        return render_template_string(f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>🗄️ Conversão para Banco</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .main-card {{
                    backdrop-filter: blur(10px);
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container py-5">
                <div class="row justify-content-center">
                    <div class="col-lg-8">
                        <div class="card main-card">
                            <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ffecd2 0%, #fcb69f 100%);">
                                <h1 class="card-title mb-2 text-dark">
                                    <i class="fas fa-database me-3"></i>🗄️ Banco SQLite Criado
                                </h1>
                                <p class="mb-0 text-dark">Conversão concluída com sucesso</p>
                            </div>
                            <div class="card-body p-4 text-center">
                                <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2); border-radius: 15px;">
                                    <i class="fas fa-check-circle me-2 fs-4"></i>
                                    <strong>{dados_inseridos:,}</strong> registros inseridos no banco de dados
                                </div>

                                <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2); border-radius: 15px;">
                                    <h6><i class="fas fa-table me-2"></i>Estrutura da Tabela 'credenciais':</h6>
                                    <ul class="list-unstyled text-start mb-0">
                                        <li>• <strong>id:</strong> Chave primária</li>
                                        <li>• <strong>url:</strong> URL do site</li>
                                        <li>• <strong>usuario:</strong> Nome de usuário</li>
                                        <li>• <strong>senha:</strong> Senha</li>
                                        <li>• <strong>dominio:</strong> Domínio extraído da URL</li>
                                        <li>• <strong>criado_em:</strong> Timestamp da inserção</li>
                                    </ul>
                                </div>

                                <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
                                    <a href="/download-db/{db_filename[:-3]}" class="btn btn-info btn-lg">
                                        <i class="fas fa-download me-2"></i>
                                        💾 Baixar Banco SQLite
                                    </a>
                                    <a href="/" class="btn btn-secondary btn-lg">
                                        <i class="fas fa-home me-2"></i>
                                        Página Principal
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)

    except Exception as e:
        app.logger.error(f"Erro ao criar banco SQLite: {e}")
        return "Erro ao criar banco de dados", 500

@app.route("/download-db/<filename>")
def download_db(filename):
    """Download do arquivo de banco SQLite"""
    try:
        db_path = os.path.join(tempfile.gettempdir(), f"{filename}.db")
        if os.path.exists(db_path):
            # Agenda limpeza do arquivo após o download
            def cleanup_file():
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        app.logger.info(f"Banco SQLite temporário removido: {filename}.db")
                except Exception as cleanup_error:
                    app.logger.error(f"Erro ao limpar banco SQLite: {cleanup_error}")

            import threading
            timer = threading.Timer(60.0, cleanup_file) # 60 segundos para download do banco
            timer.start()

            return send_file(db_path, as_attachment=True, download_name=f"{filename}.db")
        else:
            return "Banco de dados não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar banco: {e}")
        return "Erro ao baixar banco", 500

@app.route("/clear-data")
def clear_data():
    """Limpa todos os dados processados"""
    global session_data
    
    # Limpa dados da sessão
    linhas_removidas = len(session_data['all_lines'])
    session_data['all_lines'] = []
    session_data['stats'] = {
        'total_lines': 0,
        'valid_lines': 0,
        'brazilian_urls': 0,
        'domains': {}
    }
    
    app.logger.info(f"Dados limpos: {linhas_removidas} linhas removidas")
    
    return render_template_string(f"""
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>🗑️ Dados Limpos</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                min-height: 100vh;
            }}
            .main-card {{
                backdrop-filter: blur(10px);
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="card main-card">
                        <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #ff6b6b 0%, #ee5a52 100%);">
                            <h1 class="card-title mb-2 text-white">
                                <i class="fas fa-trash-alt me-3"></i>🗑️ Dados Limpos
                            </h1>
                            <p class="mb-0 text-white-50">Sistema resetado com sucesso</p>
                        </div>
                        <div class="card-body p-4 text-center">
                            <div class="alert alert-success border-0" style="background: rgba(40, 167, 69, 0.2); border-radius: 15px;">
                                <i class="fas fa-check-circle me-2 fs-4"></i>
                                <strong>{linhas_removidas:,}</strong> linhas foram removidas da memória
                            </div>
                            
                            <div class="alert alert-info border-0" style="background: rgba(23, 162, 184, 0.2); border-radius: 15px;">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Sistema Resetado:</strong> Pronto para processar novos arquivos
                            </div>

                            <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
                                <a href="/" class="btn btn-success btn-lg">
                                    <i class="fas fa-home me-2"></i>
                                    Página Principal
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/db-preview", methods=["GET", "POST"])
def db_preview():
    """Visualizador de arquivos .db"""
    if request.method == "POST":
        try:
            db_file = request.files.get("db_file")
            if not db_file or not db_file.filename or not db_file.filename.endswith('.db'):
                return render_template_string("""
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head>
                    <meta charset="utf-8">
                    <title>Erro - Visualizador DB</title>
                    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                </head>
                <body>
                    <div class="container mt-5">
                        <div class="alert alert-danger">
                            <h4>Arquivo Inválido</h4>
                            <p>Por favor, selecione um arquivo .db válido.</p>
                        </div>
                        <a href="/db-preview" class="btn btn-secondary">Tentar Novamente</a>
                    </div>
                </body>
                </html>
                """)

            # Salva arquivo temporariamente
            temp_db_path = os.path.join(tempfile.gettempdir(), f"preview_{db_file.filename}")
            db_file.save(temp_db_path)

            # Conecta ao banco e obtém informações
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            # Lista tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabelas = cursor.fetchall()

            preview_html = f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <title>Preview: {db_file.filename}</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
                <style>
                    body {{
                        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                        min-height: 100vh;
                    }}
                    .table-responsive {{
                        max-height: 400px;
                        overflow-y: auto;
                        border-radius: 10px;
                    }}
                    .table {{
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(5px);
                    }}
                </style>
            </head>
            <body>
                <div class="container py-4">
                    <div class="card">
                        <div class="card-header text-center" style="background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);">
                            <h2 class="text-white mb-0">
                                <i class="fas fa-database me-2"></i>
                                Preview: {db_file.filename}
                            </h2>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Tabelas encontradas:</strong> {len(tabelas)}
                            </div>
            """

            # Para cada tabela, mostra uma prévia
            for tabela in tabelas:
                nome_tabela = tabela[0]
                cursor.execute(f"SELECT * FROM {nome_tabela} LIMIT 10")
                dados = cursor.fetchall()

                # Obtém nomes das colunas
                cursor.execute(f"PRAGMA table_info({nome_tabela})")
                colunas_info = cursor.fetchall()
                colunas = [col[1] for col in colunas_info]

                preview_html += f"""
                <div class="mb-4">
                    <h4><i class="fas fa-table me-2"></i>Tabela: {nome_tabela}</h4>
                    <p class="text-muted">Mostrando até 10 registros</p>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead class="table-dark">
                                <tr>
                """

                # Cabeçalhos
                for coluna in colunas:
                    preview_html += f"<th>{coluna}</th>"

                preview_html += """
                                </tr>
                            </thead>
                            <tbody>
                """

                # Dados
                for linha in dados:
                    preview_html += "<tr>"
                    for valor in linha:
                        # Trunca valores muito longos
                        valor_str = str(valor)[:50] + "..." if len(str(valor)) > 50 else str(valor)
                        preview_html += f"<td>{valor_str}</td>"
                    preview_html += "</tr>"

                preview_html += """
                            </tbody>
                        </table>
                    </div>
                </div>
                """

            preview_html += """
                            <div class="text-center">
                                <a href="/db-preview" class="btn btn-primary me-2">
                                    <i class="fas fa-upload me-2"></i>
                                    Visualizar Outro DB
                                </a>
                                <a href="/" class="btn btn-secondary">
                                    <i class="fas fa-home me-2"></i>
                                    Página Principal
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            conn.close()

            # Agenda limpeza do arquivo temporário após um tempo
            def cleanup_file():
                try:
                    if os.path.exists(temp_db_path):
                        os.remove(temp_db_path)
                        app.logger.info(f"Arquivo DB temporário (preview) removido: {os.path.basename(temp_db_path)}")
                except Exception as cleanup_error:
                    app.logger.error(f"Erro ao limpar arquivo DB temporário (preview): {cleanup_error}")

            import threading
            timer = threading.Timer(60.0, cleanup_file) # Limpa após 60 segundos
            timer.daemon = True
            timer.start()

            return preview_html

        except Exception as e:
            app.logger.error(f"Erro ao visualizar DB: {e}")
            return render_template_string("""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <title>Erro - Visualizador DB</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4>Erro ao Visualizar Banco</h4>
                        <p>Ocorreu um erro ao processar o arquivo .db. Verifique se o arquivo não está corrompido.</p>
                    </div>
                    <a href="/db-preview" class="btn btn-secondary">Tentar Novamente</a>
                </div>
            </body>
            </html>
            """)

    # GET request - mostra formulário de upload
    return render_template_string("""
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Visualizador de Banco de Dados</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
            }
            .main-card {
                backdrop-filter: blur(10px);
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .file-upload-area {
                border: 2px dashed rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .file-upload-area:hover {
                border-color: #4facfe;
                background: rgba(79, 172, 254, 0.1);
            }
        </style>
    </head>
    <body>
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="card main-card">
                        <div class="card-header text-center py-4" style="background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);">
                            <h1 class="card-title mb-2 text-white">
                                <i class="fas fa-search me-3"></i>
                                Visualizador de Banco de Dados
                            </h1>
                            <p class="mb-0 text-white-50">Upload e visualização segura de arquivos .db</p>
                        </div>
                        <div class="card-body p-4">
                            <div class="alert alert-info border-0" style="background: rgba(79, 172, 254, 0.2); border-radius: 15px;">
                                <i class="fas fa-shield-alt me-2 fs-4"></i>
                                <div>
                                    <strong>Seguro e Confiável:</strong> Visualização local sem armazenamento permanente
                                    <br><small class="text-muted">
                                        <i class="fas fa-check me-1"></i> Suporte a SQLite (.db)
                                        <i class="fas fa-check me-1 ms-3"></i> Preview de tabelas e dados
                                        <i class="fas fa-check me-1 ms-3"></i> Exclusão automática após visualização
                                    </small>
                                </div>
                            </div>

                            <form method="post" enctype="multipart/form-data">
                                <div class="file-upload-area mb-4" onclick="document.getElementById('db_file').click()">
                                    <i class="fas fa-cloud-upload-alt fs-1 text-primary mb-3"></i>
                                    <h4>Clique para selecionar arquivo .db</h4>
                                    <p class="text-muted">Ou arraste e solte aqui</p>
                                    <input type="file" id="db_file" name="db_file" accept=".db" style="display: none;" onchange="updateFileName(this)">
                                    <div id="fileName" class="mt-2"></div>
                                </div>

                                <div class="d-grid">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="fas fa-eye me-2"></i>
                                        🔍 Visualizar Conteúdo do Banco
                                    </button>
                                </div>
                            </form>

                            <div class="text-center mt-4">
                                <a href="/" class="btn btn-secondary btn-lg">
                                    <i class="fas fa-arrow-left me-2"></i>
                                    Voltar para Página Principal
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function updateFileName(input) {
                const fileName = document.getElementById('fileName');
                if (input.files[0]) {
                    fileName.innerHTML = `<i class="fas fa-file-alt me-2"></i><strong>Arquivo selecionado:</strong> ${input.files[0].name}`;
                    fileName.className = 'alert alert-success';
                }
            }
        </script>
    </body>
    </html>
    """)

# Configuração de cache
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0