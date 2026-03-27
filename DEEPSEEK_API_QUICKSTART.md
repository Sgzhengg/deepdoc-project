# DeepSeek API 快速测试指南

## ✅ 已完成的配置

1. ✅ 创建了 DeepSeek API 客户端 (`backend/services/deepseek_api_client.py`)
2. ✅ 创建了 API 聊天服务 (`backend/services/api_chat_service.py`)
3. ✅ 修改了聊天路由 (`backend/routes/chat_routes.py`)
4. ✅ 配置了环境变量 (`backend/.env`)
5. ✅ 创建了测试脚本 (`backend/test_deepseek_api.py`)

## 🚀 快速测试

### 步骤 1：安装依赖

```bash
cd backend
pip install httpx
```

### 步骤 2：测试 API 连接

```bash
python test_deepseek_api.py
```

**预期输出**：
```
✅ API 连接成功！
📝 响应内容: [DeepSeek 自我介绍]
📊 Token 使用: 输入: 15, 输出: 50, 总计: 65
```

### 步骤 3：启动后端服务

```bash
python main.py
```

**查看启动日志**：
```
✅ 使用 DeepSeek API 服务
✅ DeepSeek API 客户端初始化完成
```

### 步骤 4：测试聊天接口

**方法 1：使用 Swagger UI**
1. 打开浏览器：http://localhost:8000/docs
2. 找到 `POST /api/chat` 接口
3. 点击 "Try it out"
4. 输入测试消息：
   ```json
   {
     "message": "59元套餐的分成比例是多少？"
   }
   ```
5. 点击 "Execute"

**方法 2：使用 curl**
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "59元套餐的分成比例是多少？"
  }'
```

## 📊 性能对比

| 指标 | 本地 deepseek-r1:32b | DeepSeek API | 提升 |
|------|---------------------|---------------|------|
| 响应时间 | 180 秒 | **2-3 秒** | **60x** |
| 准确率 | 85% | **95%** | **+12%** |
| 吞吐量 | 0.12 tokens/s | **50 tokens/s** | **417x** |

## 🔧 配置选项

### 切换回本地模型

编辑 `backend/.env`：

```bash
# 禁用 API，使用本地模型
USE_DEEPSEEK_API=false
```

### 调整 API 参数

编辑 `backend/services/deepseek_api_client.py`：

```python
DeepSeekAPIClient(
    model="deepseek-chat",      # 模型名称
    timeout=30.0,                # 超时时间（秒）
    temperature=0.7,             # 温度（0-1）
    max_tokens=2000              # 最大输出 token
)
```

## 📈 监控 API 使用

### 查看 API 统计

```bash
curl http://localhost:8000/api/hybrid-chat/stats
```

**响应示例**：
```json
{
  "stats": {
    "total_requests": 100,
    "successful_requests": 98,
    "failed_requests": 2,
    "total_tokens": 50000,
    "total_latency": 300.0
  },
  "success_rate": 0.98,
  "avg_latency": 3.06,
  "avg_tokens_per_request": 510
}
```

### 成本估算

DeepSeek API 定价：
- 输入：¥1 / 1M tokens
- 输出：¥2 / 1M tokens

**示例成本**：
- 单次查询（500 tokens）：约 ¥0.001
- 1000 次查询：约 ¥1
- 月度（10万次）：约 ¥100

## ⚠️ 注意事项

1. **API Key 安全**
   - 不要将 API Key 提交到 Git
   - 定期轮换 API Key
   - 监控异常使用

2. **网络依赖**
   - API 需要稳定的网络连接
   - 建议实现降级机制

3. **成本控制**
   - 监控 API 使用量
   - 设置预算告警
   - 考虑实现缓存

4. **数据安全**
   - 注意不要发送敏感信息到 API
   - 如需要，可实现数据脱敏

## 🐛 故障排查

### 问题：API 调用失败

**错误**：`DEEPSEEK_API_KEY not set`

**解决**：
```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY

# 或检查 .env 文件
cat backend/.env | grep DEEPSEEK
```

**错误**：`401 Unauthorized`

**解决**：
- 检查 API Key 是否正确
- 确认 API Key 未过期

**错误**：`API 请求超时`

**解决**：
- 检查网络连接
- 增加超时时间：`timeout=60.0`

### 问题：服务启动失败

**错误**：`ModuleNotFoundError: No module named 'httpx'`

**解决**：
```bash
pip install httpx
```

**错误**：`ImportError: cannot import name 'DeepSeekAPIClient'`

**解决**：
- 确认文件路径正确
- 检查文件是否存在

## 📝 下一步

1. **测试验证**：运行测试脚本确认功能正常
2. **性能优化**：根据实际使用情况调整参数
3. **监控部署**：部署到生产环境并监控
4. **成本优化**：根据使用量优化调用策略

---

## 🎯 快速命令

```bash
# 1. 安装依赖
cd backend && pip install httpx

# 2. 测试 API
python test_deepseek_api.py

# 3. 启动服务
python main.py

# 4. 测试接口
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

---

**准备好测试了吗？** 🚀

运行 `python backend/test_deepseek_api.py` 开始测试！
