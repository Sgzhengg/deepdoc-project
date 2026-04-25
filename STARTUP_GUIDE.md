# DeepDoc 服务启动指南

## 🚀 快速启动

### 方式 1: 使用原服务（默认）

#### 后端
```bash
cd backend
python main.py
```

#### 前端
```bash
cd frontend
npm install  # 首次运行
npm run dev
```

访问:
- 后端: http://localhost:8000
- 前端: http://localhost:5173 (Vite 默认端口)

---

### 方式 2: 使用新的极简长上下文服务 ⭐

#### 后端
```bash
cd backend

# Windows
start_with_simple_service.bat

# Linux/Mac
export USE_SIMPLE_SERVICE=true
export USE_DEEPSEEK_API=true
python main.py
```

#### 前端（相同）
```bash
cd frontend
npm run dev
```

---

## ⚙️ 环境变量配置

### 创建 .env 文件

在 `backend/` 目录创建 `.env` 文件：

```env
# 使用 DeepSeek API
USE_DEEPSEEK_API=true
DEEPSEEK_API_KEY=your_api_key_here

# 使用极简长上下文服务
USE_SIMPLE_SERVICE=true
```

### 或者在命令行设置

```bash
# Windows CMD
set USE_SIMPLE_SERVICE=true
set USE_DEEPSEEK_API=true

# Windows PowerShell
$env:USE_SIMPLE_SERVICE="true"
$env:USE_DEEPSEEK_API="true"

# Linux/Mac
export USE_SIMPLE_SERVICE=true
export USE_DEEPSEEK_API=true
```

---

## 📁 添加测试文档

将 DOCX/XLSX 文档复制到：
```
backend/data/
```

支持的格式：
- `.docx` - Word 文档（含表格）
- `.xlsx` - Excel 文档（多工作表）

---

## 🧪 测试 API

### 健康检查
```bash
curl http://localhost:8000/health
```

### 聊天接口
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "59元套餐的通用流量分成是多少？"
  }'
```

### 使用 API 文档
浏览器访问: http://localhost:8000/docs

---

## 🔧 依赖安装

### 虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r backend/requirements-simple.txt
```

### 前端依赖
```bash
cd frontend
npm install
```

---

## 📊 服务状态检查

### 查看日志输出
启动时注意以下日志：
```
✅ 极简长上下文服务已初始化，已加载 X 个文档
📁 文档目录: backend/data
```

### 切换服务
- **原服务**: `USE_SIMPLE_SERVICE=false` 或不设置
- **新服务**: `USE_SIMPLE_SERVICE=true`

---

## ⚠️ 故障排查

### 问题 1: 服务启动失败
检查依赖是否安装：
```bash
pip install python-docx pandas openpyxl python-multipart
```

### 问题 2: 文档未加载
检查 `backend/data/` 目录是否存在且包含文档。

### 问题 3: API 返回错误
检查 `DEEPSEEK_API_KEY` 是否正确设置。

---

## 🎯 推荐启动方式（测试）

### 后端
```bash
cd backend
start_with_simple_service.bat
```

### 前端
```bash
cd frontend
npm run dev
```

### 测试查询
打开浏览器访问前端，输入测试问题：
```
59元套餐的通用流量分成是多少？
```

---

## 📞 支持

如有问题，检查：
1. 后端日志输出
2. 浏览器控制台错误
3. 环境变量是否正确设置
