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
                            <strong>Formato esperado:</strong> Linhas no padrão <code>parte1:parte2:parte3</code>
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
                                    {{ total_lines }} linhas válidas acumuladas
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

# HTML para mensagem de sucesso
success_message = """
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
                            <p class="mb-0">{{ message }}</p>
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
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# HTML para mensagem de erro
error_message = """
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
                            <p class="mb-0">{{ message }}</p>
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
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def linha_valida(linha: str) -> bool:
    """
    Verifica se a linha segue o padrão parte1:parte2:parte3
    
    Args:
        linha (str): Linha a ser validada
        
    Returns:
        bool: True se a linha é válida, False caso contrário
    """
    if not linha or not linha.strip():
        return False
    
    partes = linha.strip().split(":")
    # Deve ter exatamente 3 partes e nenhuma pode estar vazia
    return len(partes) == 3 and all(parte.strip() for parte in partes)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    """
    Rota principal para upload de arquivos e exibição da interface
    """
    global all_lines
    
    if request.method == "POST":
        try:
            # Verifica se um arquivo foi enviado
            if 'file' not in request.files:
                return render_template_string(error_message, 
                    message="Nenhum arquivo foi selecionado.")
            
            file = request.files["file"]
            
            # Verifica se um arquivo foi realmente selecionado
            if file.filename == '':
                return render_template_string(error_message, 
                    message="Nenhum arquivo foi selecionado.")
            
            # Verifica se é um arquivo .txt
            if not (file and file.filename.lower().endswith(".txt")):
                return render_template_string(error_message, 
                    message="Por favor, envie apenas arquivos com extensão .txt")
            
            # Lê o conteúdo do arquivo
            try:
                content = file.read().decode("utf-8", errors="ignore").splitlines()
            except Exception as e:
                app.logger.error(f"Erro ao ler arquivo: {e}")
                return render_template_string(error_message, 
                    message="Erro ao ler o conteúdo do arquivo. Verifique se é um arquivo de texto válido.")
            
            # Filtra linhas válidas
            linhas_originais = len(content)
            filtradas = [linha.strip() for linha in content if linha_valida(linha.strip())]
            
            # Adiciona ao acumulador, evitando duplicatas
            linhas_novas = 0
            for linha in filtradas:
                if linha not in all_lines:
                    all_lines.append(linha)
                    linhas_novas += 1
            
            # Mensagem de sucesso
            message = f"{linhas_novas} linhas válidas únicas adicionadas de {file.filename}!"
            if len(filtradas) > linhas_novas:
                message += f" ({len(filtradas) - linhas_novas} duplicatas ignoradas)"
            if linhas_originais > len(filtradas):
                message += f" ({linhas_originais - len(filtradas)} linhas inválidas ignoradas)"
                
            return render_template_string(success_message, message=message)
            
        except Exception as e:
            app.logger.error(f"Erro no processamento do upload: {e}")
            return render_template_string(error_message, 
                message="Erro interno no processamento do arquivo. Tente novamente.")
    
    # GET request - exibe o formulário
    return render_template_string(html_form, total_lines=len(all_lines))

@app.route("/download")
def download():
    """
    Rota para download do arquivo consolidado com todas as linhas válidas
    """
    try:
        # Verifica se existem linhas para download
        if not all_lines:
            return render_template_string(error_message, 
                message="Não há linhas válidas para download. Faça upload de arquivos primeiro.")
        
        # Salva o arquivo final com todas as linhas válidas
        caminho_saida = os.path.join(UPLOAD_FOLDER, "resultado_final.txt")
        
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))
        
        app.logger.info(f"Arquivo final gerado com {len(all_lines)} linhas")
        return send_file(caminho_saida, as_attachment=True, download_name="resultado_final.txt")
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar arquivo de download: {e}")
        return render_template_string(error_message, 
            message="Erro ao gerar o arquivo de download. Tente novamente.")

@app.route("/reset")
def reset_lines():
    """
    Rota para limpar todas as linhas acumuladas (útil para desenvolvimento/teste)
    """
    global all_lines
    all_lines = []
    return render_template_string(success_message, 
        message="Todas as linhas acumuladas foram removidas. Você pode começar novamente.")

@app.errorhandler(413)
def request_entity_too_large(error):
    """
    Handler para arquivos muito grandes
    """
    return render_template_string(error_message, 
        message="O arquivo enviado é muito grande. Tente com um arquivo menor.")

@app.errorhandler(500)
def internal_error(error):
    """
    Handler para erros internos do servidor
    """
    app.logger.error(f"Erro interno: {error}")
    return render_template_string(error_message, 
        message="Erro interno do servidor. Tente novamente mais tarde.")

if __name__ == "__main__":
    # Configura o tamanho máximo de upload (16MB)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Roda no navegador local
    app.run(host="0.0.0.0", port=5000, debug=True)
