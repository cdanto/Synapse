#!/bin/bash
export PYTHONIOENCODING="utf-8"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

export LLAMA_URL="http://127.0.0.1:8080/v1/chat/completions"
export LLAMA_MODEL="qwen2.5-7b-instruct"
python3 chat_stream.py