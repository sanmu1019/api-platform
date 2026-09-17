FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 依赖全部为纯 Python 包或带预编译 wheel，无需编译器。
# 原先安装 build-essential 只是增大镜像体积与攻击面，这里移除。
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# 以非 root 用户运行，降低容器逃逸后的影响面。
# 注意：docker-compose 会把宿主机的 ./data 挂载到 /app/data，
# 因此宿主机上的 data 目录必须属于 UID 10001，否则 SQLite 无法写入：
#   sudo chown -R 10001:10001 data
# 若沿用 root 运行，删除下面的 useradd / USER 两段即可。
RUN useradd --system --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
