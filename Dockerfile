# 阶段一：构建阶段
FROM python:3.10 AS builder

# 合并命令以减少层数，并安装时区数据
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo Asia/Shanghai > /etc/timezone && \
    # 清理缓存和不再需要的文件
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /root/VintageVigil

# 将依赖文件单独复制，以利用Docker缓存
COPY requirements.txt .
# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt --target /root/VintageVigil/dependencies && \
    # 清理pip缓存
    rm -rf /root/.cache/pip

# 将代码复制到容器内
COPY . .

# 阶段二：运行阶段
FROM python:3.10-slim AS runner

# 复制时区设置
COPY --from=builder /etc/localtime /etc/localtime
COPY --from=builder /etc/timezone /etc/timezone

# 设置工作目录
WORKDIR /root/VintageVigil

# 从构建阶段复制已安装的依赖
COPY --from=builder /root/VintageVigil/dependencies /usr/local/lib/python3.10/site-packages

# 从构建阶段复制项目文件
COPY --from=builder /root/VintageVigil .

# 设置容器启动时执行的命令（根据你的需要选择一个）
# 自动监控
# CMD ["bash", "./run_checker.sh"] 

# 在控制台不输出日志
# CMD ["sh", "-c", "python ./main.py > /dev/null 2>&1"] 

# 在控制台输出日志
CMD ["python", "./main.py"]