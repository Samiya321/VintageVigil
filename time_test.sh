#!/bin/bash

# 定义关联数组，包含网站名称和对应的URL
declare -A urls
urls["任你购"]="https://rl.rennigou.jp/supplier/search/index"
urls["Jumpshop"]="https://jumpshop-online.com/search"
urls["Rakuma"]="http://fril.jp/s"
urls["Paypay"]="http://paypayfleamarket.yahoo.co.jp/api/v1/search"
urls["指南针"]="http://lashinbang-f-s.snva.jp"
urls["骏河屋"]="http://www.suruga-ya.jp/search"
urls["煤炉用户"]="https://api.mercari.jp/items/get_items"
urls["煤炉搜索"]="https://api.mercari.jp/v2/entities:search"
urls["Telegram"]="https://api.telegram.org"
urls["任意门"]="https://sig.doorzo.com"
urls["hoyoyo"]="https://cn.hoyoyo.com"

# 提示用户输入测试次数，如果没有输入，默认为10次
read -p "请输入测试次数（默认为10次）: " test_count
test_count=${test_count:-10}

# 遍历关联数组并对每个URL执行测试
for site_name in "${!urls[@]}"; do
  url=${urls[$site_name]}
  echo "正在测试网站：$site_name ($url)"

  # 初始化各项时间指标的累积值
  total_connect_time=0
  total_dns_time=0
  total_tls_time=0
  total_redirect_time=0
  total_pretransfer_time=0
  total_starttransfer_time=0
  total_total_time=0

  # 执行用户指定次数的Curl请求并计算各项时间指标的总和
  for ((i=1; i<=$test_count; i++)); do
    result=$(curl -w "连接时间: %{time_connect}\nDNS解析时间: %{time_namelookup}\nTLS握手时间: %{time_appconnect}\n重定向时间: %{time_redirect}\n准备传输时间: %{time_pretransfer}\n传输开始时间: %{time_starttransfer}\n总时间: %{time_total}\n" -o /dev/null -s "$url")

    # 从结果中提取并累加时间指标
    connect_time=$(echo "$result" | grep "连接时间" | awk '{print $NF}')
    dns_time=$(echo "$result" | grep "DNS解析时间" | awk '{print $NF}')
    tls_time=$(echo "$result" | grep "TLS握手时间" | awk '{print $NF}')
    redirect_time=$(echo "$result" | grep "重定向时间" | awk '{print $NF}')
    pretransfer_time=$(echo "$result" | grep "准备传输时间" | awk '{print $NF}')
    starttransfer_time=$(echo "$result" | grep "传输开始时间" | awk '{print $NF}')
    total_time=$(echo "$result" | grep "总时间" | awk '{print $NF}')

    # 累加各项时间
    total_connect_time=$(echo "$total_connect_time + $connect_time" | bc)
    total_dns_time=$(echo "$total_dns_time + $dns_time" | bc)
    total_tls_time=$(echo "$total_tls_time + $tls_time" | bc)
    total_redirect_time=$(echo "$total_redirect_time + $redirect_time" | bc)
    total_pretransfer_time=$(echo "$total_pretransfer_time + $pretransfer_time" | bc)
    total_starttransfer_time=$(echo "$total_starttransfer_time + $starttransfer_time" | bc)
    total_total_time=$(echo "$total_total_time + $total_time" | bc)

    # echo "第 $i 次测试完成"
  done

  # 计算平均值并输出
  average_connect_time=$(echo "scale=4; $total_connect_time / $test_count" | bc)
  average_dns_time=$(echo "scale=4; $total_dns_time / $test_count" | bc)
  average_tls_time=$(echo "scale=4; $total_tls_time / $test_count" | bc)
  average_redirect_time=$(echo "scale=4; $total_redirect_time / $test_count" | bc)
  average_pretransfer_time=$(echo "scale=4; $total_pretransfer_time / $test_count" | bc)
  average_starttransfer_time=$(echo "scale=4; $total_starttransfer_time / $test_count" | bc)
  average_total_time=$(echo "scale=4; $total_total_time / $test_count" | bc)
  
  echo "$site_name 的平均时间指标:"
  printf "连接时间 平均值: %.4f 秒\n" $average_connect_time
  printf "DNS解析时间 平均值: %.4f 秒\n" $average_dns_time
  printf "TLS握手时间 平均值: %.4f 秒\n" $average_tls_time
  printf "重定向时间 平均值: %.4f 秒\n" $average_redirect_time
  printf "准备传输时间 平均值: %.4f 秒\n" $average_pretransfer_time
  printf "传输开始时间 平均值: %.4f 秒\n" $average_starttransfer_time
  printf "总时间 平均值: %.4f 秒\n" $average_total_time
  echo "-----------------------------------------"
done  