FROM python:3.12-slim

# Instala uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copia arquivos de dependência
COPY pyproject.toml ./
COPY uv.lock* ./

# Instala dependências (sem dev)
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copia o código
COPY . .

# Expõe a porta
EXPOSE 8000

# Variável de ambiente para o PATH do venv
ENV PATH="/app/.venv/bin:$PATH"

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
