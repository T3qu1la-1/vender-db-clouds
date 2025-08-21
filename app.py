from flask import Flask, request, render_template_string, send_file
import os
import logging
import sqlite3
import tempfile

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lista que acumula as linhas válidas
all_lines = []

# Nome do arquivo final (personalizado pelo usuário)
nome_arquivo_final = "resultado_final"

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
                                <label class="form-label">
                                    <i class="fas fa-file-text me-2"></i>
                                    Selecione até 4 arquivos .txt
                                </label>
                                <input type="file" 
                                       class="form-control mb-2" 
                                       name="file1" 
                                       accept=".txt">
                                <input type="file" 
                                       class="form-control mb-2" 
                                       name="file2" 
                                       accept=".txt">
                                <input type="file" 
                                       class="form-control mb-2" 
                                       name="file3" 
                                       accept=".txt">
                                <input type="file" 
                                       class="form-control mb-2" 
                                       name="file4" 
                                       accept=".txt">
                            </div>
                            
                            <div class="mb-3">
                                <label for="filename" class="form-label">
                                    <i class="fas fa-save me-2"></i>
                                    Nome do arquivo final
                                </label>
                                <input type="text" 
                                       class="form-control" 
                                       id="filename" 
                                       name="filename" 
                                       placeholder="resultado_final" 
                                       value="resultado_final">
                                <small class="text-muted">O arquivo será salvo como [nome].txt</small>
                            </div>
                            
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-upload me-2"></i>
                                    Processar Arquivos
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
                            <a href="/txt-to-db" class="btn btn-info">
                                <i class="fas fa-database me-2"></i>
                                Converter TXT para DB
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
    
    # Para URLs que começam com http:// ou https://
    if linha.startswith('http://') or linha.startswith('https://'):
        # Encontra todos os dois pontos na linha
        partes = linha.split(':')
        
        # URLs HTTPS terão pelo menos 4 partes: ['https', '//site.com/path', 'user', 'pass']
        # URLs HTTP terão pelo menos 3 partes: ['http', '//site.com/path', 'user', 'pass'] 
        if linha.startswith('https://') and len(partes) >= 4:
            # Para HTTPS: reconstrói a URL e pega user:pass
            url = ':'.join(partes[:-2])  # Tudo exceto os 2 últimos
            user = partes[-2]  # Penúltimo
            password = partes[-1]  # Último
            return bool(url.strip() and user.strip() and password.strip())
        elif linha.startswith('http://') and len(partes) >= 3:
            # Para HTTP: reconstrói a URL e pega user:pass
            url = ':'.join(partes[:-2])  # Tudo exceto os 2 últimos
            user = partes[-2]  # Penúltimo  
            password = partes[-1]  # Último
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
                        for linha in content:
                            linha_limpa = linha.strip()
                            if linha_limpa:  # ignora linhas vazias
                                if linha_valida(linha_limpa):
                                    filtradas.append(linha_limpa)
                                    app.logger.info(f"Linha válida: {linha_limpa}")
                                else:
                                    app.logger.info(f"Linha inválida: {linha_limpa}")
                        
                        app.logger.info(f"Arquivo {file.filename}: {len(filtradas)} linhas válidas")
                        
                        # adiciona ao acumulador
                        all_lines.extend(filtradas)
                        total_filtradas += len(filtradas)
                        arquivos_processados.append(f"{file.filename} ({len(filtradas)} válidas)")
                        
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
            lista_arquivos = "<br>".join([f"• {arq}" for arq in arquivos_processados])
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
                                        <h4 class="alert-heading">Processamento Concluído!</h4>
                                        <p class="mb-2"><strong>{total_filtradas} linhas válidas</strong> adicionadas dos arquivos:</p>
                                        <div class="text-start">{lista_arquivos}</div>
                                        <hr>
                                        <small>Arquivo final: <strong>{filename}.txt</strong></small>
                                    </div>
                                    
                                    <div class="d-grid gap-2">
                                        <a href="/" class="btn btn-primary">
                                            <i class="fas fa-arrow-left me-2"></i>
                                            Processar Mais Arquivos
                                        </a>
                                        <a href="/download" class="btn btn-success">
                                            <i class="fas fa-download me-2"></i>
                                            Baixar {filename}.txt
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
        
        # salva o arquivo final com todas as linhas válidas
        global nome_arquivo_final
        filename = f"{nome_arquivo_final}.txt"
        caminho_saida = os.path.join(UPLOAD_FOLDER, filename)
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))
        return send_file(caminho_saida, as_attachment=True, download_name=filename)
        
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
            
            # Cria um arquivo temporário para o banco SQLite
            db_path = os.path.join(UPLOAD_FOLDER, f"{db_filename}.db")
            
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
        db_path = os.path.join(UPLOAD_FOLDER, f"{filename}.db")
        if os.path.exists(db_path):
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