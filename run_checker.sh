#!/bin/bash

while true; do
    # 使用pgrep检查main.py是否在运行
    if ! pgrep -f "python3 /home/linuxuser/test/main.py" > /dev/null; then # 不输出进程id
        nohup python3 /home/linuxuser/test/main.py > /dev/null 2>&1 & # 丢弃输出
    fi
    sleep 60  # 检查间隔时间，此处设置为每60秒检查一次
done