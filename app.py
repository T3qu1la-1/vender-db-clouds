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

# HTML da interface com Bootstrap styling
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🚀 Processador TXT </title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
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
        .main-card {
            backdrop-filter: blur(15px);
            background: 
                linear-gradient(145deg, rgba(20, 20, 35, 0.9) 0%, rgba(30, 30, 50, 0.8) 100%);
            border: 2px solid;
            border-image: linear-gradient(45deg, rgba(138, 43, 226, 0.5), rgba(30, 144, 255, 0.3), rgba(138, 43, 226, 0.5)) 1;
            border-radius: 25px;
            box-shadow: 
                0 15px 35px rgba(0, 0, 0, 0.7),
                inset 0 1px 0 rgba(255, 255, 255, 0.1),
                0 0 30px rgba(138, 43, 226, 0.2);
            transition: all 0.4s ease;
            position: relative;
        }
        .main-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 
                0 25px 50px rgba(0, 0, 0, 0.8),
                0 0 40px rgba(138, 43, 226, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        .card-header {
            background: 
                linear-gradient(135deg, rgba(75, 0, 130, 0.9) 0%, rgba(25, 25, 112, 0.9) 50%, rgba(72, 61, 139, 0.9) 100%);
            border-radius: 25px 25px 0 0 !important;
            border: none;
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        .card-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            animation: shimmer 2s infinite;
        }
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        .btn-gradient {
            background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
            border: none;
            transition: all 0.3s ease;
        }
        .btn-gradient:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .btn-lg {
            border-radius: 15px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .btn-lg:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        .btn-warning {
            background: linear-gradient(45deg, #ff7b7b 0%, #ff9a56 100%);
            border: none;
        }
        .btn-primary {
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            border: none;
        }
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
            box-shadow: 
                0 0 20px rgba(138, 43, 226, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        .stats-badge {
            background: linear-gradient(45deg, rgba(75, 0, 130, 0.8) 0%, rgba(138, 43, 226, 0.9) 100%);
            border: 1px solid rgba(138, 43, 226, 0.5);
            border-radius: 20px;
            padding: 18px 30px;
            font-weight: 700;
            animation: pulseGothic 3s infinite;
            box-shadow: 
                0 8px 25px rgba(138, 43, 226, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            color: #fff;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
        }
        @keyframes pulseGothic {
            0% { 
                transform: scale(1);
                box-shadow: 0 8px 25px rgba(138, 43, 226, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
            50% { 
                transform: scale(1.08);
                box-shadow: 0 12px 35px rgba(138, 43, 226, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            100% { 
                transform: scale(1);
                box-shadow: 0 8px 25px rgba(138, 43, 226, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
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
            position: relative;
            overflow: hidden;
        }
        .file-input-label:hover {
            background: rgba(30, 30, 50, 0.8);
            border-color: #8a2be2;
            box-shadow: 
                0 5px 15px rgba(138, 43, 226, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
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
        .progress-text {
            font-size: 18px;
            margin-bottom: 10px;
        }
        .progress-detail {
            font-size: 14px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div class="progress-text">🔄 Preparando seu arquivo final...</div>
            <div class="progress-detail">Compilando todas as linhas processadas</div>
        </div>
    </div>

    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card main-card">
                    <div class="card-header text-center py-4">
                        <h1 class="card-title mb-2 text-white">
                            <i class="fas fa-rocket me-3"></i>
                            Processador TXT Pro
                        </h1>
                        <p class="mb-0 text-white-50">Processamento inteligente de credenciais</p>
                    </div>
                    <div class="card-body p-4">
                        <div class="alert alert-info border-0" style="background: rgba(102, 126, 234, 0.2); border-radius: 15px;" role="alert">
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

                        <form method="post" enctype="multipart/form-data" class="mb-4" onsubmit="showLoading()">
                            <div class="mb-4">
                                <label class="form-label fw-bold">
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
                                <label for="filename" class="form-label fw-bold">
                                    <i class="fas fa-tag me-2" style="color: #667eea;"></i>
                                    Nome do arquivo final
                                </label>
                                <div class="input-group">
                                    <span class="input-group-text bg-transparent border-end-0" style="border-color: rgba(255,255,255,0.3);">
                                        <i class="fas fa-file-signature"></i>
                                    </span>
                                    <input type="text" 
                                           class="form-control border-start-0" 
                                           id="filename" 
                                           name="filename" 
                                           placeholder="resultado_final" 
                                           value="resultado_final"
                                           style="border-color: rgba(255,255,255,0.3);">
                                    <span class="input-group-text bg-transparent border-start-0" style="border-color: rgba(255,255,255,0.3);">
                                        .txt
                                    </span>
                                </div>
                                <small class="text-muted">💡 Arquivo manterá TODAS as linhas válidas processadas</small>
                            </div>

                            <div class="d-grid">
                                <button type="submit" class="btn btn-gradient btn-lg py-3">
                                    <i class="fas fa-rocket me-3"></i>
                                    🚀 Processar Arquivos
                                </button>
                            </div>
                        </form>

                        <div class="text-center mt-4">
                            <div class="mb-4">
                                <div class="stats-badge d-inline-block">
                                    <i class="fas fa-chart-line me-2"></i>
                                    <strong>""" + f"{len(session_data['all_lines']):,}" + """</strong> linhas processadas
                                </div>
                                <br>
                                <small class="text-muted mt-2 d-block">
                                    <i class="fas fa-infinity me-1"></i> 
                                    Sem limite de linhas
                                </small>
                            </div>
                            <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                                <a href="/download" class="btn btn-success btn-lg">
                                    <i class="fas fa-download me-2"></i>
                                    💾 Download Completo
                                </a>
                                <a href="/filter-br" class="btn btn-warning btn-lg">
                                    <i class="fas fa-flag me-2"></i>
                                    🇧🇷 Filtrar URLs .BR
                                </a>
                                <a href="/txt-to-db" class="btn btn-info btn-lg">
                                    <i class="fas fa-database me-2"></i>
                                    🗄️ Converter DB
                                </a>
                                <a href="/db-preview" class="btn btn-primary btn-lg">
                                    <i class="fas fa-search me-2"></i>
                                    🔍 Visualizar DB
                                </a>
                            </div>
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



        // Atualiza labels dos arquivos quando selecionados
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                const label = document.querySelector(`label[for="${this.id}"]`);
                if (this.files[0]) {
                    label.innerHTML = `<i class="fas fa-file-check mb-2 d-block" style="color: #28a745;"></i>${this.files[0].name}`;
                    label.style.borderColor = '#28a745';
                    label.style.background = 'rgba(40, 167, 69, 0.1)';
                } else {
                    label.innerHTML = `<i class="fas fa-file-plus mb-2 d-block"></i>Arquivo ${this.id.slice(-1)}`;
                    label.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                    label.style.background = 'rgba(255, 255, 255, 0.1)';
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

    for linha in linhas:
        linha_limpa = linha.strip().lower()
        url_parte = linha_limpa.split(':')[0] if ':' in linha_limpa else linha_limpa
        
        eh_brasileiro = False
        
        # 1. Verifica domínios .br
        if any(dominio in linha_limpa for dominio in dominios_br):
            eh_brasileiro = True
            
        # 2. Verifica sites brasileiros conhecidos
        elif any(site in linha_limpa for site in sites_brasileiros):
            eh_brasileiro = True
            
        # 3. Verifica palavras-chave brasileiras
        elif any(palavra in linha_limpa for palavra in palavras_br):
            eh_brasileiro = True
            
        # 4. Verifica nomes de empresas brasileiras
        elif any(empresa in linha_limpa for empresa in empresas_br):
            eh_brasileiro = True
            
        # 5. Padrões específicos brasileiros
        elif any(padrao in linha_limpa for padrao in [
            'cpf', 'cnpj', 'rg', 'cep', 'pix', 'boleto',
            'cartorio', 'tabeliao', 'delegacia', 'prefeitura',
            'camara', 'assembleia', 'senado', 'congresso',
            'ministerio', 'secretaria', 'anvisa', 'anatel',
            'cvm', 'bacen', 'banco_central', 'susep'
        ]):
            eh_brasileiro = True
            
        # 6. Códigos DDD brasileiros na URL (padrão comum)
        elif any(ddd in linha_limpa for ddd in [
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
        ]):
            eh_brasileiro = True

        if eh_brasileiro:
            urls_brasileiras.append(linha.strip())  # Mantém formatação original

    return urls_brasileiras

def linha_valida(linha: str) -> bool:
    """Verifica se a linha segue o padrão url:user:pass - versão melhorada"""
    if not linha or not linha.strip():
        return False

    linha = linha.strip()

    # Remove aspas duplas no início e fim se existirem
    if linha.startswith('"') and linha.endswith('"'):
        linha = linha[1:-1]

    # Lida com formato "URL":"user":"pass" - substitui aspas entre os campos
    if linha.count('":"') >= 2:
        # Remove todas as aspas e substitui por separadores simples
        linha = linha.replace('":"', ':').strip('"')

    # Lida com formato "URL:user:pass" (aspas só no início/fim)
    if linha.startswith('"') and linha.endswith('"'):
        linha = linha[1:-1]

    # Remove espaços extras e caracteres de controle
    linha = ' '.join(linha.split())

    # Tenta diferentes separadores comuns
    separadores = [':', '|', ';', '\t', ' ']

    for sep in separadores:
        if sep in linha:
            partes = [p.strip() for p in linha.split(sep) if p.strip()]

            # Verifica se tem pelo menos 3 partes não vazias
            if len(partes) >= 3:
                # Para URLs que começam com http:// ou https://
                if partes[0].startswith(('http://', 'https://')):
                    # Reconstrói a URL se foi dividida incorretamente
                    if len(partes) >= 4 and partes[0].startswith('https://'):
                        url = ':'.join(partes[:-2])  # Reconstrói HTTPS URL
                        user = partes[-2].strip()
                        password = partes[-1].strip()
                        return bool(url and user and password and len(user) > 0 and len(password) > 0)
                    elif len(partes) >= 3 and partes[0].startswith('http://'):
                        url = ':'.join(partes[:-2])  # Reconstrói HTTP URL  
                        user = partes[-2].strip()
                        password = partes[-1].strip()
                        return bool(url and user and password and len(user) > 0 and len(password) > 0)

                # Para URLs sem protocolo ou outros formatos
                url, user, password = partes[0], partes[1], partes[2]

                # Valida se todas as partes têm conteúdo válido
                if (url and user and password and 
                    len(url.strip()) > 0 and 
                    len(user.strip()) > 0 and 
                    len(password.strip()) > 0):

                    # Verifica se não são apenas caracteres especiais
                    if (not all(c in '.:/-_' for c in url.strip()) and
                        not all(c in '.:/-_' for c in user.strip()) and  
                        not all(c in '.:/-_' for c in password.strip())):
                        return True

    # Fallback original para formato padrão url:user:pass
    if ':' in linha:
        partes = linha.split(":")
        if len(partes) >= 3:
            # Para HTTPS URLs
            if linha.startswith('https://') and len(partes) >= 4:
                url = ':'.join(partes[:-2])
                user = partes[-2].strip()
                password = partes[-1].strip()
                return bool(url and user and password and len(user) > 0 and len(password) > 0)
            # Para HTTP URLs  
            elif linha.startswith('http://') and len(partes) >= 3:
                url = ':'.join(partes[:-2])
                user = partes[-2].strip()
                password = partes[-1].strip()
                return bool(url and user and password and len(user) > 0 and len(password) > 0)
            # Formato simples de 3 partes
            elif len(partes) == 3:
                url, user, password = partes[0].strip(), partes[1].strip(), partes[2].strip()
                return bool(url and user and password and len(url) > 0 and len(user) > 0 and len(password) > 0)

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
                                        <a href="/" class="btn btn-light btn-lg">
                                            <i class="fas fa-upload me-2"></i>
                                            📤 Processar Mais
                                        </a>
                                        <a href="/download" class="btn btn-gradient btn-lg">
                                            <i class="fas fa-download me-2"></i>
                                            💾 Download Completo
                                        </a>
                                    </div>

                                    <div class="mt-4">
                                        <small class="text-white-50">
                                            💡 O arquivo conterá TODAS as linhas válidas processadas
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>


            </body>
            </html>
            """
            return success_html

        except Exception as e:
            app.logger.error(f"Erro geral no processamento: {e}")
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
                                    <div class="alert alert-danger" role="alert">
                                        <i class="fas fa-exclamation-triangle me-2 fs-4"></i>
                                        <h4 class="alert-heading">Erro no Processamento</h4>
                                        <p class="mb-0">Erro interno. Tente novamente.</p>
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

    return render_template_string(html_form)

@app.route("/download")
def download():
    """Download direto do conteúdo processado em memória."""
    try:
        if not session_data['all_lines']:
            # Erro se não há linhas para download
            error_html = """
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Nenhum Arquivo</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-8 col-lg-6">
                            <div class="card">
                                <div class="card-body text-center">
                                    <div class="alert alert-info" role="alert">
                                        <i class="fas fa-info-circle me-2 fs-4"></i>
                                        <h4 class="alert-heading">Nenhum Arquivo Disponível</h4>
                                        <p class="mb-0">Não há linhas válidas para download. Faça upload de arquivos primeiro.</p>
                                    </div>

                                    <a href="/" class="btn btn-primary">
                                        <i class="fas fa-upload me-2"></i>
                                        Fazer Upload
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

        # Download direto da memória - sem arquivos temporários
        linhas_finais = session_data['all_lines']
        linhas_finais_count = len(linhas_finais)

        app.logger.info(f"Download direto: {linhas_finais_count:,} linhas")

        # Nome do arquivo
        filename = f"{session_data.get('nome_arquivo_final', 'resultado_final')}.txt"

        # Cria conteúdo final na memória
        conteudo_final = '\n'.join(linhas_finais)

        return Response(
            conteudo_final,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )

    except MemoryError:
        app.logger.error("Erro de memória ao salvar arquivo")
        return "Arquivo muito grande para processar. Tente dividir em arquivos menores.", 413
    except Exception as write_error:
        app.logger.error(f"Erro ao escrever arquivo: {write_error}")
        return "Erro ao criar arquivo para download", 500


@app.route("/txt-to-db", methods=["GET", "POST"])
def txt_to_db():
    """Página para converter arquivos TXT em banco de dados SQLite"""

    if request.method == "POST":
        try:
            # Pega o nome do arquivo DB
            db_filename = request.form.get("db_filename", "database").strip()
            if not db_filename:
                db_filename = "database"

            # Processa múltiplos arquivos
            arquivos_processados = []
            total_linhas = 0

            # Cria arquivo temporário para o banco SQLite (será removido após download)
            db_path = os.path.join(tempfile.gettempdir(), f"{db_filename}.db")

            # Conecta ao banco SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Cria a tabela para armazenar os dados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            for i in range(1, 5):  # file1, file2, file3, file4
                file = request.files.get(f"file{i}")
                if file and file.filename and file.filename.endswith(".txt"):
                    try:
                        # lê o conteúdo do arquivo
                        content = file.read().decode("utf-8", errors="ignore").splitlines()
                        linhas_inseridas = 0

                        for linha in content:
                            linha_limpa = linha.strip()
                            if linha_limpa and linha_valida(linha_limpa):
                                # Extrai URL, user e password
                                partes = linha_limpa.split(':')
                                if linha_limpa.startswith('https://') and len(partes) >= 4:
                                    url = ':'.join(partes[:-2])
                                    user = partes[-2]
                                    password = partes[-1]
                                elif linha_limpa.startswith('http://') and len(partes) >= 3:
                                    url = ':'.join(partes[:-2])
                                    user = partes[-2]
                                    password = partes[-1]
                                elif len(partes) == 3:
                                    url, user, password = partes
                                else:
                                    continue

                                # Insere no banco
                                cursor.execute('''
                                    INSERT INTO credentials (url, username, password, source_file)
                                    VALUES (?, ?, ?, ?)
                                ''', (url.strip(), user.strip(), password.strip(), file.filename))
                                linhas_inseridas += 1

                        total_linhas += linhas_inseridas
                        arquivos_processados.append(f"{file.filename} ({linhas_inseridas} registros)")

                    except Exception as e:
                        app.logger.error(f"Erro ao processar arquivo {file.filename}: {e}")
                        arquivos_processados.append(f"{file.filename} (erro)")

            # Salva e fecha conexão
            conn.commit()
            conn.close()

            if not arquivos_processados:
                return render_template_string("""
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head>
                    <meta charset="utf-8">
                    <title>Erro</title>
                    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                </head>
                <body>
                    <div class="container mt-5">
                        <div class="alert alert-warning">
                            <h4>Nenhum Arquivo</h4>
                            <p>Selecione pelo menos um arquivo .txt para converter</p>
                        </div>
                        <a href="/txt-to-db" class="btn btn-secondary">Voltar</a>
                    </div>
                </body>
                </html>
                """)

            # Mensagem de sucesso
            lista_arquivos = "<br>".join([f"• {arq}" for arq in arquivos_processados])
            return render_template_string(f"""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Conversão Concluída</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-8 col-lg-6">
                            <div class="card">
                                <div class="card-body text-center">
                                    <div class="alert alert-success">
                                        <i class="fas fa-check-circle me-2 fs-4"></i>
                                        <h4>Conversão Concluída!</h4>
                                        <p><strong>{total_linhas} registros</strong> inseridos no banco:</p>
                                        <div class="text-start">{lista_arquivos}</div>
                                        <hr>
                                        <small>Arquivo: <strong>{db_filename}.db</strong></small>
                                    </div>

                                    <div class="d-grid gap-2">
                                        <a href="/txt-to-db" class="btn btn-primary">
                                            <i class="fas fa-arrow-left me-2"></i>
                                            Converter Mais Arquivos
                                        </a>
                                        <a href="/download-db/{db_filename}" class="btn btn-success">
                                            <i class="fas fa-download me-2"></i>
                                            Baixar {db_filename}.db
                                        </a>
                                        <a href="/" class="btn btn-secondary">
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
            app.logger.error(f"Erro na conversão: {e}")
            return render_template_string("""
            <!doctype html>
            <html lang="pt-BR" data-bs-theme="dark">
            <head>
                <meta charset="utf-8">
                <title>Erro</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4>Erro na Conversão</h4>
                        <p>Ocorreu um erro ao processar os arquivos. Tente novamente.</p>
                    </div>
                    <a href="/txt-to-db" class="btn btn-secondary">Tentar Novamente</a>
                </div>
            </body>
            </html>
            """)

    # GET request - mostra o formulário
    return render_template_string("""
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Converter TXT para DB</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-8 col-lg-6">
                    <div class="card">
                        <div class="card-header text-center">
                            <h2 class="card-title mb-0">
                                <i class="fas fa-database me-2"></i>
                                Converter TXT para DB
                            </h2>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Converta arquivos TXT em banco SQLite (.db)</strong><br>
                                <small>Os dados serão organizados em tabela com colunas: URL, Usuário, Senha</small>
                            </div>

                            <form method="post" enctype="multipart/form-data" class="mb-4">
                                <div class="mb-3">
                                    <label class="form-label">
                                        <i class="fas fa-file-text me-2"></i>
                                        Selecione até 4 arquivos (.txt/.rar/.zip)
                                    </label>
                                    <input type="file" class="form-control mb-2" name="file1" accept=".txt">
                                    <input type="file" class="form-control mb-2" name="file2" accept=".txt">
                                    <input type="file" class="form-control mb-2" name="file3" accept=".txt">
                                    <input type="file" class="form-control mb-2" name="file4" accept=".txt">
                                </div>

                                <div class="mb-3">
                                    <label for="db_filename" class="form-label">
                                        <i class="fas fa-database me-2"></i>
                                        Nome do banco de dados
                                    </label>
                                    <input type="text" 
                                           class="form-control" 
                                           id="db_filename" 
                                           name="db_filename" 
                                           placeholder="database" 
                                           value="database">
                                    <small class="text-muted">O banco será salvo como [nome].db</small>
                                </div>

                                <div class="d-grid">
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-cogs me-2"></i>
                                        Converter para DB
                                    </button>
                                </div>
                            </form>

                            <div class="text-center">
                                <a href="/" class="btn btn-secondary">
                                    <i class="fas fa-arrow-left me-2"></i>
                                    Voltar para Página Principal
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

@app.route("/download-db/<filename>")
def download_db(filename):
    """Rota para download do arquivo de banco de dados"""
    try:
        # Procura arquivo temporário
        db_path = os.path.join(tempfile.gettempdir(), f"{filename}.db")
        if os.path.exists(db_path):
            # Programa limpeza do arquivo após download
            def cleanup_file(): # Renamed from cleanup_db to cleanup_file
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        app.logger.info(f"Arquivo DB temporário removido: {filename}.db")
                except Exception as cleanup_error:
                    app.logger.error(f"Erro ao limpar DB: {cleanup_error}")

            # Agenda limpeza para após o download
            import threading
            timer = threading.Timer(30.0, cleanup_file)  # Remove após 30 segundos
            timer.start()

            return send_file(db_path, as_attachment=True, download_name=f"{filename}.db")
        else:
            return "Arquivo não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar DB: {e}")
        return "Erro ao baixar arquivo", 500

@app.route("/filter-br")
def filter_br():
    """Rota para filtrar apenas URLs brasileiras"""
    global session_data

    if not session_data['all_lines']:
        return render_template_string("""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head>
            <meta charset="utf-8">
            <title>Filtro BR</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <h4>Nenhum dado processado</h4>
                    <p>Você precisa processar arquivos primeiro antes de filtrar URLs brasileiras.</p>
                </div>
                <a href="/" class="btn btn-primary">Voltar e Processar Arquivos</a>
            </div>
        </body>
        </html>
        """)

    # Filtra URLs brasileiras
    urls_br = filtrar_urls_brasileiras(session_data['all_lines'])

    # Cria arquivo temporário com URLs brasileiras
    nome_arquivo = f"urls_brasileiras_{len(urls_br)}"
    arquivo_temp = os.path.join(tempfile.gettempdir(), f"{nome_arquivo}.txt")

    try:
        with open(arquivo_temp, 'w', encoding='utf-8') as f:
            for url in urls_br:
                f.write(f"{url}\\n")

        return render_template_string(f"""
        <!doctype html>
        <html lang="pt-BR" data-bs-theme="dark">
        <head>
            <meta charset="utf-8">
            <title>URLs Brasileiras Filtradas</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
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
                                    <a href="/download-filtered/{nome_arquivo}" class="btn btn-success btn-lg">
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
            timer = threading.Timer(30.0, cleanup_file)  # Remove após 30 segundos
            timer.start()
            
            return send_file(file_path, as_attachment=True, download_name=f"{filename}.txt")
        else:
            return "Arquivo não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar arquivo filtrado: {e}")
        return "Erro ao baixar arquivo", 500

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

# Sem limite de tamanho de upload
# app.config['MAX_CONTENT_LENGTH'] removido
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0