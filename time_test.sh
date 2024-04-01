#!/bin/bash

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 检查并安装依赖
check_install() {
    local dependencies=("curl" "bc" "awk")
    for dep in "${dependencies[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            echo -e "${RED}${dep} 未安装，正在尝试安装...${NC}"
            if sudo apt-get install "$dep" -y || sudo yum install "$dep" -y || brew install "$dep"; then
                echo -e "${GREEN}${dep} 安装成功。${NC}"
            else
                echo -e "${RED}安装 ${dep} 失败，请手动安装。${NC}"
                exit 1
            fi
        fi
    done
}

# 初始化关联数组来存储网站和相应的平均时间
declare -A sites=(
    ["https://rl.rennigou.jp/supplier/search/index"]=""
    ["https://jumpshop-online.com/search"]=""
    ["http://fril.jp/s"]=""
    ["http://paypayfleamarket.yahoo.co.jp/api/v1/search"]=""
    ["http://lashinbang-f-s.snva.jp"]=""
    ["http://www.suruga-ya.jp/search"]=""
    ["https://api.mercari.jp/v2/entities:search"]=""
    ["https://api.telegram.org"]=""
    ["https://sig.doorzo.com"]=""
    ["https://cn.hoyoyo.com"]=""
)

check_install

test_time=5

echo "开始测试网站响应时间..."

# 遍历网站进行测试
for site in "${!sites[@]}"; do
    echo -e "${GREEN}正在测试${NC} $site"
    total_time=0

    for ((i=1; i<=test_time; i++)); do
        time=$(curl -o /dev/null -s -w '%{time_total}' "$site")
        time_ms=$(echo "$time * 1000" | bc)
        total_time=$(echo "$total_time+$time_ms" | bc)
        echo -e "尝试 $i: ${time_ms} ms"
    done

    average_time=$(echo "scale=2; $total_time / $test_time" | bc)
    sites[$site]=$average_time
done

# 输出结果
max_length=0
for site in "${!sites[@]}"; do
    if [ ${#site} -gt $max_length ]; then
        max_length=${#site}
    fi
done
if [ $max_length -lt 30 ]; then
    max_length=30
fi

echo -e "\n网站响应时间测试结果："
printf "%-${max_length}s 平均时间(ms)\n" "网站"
echo "--------------------------------------------------------------"
for site in "${!sites[@]}"; do
    printf "%-${max_length}s %s ms\n" "$site" "${sites[$site]}"
done

echo -e "\n测试完成。"
