#!/bin/bash

while true; do
    # 使用pgrep检查main.py是否在运行
    if ! pgrep -f "python ./main.py" > /dev/null; then # 不输出进程id
        python ./main.py > /dev/null 2>&1 # 丢弃输出
    fi
    sleep 180  # 检查间隔时间，此处设置为每180秒检查一次
done