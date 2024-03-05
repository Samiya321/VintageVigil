#!/bin/sh

# 指定目标目录
TARGET_DIR="/root/VintageVigil/user/user"

# Base64编码的GitHub Tokens数组
TOKENS_B64='WyJnaHBfYnBxYVVzbHFSWFJKZHZwVEpQRHlJcW5mYkZlRjJCM1BYcHdaIiwiZ2hwXzhGclJWSGRFSVdvYUpjNHpoVkFCb1prTUF2ZHZ2RjNOa1NjQyIsImdocF9kMmpZTFFGMkJTVmlKWGRWdlRoaXFHbFBaa1cxQW4wejNFOFYiLCJnaHBfZlltUk1nY0w4bGtKb3Q2aXlTT3A5NzBPNmV2U0JFMmdZRFplIiwiZ2hwX0VTTm9XTGtxUVFHVWpnQ1lVY3FiYkV0bTltbkx3UDJWMGhCMyJd'

# 从环境变量读取监控间隔时间，默认为60秒
CHECK_INTERVAL=${CHECK_INTERVAL:-60}

# 从环境变量读取是否使用Authorization头，默认为True
USE_TOKEN=${USE_TOKEN:-True}

# 解码Token数组
get_tokens() {
  echo "$TOKENS_B64" | base64 -d | jq -r '.[]'
}

# 解析仓库信息和分支名称
parse_config() {
  REPO_OWNER=$(echo $CONFIG_PATH | sed -E 's|https://github.com/([^/]*)/.*|\1|')
  REPO_NAME=$(echo $CONFIG_PATH | sed -E 's|https://github.com/[^/]*/([^/]*)/.*|\1|')
  BRANCH=$(echo $CONFIG_PATH | sed -E 's|https://github.com/[^/]*/[^/]*/tree/([^/]*)/.*|\1|')
  FOLDER_PATH=$(echo $CONFIG_PATH | sed -E 's|https://github.com/.*/tree/[^/]*/(.*)|\1|')
}

# 使用多个Token尝试请求直到成功或尝试完所有Token
try_request_with_tokens() {
  local url=$1
  local success=false
  for token in $(get_tokens); do
    if [ "$USE_TOKEN" = "True" ]; then
      response=$(curl -s -H "Authorization: Bearer $token" -o response.json -w "%{http_code}" "$url")
    else
      response=$(curl -s -o response.json -w "%{http_code}" "$url")
    fi
    # 检查响应码是否为200
    if [ "$response" -eq 200 ]; then
      success=true
      break
    fi
  done
  if [ "$success" = true ]; then
    cat response.json
  else
    echo "All tokens failed or no valid response."
    return 1
  fi
}

# 递归下载目录内容
download_folder_contents() {
  local repo_owner=$1
  local repo_name=$2
  local branch=$3
  local folder_path=$4
  local target_dir=$5

  echo "Downloading contents of $folder_path from $repo_owner/$repo_name at branch $branch to $target_dir"

  local files_url="https://api.github.com/repos/$repo_owner/$repo_name/contents/$folder_path?ref=$branch"
  local files_response=$(try_request_with_tokens "$files_url")
  if [ $? -ne 0 ]; then
    echo "Failed to retrieve files list."
    return
  fi
  local items=$(echo "$files_response" | jq -r '.[] | @base64')

  for item in $items; do
    _jq() {
      echo ${item} | base64 -d | jq -r ${1}
    }
    item_type=$(_jq '.type')
    item_path=$(_jq '.path')
    item_download_url=$(_jq '.download_url')
    download_url="${item_download_url}?token=$(date +%s)"
    file_target_path="$target_dir/${item_path#$FOLDER_PATH/}"
    if [ "$item_type" = "dir" ]; then
      mkdir -p "$file_target_path"
      download_folder_contents "$repo_owner" "$repo_name" "$branch" "$item_path" "$target_dir"
    else
      echo "Downloading $download_url to $file_target_path"
      curl -s -L "$download_url" -o "$file_target_path"
    fi
  done
}

initialize_or_update_repo() {
  # 检查CONFIG_PATH是否已设置
  if [ -z "$CONFIG_PATH" ]; then
    echo "CONFIG_PATH未设置。仅运行python /root/VintageVigil/main.py。"
    cd /root/VintageVigil
    python main.py &
    MAIN_PY_PID=$!
    echo "python /root/VintageVigil/main.py 的 PID 为 $MAIN_PY_PID"
    wait $MAIN_PY_PID
    exit 0
  fi

  parse_config
  
  mkdir -p "$TARGET_DIR"
  local repo_tree_url="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/git/trees/$BRANCH?recursive=1"
  local repo_tree_response=$(try_request_with_tokens "$repo_tree_url")
  if [ $? -ne 0 ]; then
    echo "Failed to retrieve repository tree."
    return
  fi
  local new_folder_hash=$(echo "$repo_tree_response" | jq -r ".tree[] | select(.path==\"$FOLDER_PATH\") | .sha")

  if [ -z "$new_folder_hash" ]; then
    echo "Failed to retrieve FOLDER_HASH."
    return
  fi

  echo "Current folder hash: $LAST_FOLDER_HASH, New folder hash: $new_folder_hash"
  
  if [ "$new_folder_hash" != "$LAST_FOLDER_HASH" ]; then
    echo "Detected changes in $CONFIG_PATH. Updating files..."
    LAST_FOLDER_HASH="$new_folder_hash"

    # Terminate the current running main.py process
    if [ ! -z "$MAIN_PY_PID" ]; then
      kill $MAIN_PY_PID
      while kill -0 $MAIN_PY_PID 2>/dev/null; do
        echo "Waiting for process $MAIN_PY_PID to terminate"
        sleep 1
      done
    fi
    # 确保目录存在，防止rm命令因路径不存在而失败
    if [ -d "$TARGET_DIR" ]; then
      # 删除目录下所有内容
      rm -rf "$TARGET_DIR"/*
      
      # 等待直到$TARGET_DIR为空
      while [ "$(ls -A $TARGET_DIR)" ]; do
        echo "Waiting for $TARGET_DIR to be fully cleared"
        sleep 1
      done
    fi
    echo "All files have been deleted."
    
    download_folder_contents "$REPO_OWNER" "$REPO_NAME" "$BRANCH" "$FOLDER_PATH" "$TARGET_DIR"
    echo "All files have been downloaded."
    
    cd /root/VintageVigil
    if [ -f "main.py" ]; then
        python main.py &
        MAIN_PY_PID=$!
        echo "Restarted python /root/VintageVigil/main.py with PID $MAIN_PY_PID"
    else
        echo "main.py does not exist in /root/VintageVigil"
    fi
  else
    echo "No changes detected."
  fi
}

# 初始哈希值设置为一个空值，以便首次执行时触发更新
LAST_FOLDER_HASH=""

# 初始设置或更新
initialize_or_update_repo

# 间歇性监控循环
while true; do
  sleep "$CHECK_INTERVAL"
  initialize_or_update_repo
done
