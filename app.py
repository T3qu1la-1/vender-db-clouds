from flask import Flask, request, render_template_string, send_file
import os
import logging
import sqlite3
import tempfile

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Função para limpeza de arquivos temporários antigos
def cleanup_old_temp_files():
    """Remove arquivos temporários antigos (mais de 1 hora)"""
    import time
    temp_dir = tempfile.gettempdir()
    current_time = time.time()
    
    try:
        for filename in os.listdir(temp_dir):
            if filename.endswith(('_otimizado.txt', '.db')) and ('resultado_final' in filename or 'database' in filename):
                filepath = os.path.join(temp_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > 3600:  # 1 hora
                        try:
                            os.remove(filepath)
                            app.logger.info(f"Arquivo temporário antigo removido: {filename}")
                        except Exception as e:
                            app.logger.error(f"Erro ao remover arquivo antigo {filename}: {e}")
    except Exception as e:
        app.logger.error(f"Erro na limpeza de arquivos temporários: {e}")

# Executa limpeza ao iniciar a aplicação
cleanup_old_temp_files()

# Pasta de uploads não é mais criada - tudo é processado em memória
# UPLOAD_FOLDER removido - arquivos são temporários

# Lista que acumula as linhas válidas
all_lines = []

# Nome do arquivo final (personalizado pelo usuário)
nome_arquivo_final = "resultado_final"

# Limite máximo de linhas acumuladas
MAX_LINES = 5000000  # 5 milhões

# HTML da interface com Bootstrap styling
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🚀 Processador TXT Pro</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .main-card {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        .main-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        .card-header {
            background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px 20px 0 0 !important;
            border: none;
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
        .form-control {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            transition: all 0.3s ease;
        }
        .form-control:focus {
            background: rgba(255, 255, 255, 0.15);
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }
        .stats-badge {
            background: linear-gradient(45deg, #11998e 0%, #38ef7d 100%);
            border-radius: 15px;
            padding: 15px 25px;
            font-weight: 600;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
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
            padding: 12px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            cursor: pointer;
            display: block;
            text-align: center;
            transition: all 0.3s ease;
        }
        .file-input-label:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: #667eea;
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
            <div class="progress-detail">Otimizando dados e removendo duplicatas</div>
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
                                    Selecione até 4 arquivos .txt
                                </label>
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file1" accept=".txt" id="file1">
                                            <label for="file1" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 1
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file2" accept=".txt" id="file2">
                                            <label for="file2" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 2
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file3" accept=".txt" id="file3">
                                            <label for="file3" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 3
                                            </label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="file-input-wrapper">
                                            <input type="file" name="file4" accept=".txt" id="file4">
                                            <label for="file4" class="file-input-label">
                                                <i class="fas fa-file-plus mb-2 d-block"></i>
                                                Arquivo 4
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
                                <small class="text-muted">💡 Arquivo será otimizado automaticamente (sem duplicatas)</small>
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
                                    <strong>""" + f"{len(all_lines):,}" + """</strong> linhas processadas
                                </div>
                                <br>
                                <small class="text-muted mt-2 d-block">
                                    <i class="fas fa-shield-alt me-1"></i> 
                                    Limite máximo: 5.000.000 linhas
                                </small>
                            </div>
                            <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                                <a href="/download" class="btn btn-success btn-lg" onclick="showDownloadLoading()">
                                    <i class="fas fa-download me-2"></i>
                                    💾 Download Final
                                </a>
                                <a href="/txt-to-db" class="btn btn-info btn-lg">
                                    <i class="fas fa-database me-2"></i>
                                    🗄️ Converter DB
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
        
        function showDownloadLoading() {
            document.getElementById('loadingOverlay').style.display = 'flex';
            document.querySelector('.progress-text').textContent = '📥 Preparando download...';
            document.querySelector('.progress-detail').textContent = 'Otimizando arquivo e removendo duplicatas';
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

def linha_valida(linha: str) -> bool:
    """Verifica se a linha segue o padrão url:user:pass"""
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
    
    # Para URLs que começam com http:// ou https://
    if linha.startswith(('http://', 'https://')):
        # Encontra todos os dois pontos na linha
        partes = linha.split(':')
        
        # URLs HTTPS terão pelo menos 4 partes: ['https', '//site.com/path', 'user', 'pass']
        # URLs HTTP terão pelo menos 3 partes: ['http', '//site.com/path', 'user', 'pass'] 
        if linha.startswith('https://') and len(partes) >= 4:
            # Para HTTPS: reconstrói a URL e pega user:pass
            url = ':'.join(partes[:-2])  # Tudo exceto os 2 últimos
            user = partes[-2].strip()  # Penúltimo
            password = partes[-1].strip()  # Último
            return bool(url and user and password)
        elif linha.startswith('http://') and len(partes) >= 3:
            # Para HTTP: reconstrói a URL e pega user:pass
            url = ':'.join(partes[:-2])  # Tudo exceto os 2 últimos
            user = partes[-2].strip()  # Penúltimo  
            password = partes[-1].strip()  # Último
            return bool(url and user and password)
    
    # Fallback: se não começa com http, tenta dividir normalmente em 3 partes
    partes = linha.split(":")
    if len(partes) == 3:
        return all(parte.strip() for parte in partes)
    
    return False

@app.route("/", methods=["GET", "POST"])
def upload_file():
    global all_lines
    if request.method == "POST":
        try:
            # Pega o nome do arquivo final
            filename = request.form.get("filename", "resultado_final").strip()
            if not filename:
                filename = "resultado_final"
            
            # Processa múltiplos arquivos
            arquivos_processados = []
            total_filtradas = 0
            
            for i in range(1, 5):  # file1, file2, file3, file4
                file = request.files.get(f"file{i}")
                if file and file.filename and file.filename.endswith(".txt"):
                    try:
                        # lê o conteúdo do arquivo
                        content = file.read().decode("utf-8", errors="ignore").splitlines()
                        app.logger.info(f"Arquivo {file.filename} lido com {len(content)} linhas")
                        
                        # filtra linhas válidas
                        filtradas = []
                        linhas_processadas = 0
                        for linha in content:
                            linha_limpa = linha.strip()
                            if linha_limpa:  # ignora linhas vazias
                                linhas_processadas += 1
                                if linha_valida(linha_limpa):
                                    # Verifica se não ultrapassou o limite
                                    if len(all_lines) + len(filtradas) >= MAX_LINES:
                                        app.logger.info(f"Limite de {MAX_LINES:,} linhas atingido!")
                                        break
                                    filtradas.append(linha_limpa)
                                    
                                    # Força garbage collection a cada 50k linhas para economizar memória
                                    if len(filtradas) % 50000 == 0:
                                        import gc
                                        gc.collect()
                                    # Log apenas a cada 1000 linhas válidas para evitar spam
                                    if len(filtradas) % 1000 == 0:
                                        app.logger.info(f"Processadas {len(filtradas)} linhas válidas...")
                        
                        app.logger.info(f"Arquivo {file.filename}: {len(filtradas)} válidas de {linhas_processadas} processadas")
                        
                        # adiciona ao acumulador
                        linhas_antes = len(all_lines)
                        all_lines.extend(filtradas)
                        total_filtradas += len(filtradas)
                        arquivos_processados.append(f"{file.filename} ({len(filtradas)} válidas)")
                        
                        # Para se atingiu o limite
                        if len(all_lines) >= MAX_LINES:
                            app.logger.info(f"Limite máximo de {MAX_LINES:,} linhas atingido! Parando processamento.")
                            break
                        
                    except Exception as e:
                        app.logger.error(f"Erro ao processar arquivo {file.filename}: {e}")
                        arquivos_processados.append(f"{file.filename} (erro)")
            
            app.logger.info(f"Total acumulado: {len(all_lines)}")
            
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
                        <div style="font-size: 18px; margin-bottom: 10px;">🔄 Preparando download otimizado...</div>
                        <div style="font-size: 14px; opacity: 0.8;">Removendo duplicatas e organizando dados</div>
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
                                                <h4 class="text-white">{len(all_lines):,}</h4>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="d-grid gap-3 d-md-flex justify-content-md-center">
                                        <a href="/" class="btn btn-light btn-lg">
                                            <i class="fas fa-upload me-2"></i>
                                            📤 Processar Mais
                                        </a>
                                        <a href="/download" class="btn btn-gradient btn-lg" onclick="showDownloadLoading()">
                                            <i class="fas fa-download me-2"></i>
                                            💾 Download Otimizado
                                        </a>
                                    </div>
                                    
                                    <div class="mt-4">
                                        <small class="text-white-50">
                                            💡 O arquivo será otimizado automaticamente (duplicatas removidas)
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <script>
                    function showDownloadLoading() {{
                        document.getElementById('loadingOverlay').style.display = 'flex';
                    }}
                </script>
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
    try:
        if not all_lines:
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
        
        # Otimiza o arquivo removendo duplicatas e ordenando
        global nome_arquivo_final
        
        # Remove duplicatas de forma mais eficiente para grandes datasets
        app.logger.info(f"Iniciando otimização de {len(all_lines):,} linhas...")
        
        # Usa set para remoção mais eficiente de duplicatas
        linhas_unicas = list(dict.fromkeys(all_lines))  # Remove duplicatas mantendo ordem
        app.logger.info(f"Duplicatas removidas: {len(all_lines):,} → {len(linhas_unicas):,} linhas")
        
        # Ordena de forma mais eficiente
        linhas_finais = sorted(set(linhas_unicas))
        app.logger.info(f"Ordenação concluída: {len(linhas_finais):,} linhas finais")
        
        # Calcula estatísticas de otimização
        linhas_originais = len(all_lines)
        linhas_finais_count = len(linhas_finais)
        reducao = ((linhas_originais - linhas_finais_count) / linhas_originais * 100) if linhas_originais > 0 else 0
        
        app.logger.info(f"Otimização: {linhas_originais:,} → {linhas_finais_count:,} linhas ({reducao:.1f}% redução)")
        
        # Cria arquivo temporário (será deletado após download)
        filename = f"{nome_arquivo_final}_otimizado.txt"
        caminho_saida = os.path.join(tempfile.gettempdir(), filename)
        
        app.logger.info(f"Salvando arquivo: {filename} ({linhas_finais_count:,} linhas)")
        
        try:
            with open(caminho_saida, "w", encoding="utf-8", buffering=8192) as f:
                # Adiciona cabeçalho informativo
                f.write(f"# Arquivo otimizado - {linhas_finais_count:,} linhas únicas\n")
                f.write(f"# Original: {linhas_originais:,} linhas | Redução: {reducao:.1f}%\n")
                f.write(f"# Formato: url:user:pass\n")
                f.write(f"# Processado em: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# =================================\n\n")
                
                # Escreve em chunks para arquivos grandes
                if len(linhas_finais) > 100000:  # Para arquivos grandes
                    app.logger.info("Escrevendo arquivo grande em chunks...")
                    chunk_size = 10000
                    for i in range(0, len(linhas_finais), chunk_size):
                        chunk = linhas_finais[i:i+chunk_size]
                        f.write("\n".join(chunk))
                        if i + chunk_size < len(linhas_finais):
                            f.write("\n")
                        if (i // chunk_size) % 10 == 0:  # Log a cada 100k linhas
                            app.logger.info(f"Escrito {i + len(chunk):,} linhas...")
                else:
                    f.write("\n".join(linhas_finais))
                    
            app.logger.info(f"Arquivo salvo com sucesso: {filename}")
            
        except MemoryError:
            app.logger.error("Erro de memória ao salvar arquivo")
            return "Arquivo muito grande para processar. Tente dividir em arquivos menores.", 413
        except Exception as write_error:
            app.logger.error(f"Erro ao escrever arquivo: {write_error}")
            return "Erro ao criar arquivo para download", 500
        
        # Verifica se o arquivo foi criado corretamente
        if not os.path.exists(caminho_saida):
            app.logger.error("Arquivo não foi criado")
            return "Erro: arquivo não foi criado", 500
            
        file_size = os.path.getsize(caminho_saida)
        app.logger.info(f"Iniciando download: {filename} ({file_size / (1024*1024):.1f} MB)")
        
        # Para arquivos muito grandes, adiciona parâmetros específicos
        try:
            if file_size > 50 * 1024 * 1024:  # Arquivos maiores que 50MB
                app.logger.info("Arquivo grande detectado, usando streaming response")
                return send_file(
                    caminho_saida, 
                    as_attachment=True, 
                    download_name=filename,
                    conditional=True,  # Permite download parcial
                    max_age=0  # Não cachear
                )
            else:
                # Programa limpeza do arquivo após download
                def cleanup_file():
                    try:
                        if os.path.exists(caminho_saida):
                            os.remove(caminho_saida)
                            app.logger.info(f"Arquivo temporário removido: {filename}")
                    except Exception as cleanup_error:
                        app.logger.error(f"Erro ao limpar arquivo: {cleanup_error}")
                        
                # Agenda limpeza para após o download (usando thread)
                import threading
                timer = threading.Timer(30.0, cleanup_file)  # Remove após 30 segundos
                timer.start()
                
                return send_file(caminho_saida, as_attachment=True, download_name=filename)
                
        except Exception as send_error:
            app.logger.error(f"Erro ao enviar arquivo: {send_error}")
            # Limpa arquivo em caso de erro
            try:
                if os.path.exists(caminho_saida):
                    os.remove(caminho_saida)
            except:
                pass
            return "Erro ao enviar arquivo para download", 500
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar download: {e}")
        return "Erro ao gerar arquivo para download", 500

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
                    <meta name="viewport" content="width=device-width, initial-scale=1">
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
                                        Selecione até 4 arquivos .txt
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
            def cleanup_db():
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        app.logger.info(f"Arquivo DB temporário removido: {filename}.db")
                except Exception as cleanup_error:
                    app.logger.error(f"Erro ao limpar DB: {cleanup_error}")
            
            # Agenda limpeza para após o download
            import threading
            timer = threading.Timer(60.0, cleanup_db)  # Remove após 60 segundos para DBs
            timer.start()
            
            return send_file(db_path, as_attachment=True, download_name=f"{filename}.db")
        else:
            return "Arquivo não encontrado", 404
    except Exception as e:
        app.logger.error(f"Erro ao baixar DB: {e}")
        return "Erro ao baixar arquivo", 500

if __name__ == "__main__":
    # Configura o tamanho máximo de upload
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # Roda no navegador local
    app.run(host="0.0.0.0", port=5000, debug=True)