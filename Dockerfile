# 阶段一：构建阶段
FROM python:3.10 AS builder

# 将依赖文件单独复制到工作目录，以利用Docker缓存
COPY requirements.txt /root/VintageVigil/

# 安装Python依赖，并清理pip缓存
RUN cd /root/VintageVigil && pip install --no-cache-dir -r requirements.txt --target /root/dependencies

# 将代码复制到容器内
COPY . /root/VintageVigil

# 确保启动脚本具有执行权限
RUN chmod +x /root/VintageVigil/start.sh

# 阶段二：运行阶段
FROM python:3.10-slim AS runner

# 安装运行时依赖，并清理APT缓存
RUN apt-get update && \
    apt-get install -y --no-install-recommends jq curl tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的依赖和项目文件
COPY --from=builder /root/dependencies /usr/local/lib/python3.10/site-packages
COPY --from=builder /root/VintageVigil /root/VintageVigil
