# MCP+GraphRAG搭建检索增强智能体

### 环境搭建

```sh
uv init mcp-graphrag
cd mcp-graphrag

# 创建虚拟环境
uv venv
# 激活虚拟环境
source .venv/bin/activate

# 安装 MCP SDK
uv add mcp graphrag pathlib pandas

# 创建GraphRAG并构建索引（Index）
mkdir -p ./graphrag/input
graphrag init --root ./graphrag
```