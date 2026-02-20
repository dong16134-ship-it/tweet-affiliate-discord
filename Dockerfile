# 1. 使用 Playwright 官方提供的 Python 镜像（这步最关键，它自带了所有浏览器和 Linux 依赖！）
# 注意：这里的版本号建议和你 requirements.txt 里的 playwright 版本一致
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖文件并安装 Python 库
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 把你的监控代码复制进去
COPY . .

# 5. 设置启动命令（假设你的主程序叫 main.py）
CMD ["python", "main.py"]
