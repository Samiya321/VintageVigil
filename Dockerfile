# 使用官方 Python 3.11 镜像
FROM python:3.11

# 设置工作目录
WORKDIR /VintageVigil

# 将本地代码复制到容器内
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置容器启动时执行的命令
CMD ["python", "./main.py"]