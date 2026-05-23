FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY setup.py README.md ./
COPY scope_mcp/ scope_mcp/
RUN pip install --no-cache-dir -e . && \
    mkdir -p /app/scope_output

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8123/')" || exit 1

EXPOSE 8123

ENTRYPOINT ["scope-mcp"]
