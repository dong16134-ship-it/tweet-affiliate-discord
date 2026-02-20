# 使用官方 Python 3.11 精简版镜像作为基础
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 启动 Flask 服务
CMD ["python", "main.py"]
