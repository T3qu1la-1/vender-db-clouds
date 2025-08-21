from flask import Flask, request, render_template_string, send_file
import os
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lista que acumula as linhas válidas
all_lines = []

# HTML da interface com Bootstrap styling
html_form = """
<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Uploader de TXT - Processador de Linhas</title>
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
                            <i class="fas fa-file-upload me-2"></i>
                            Uploader de Arquivos TXT
                        </h2>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-info" role="alert">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Formato esperado:</strong> Linhas no padrão <code>url:user:pass</code>
                            <br><small class="text-muted">
                                Exemplo: <code>http://site.com.br/login:usuario123:senha456</code>
                            </small>
                        </div>
                        
                        <form method="post" enctype="multipart/form-data" class="mb-4">
                            <div class="mb-3">
                                <label for="file" class="form-label">
                                    <i class="fas fa-file-text me-2"></i>
                                    Selecione um arquivo .txt
                                </label>
                                <input type="file" 
                                       class="form-control" 
                                       id="file" 
                                       name="file" 
                                       accept=".txt" 
                                       required>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-upload me-2"></i>
                                    Fazer Upload
                                </button>
                            </div>
                        </form>
                        
                        <div class="text-center">
                            <div class="mb-3">
                                <span class="badge bg-secondary fs-6">
                                    <i class="fas fa-list me-2"></i>
                                    """ + str(len(all_lines)) + """ linhas válidas acumuladas
                                </span>
                            </div>
                            <a href="/download" class="btn btn-success">
                                <i class="fas fa-download me-2"></i>
                                Baixar Arquivo Final
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def linha_valida(linha: str) -> bool:
    """Verifica se a linha segue o padrão url:user:pass"""
    if not linha or not linha.strip():
        return False
    
    linha = linha.strip()
    
    # Divide a linha em partes, mas cuidado com URLs que podem ter múltiplos ':'
    # Procura pelo padrão: URL (que começa com http/https) : user : pass
    if linha.startswith('http://') or linha.startswith('https://'):
        # Encontra os dois pontos que separam URL:user:pass
        partes = linha.split(':', 2)  # Divide em no máximo 3 partes
        if len(partes) >= 3:
            url, user, password = partes[0], partes[1], partes[2]
            # Verifica se todas as partes têm conteúdo
            return bool(url.strip() and user.strip() and password.strip())
    
    # Fallback: se não começa com http, tenta dividir normalmente em 3 partes
    partes = linha.split(":")
    if len(partes) == 3:
        return all(parte.strip() for parte in partes)
    
    return False

@app.route("/", methods=["GET", "POST"])
def upload_file():
    global all_lines
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename and file.filename.endswith(".txt"):
            try:
                # lê o conteúdo do arquivo
                content = file.read().decode("utf-8", errors="ignore").splitlines()
                # filtra linhas válidas
                filtradas = [linha.strip() for linha in content if linha_valida(linha.strip())]
                # adiciona ao acumulador
                all_lines.extend(filtradas)
                
                # Mensagem de sucesso com Bootstrap
                success_html = f"""
                <!doctype html>
                <html lang="pt-BR" data-bs-theme="dark">
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Upload Concluído</title>
                    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
                </head>
                <body>
                    <div class="container mt-5">
                        <div class="row justify-content-center">
                            <div class="col-md-8 col-lg-6">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <div class="alert alert-success" role="alert">
                                            <i class="fas fa-check-circle me-2 fs-4"></i>
                                            <h4 class="alert-heading">Upload Concluído!</h4>
                                            <p class="mb-0">{len(filtradas)} linhas válidas adicionadas de {file.filename}!</p>
                                        </div>
                                        
                                        <div class="d-grid gap-2">
                                            <a href="/" class="btn btn-primary">
                                                <i class="fas fa-arrow-left me-2"></i>
                                                Fazer Novo Upload
                                            </a>
                                            <a href="/download" class="btn btn-success">
                                                <i class="fas fa-download me-2"></i>
                                                Baixar Arquivo Final
                                            </a>
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
                app.logger.error(f"Erro ao processar arquivo: {e}")
                error_html = f"""
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
                                            <h4 class="alert-heading">Erro no Upload</h4>
                                            <p class="mb-0">Erro ao processar o arquivo. Tente novamente.</p>
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
        else:
            # Erro para arquivo inválido
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
                                        <h4 class="alert-heading">Arquivo Inválido</h4>
                                        <p class="mb-0">⚠️ Envie apenas arquivos .txt</p>
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
        
        # salva o arquivo final com todas as linhas válidas
        caminho_saida = os.path.join(UPLOAD_FOLDER, "resultado_final.txt")
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))
        return send_file(caminho_saida, as_attachment=True, download_name="resultado_final.txt")
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar download: {e}")
        return "Erro ao gerar arquivo para download", 500

if __name__ == "__main__":
    # Configura o tamanho máximo de upload
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # Roda no navegador local
    app.run(host="0.0.0.0", port=5000, debug=True)