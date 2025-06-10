import os
from pathlib import Path
import mimetypes
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

def get_target_directory():
    """
    Obtém o diretório alvo a partir da variável de ambiente TARGET_DIRECTORY.
    Se não estiver definida, retorna o diretório padrão './arquivos'.
    """
    dir_path = os.getenv("TARGET_DIRECTORY", "./arquivos")
    target = Path(dir_path).resolve()
    # Certifique-se de que o diretório exista
    target.mkdir(parents=True, exist_ok=True)
    return target

# Defina aqui o diretório cujos arquivos serão listados e disponibilizados para download
# Agora obtido via variável de ambiente
target_directory = get_target_directory()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/files")
def list_files():
    """
    Retorna a lista de arquivos presentes no diretório predefinido e seus subdiretórios, incluindo metadados:
    - nome do arquivo
    - tipo MIME
    - tamanho em bytes
    - data de criação
    - data de modificação
    - subdiretório relativo (vazio se estiver no diretório raiz)
    """
    try:
        files_info = []
        for file_path in target_directory.rglob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                size = stat.st_size
                created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
                modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                mime_type, _ = mimetypes.guess_type(file_path.name)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                # Determina subdiretório relativo a partir de target_directory
                relative_path = file_path.relative_to(target_directory)
                parent = relative_path.parent
                subdirectory = str(parent).replace('\\', '/') if str(parent) != '.' else ''

                files_info.append({
                    "name": file_path.name,
                    "type": mime_type,
                    "size_bytes": size,
                    "created_at": created_at,
                    "modified_at": modified_at,
                    "subdirectory": subdirectory
                })
        return {"files": files_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_path:path}")
def download_file(file_path: str):
    """
    Permite download de um arquivo especificado pelo caminho relativo (incluindo subdiretórios) dentro do diretório predefinido.
    """
    try:
        # Resolve o caminho completo e previne path traversal
        requested_path = (target_directory / file_path).resolve()
        if not str(requested_path).startswith(str(target_directory)):
            raise HTTPException(status_code=400, detail="Caminho inválido")
        if not requested_path.exists() or not requested_path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        return FileResponse(path=requested_path, filename=requested_path.name, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Exemplo de execução:
# Salve este arquivo como main.py e execute:
#   uvicorn main:app --reload
# Defina a variável de ambiente TARGET_DIRECTORY para apontar ao diretório desejado antes de rodar.
# Por exemplo (Linux/Mac):
#   export TARGET_DIRECTORY="/dados/meus_arquivos"
#   uvicorn main:app --reload
# Ou, se usando Docker Compose, defina no ambiente do serviço no docker-compose.yml.
