"""安全配置模块"""
import os
from typing import List, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import logging

logger = logging.getLogger(__name__)

# API密钥认证
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# 从环境变量获取API密钥，如果未设置则使用默认密钥（仅用于开发）
VALID_API_KEYS = os.getenv("VALID_API_KEYS", "").split(",") if os.getenv("VALID_API_KEYS") else []

# 开发环境的默认密钥（生产环境必须设置环境变量）
DEFAULT_DEV_KEY = "dev-key-please-change-in-production"
if not VALID_API_KEYS:
    logger.warning("⚠️ 使用开发环境默认API密钥，生产环境请设置VALID_API_KEYS环境变量")
    VALID_API_KEYS.append(DEFAULT_DEV_KEY)

# IP白名单配置
ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",") if os.getenv("ALLOWED_IPS") else []
# 开发环境允许本地访问
if not ALLOWED_IPS:
    ALLOWED_IPS.extend(["127.0.0.1", "localhost", "::1"])

# 请求频率限制配置
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))  # 每分钟请求数
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))     # 时间窗口（秒）

# 简单的内存存储（生产环境应使用Redis）
rate_limit_store = {}

async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)):
    """验证API密钥"""
    if api_key is None:
        logger.warning("🚫 API访问被拒绝：缺少API密钥")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API密钥缺失，请在请求头中提供 X-API-Key"
        )

    if api_key not in VALID_API_KEYS:
        logger.warning(f"🚫 API访问被拒绝：无效的API密钥")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的API密钥"
        )

    logger.info(f"✅ API密钥验证成功")
    return api_key

async def verify_ip_access(client_ip: str) -> bool:
    """验证IP访问权限"""
    if not ALLOWED_IPS or "*" in ALLOWED_IPS:
        return True

    if client_ip in ALLOWED_IPS:
        return True

    logger.warning(f"🚫 IP访问被拒绝：{client_ip}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"IP地址 {client_ip} 无权访问"
    )

async def check_rate_limit(client_id: str) -> bool:
    """检查请求频率限制"""
    import time
    current_time = int(time.time())

    if client_id not in rate_limit_store:
        rate_limit_store[client_id] = []

    # 清理过期的请求记录
    rate_limit_store[client_id] = [
        req_time for req_time in rate_limit_store[client_id]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]

    # 检查是否超过限制
    if len(rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
        logger.warning(f"🚫 请求频率超限：{client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求频率超限，每分钟最多{RATE_LIMIT_REQUESTS}次请求"
        )

    # 记录本次请求
    rate_limit_store[client_id].append(current_time)
    return True

def get_client_ip(request) -> str:
    """获取客户端真实IP"""
    # 检查代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return str(request.client.host) if request.client else "unknown"