# 🎯 虚拟环境安装和启动完整指南

## ✅ 安装已完成

**虚拟环境**: `venv/` (已创建)
**后端依赖**: 已安装 FastAPI, Uvicorn, python-docx, pandas, openpyxl, httpx 等
**环境配置**: `.env` 文件已配置（USE_SIMPLE_SERVICE=true）

---

## 🚀 快速启动（推荐）

### 方式 1: 使用启动脚本（最简单）

```bash
# Windows
cd backend
start_simple_venv.bat
```

### 方式 2: 手动启动

```bash
# 1. 激活虚拟环境（可选，脚本会自动使用虚拟环境）
# Windows CMD:
venv\Scripts\activate

# 2. 启动服务
cd backend
python main.py
```

---

## 📊 启动日志说明

看到以下日志表示启动成功：

```
✅ 已加载 0 个文档               ← 极简长上下文服务已启动
📁 文档目录: E:\deepdoc-project\backend\data  ← 文档目录路径
INFO:     Uvicorn running on http://0.0.0.0:8000  ← 服务已启动
```

**说明**:
- ⚠️ "已加载 0 个文档" 是正常的（`backend/data/` 目录当前为空）
- ✅ 极简长上下文服务已经启动并运行
- ✅ 服务可以正常接收 API 请求

---

## 🧪 测试 API

### 1. 健康检查
```bash
curl http://localhost:8000/health
```

### 2. 测试聊天接口
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下系统功能"
  }'
```

### 3. 测试表格查询（需要添加文档）
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "59元套餐的通用流量分成是多少？"
  }'
```

---

## 📁 添加测试文档

### 支持的格式
- **DOCX**: Word 文档（`.docx`）
- **XLSX**: Excel 文档（`.xlsx`）

### 添加步骤
```bash
# 将文档复制到 data 目录
cp /path/to/policy1.docx backend/data/
cp /path/to/policy2.xlsx backend/data/
```

### 重启服务使文档生效
```bash
# Ctrl+C 停止服务
# 重新启动
cd backend
start_simple_venv.bat
```

---

## 🔄 切换服务

### 使用极简长上下文服务（新）
```bash
cd backend
start_simple_venv.bat
```

### 使用原服务
```bash
# 修改 .env 文件
# 将 USE_SIMPLE_SERVICE=true 改为 false

# 或者直接删除/重命名 .env 文件
cd backend
ren .env .env.disabled
python main.py
```

---

## 🌐 访问服务

启动成功后访问：

- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **聊天接口**: http://localhost:8000/api/chat

---

## 📋 前端启动（可选）

如果有前端，启动方式：

```bash
cd frontend
npm install  # 首次运行
npm run dev
```

前端通常运行在: http://localhost:5173

---

## ⚠️ 故障排查

### 问题 1: 虚拟环境不存在
```bash
# 重新创建虚拟环境
python -m venv venv

# 安装依赖
venv\Scripts\activate
pip install python-dotenv fastapi uvicorn python-docx pandas openpyxl python-multipart httpx
```

### 问题 2: 依赖缺失
```bash
# 激活虚拟环境
venv\Scripts\activate

# 安装缺失依赖
pip install python-dotenv fastapi uvicorn python-docx pandas openpyxl python-multipart httpx
```

### 问题 3: 端口被占用
```bash
# 查找占用端口的进程
netstat -ano | findstr :8000

# 杀死进程（如果需要）
taskkill /F /PID [进程ID]
```

### 问题 4: 服务启动失败
检查：
1. 虚拟环境是否正确创建
2. 依赖是否全部安装
3. .env 文件是否存在且配置正确
4. 端口 8000 是否被占用

---

## 🎯 推荐测试流程

1. **启动后端服务**
   ```bash
   cd backend
   start_simple_venv.bat
   ```

2. **检查启动日志**
   - 确认看到 "✅ 已加载 X 个文档"
   - 确认服务运行在 http://0.0.0.0:8000

3. **测试 API**
   - 浏览器访问 http://localhost:8000/docs
   - 测试 `/api/chat` 接口

4. **添加测试文档**
   - 将 DOCX/XLSX 文档复制到 `backend/data/`
   - 重启服务
   - 测试文档查询功能

---

## ✅ 当前状态

**虚拟环境**: ✅ 已创建并配置
**依赖安装**: ✅ 后端核心依赖已安装
**环境配置**: ✅ .env 文件已配置
**启动脚本**: ✅ `start_simple_venv.bat` 已创建
**服务状态**: ✅ 可以启动

**现在可以使用 `start_simple_venv.bat` 启动服务了！**
