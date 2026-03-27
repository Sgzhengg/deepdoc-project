"""
手机端专用API路由
提供会话管理、反馈等功能
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/mobile", tags=["Mobile"])

# ========== 简单的内存存储（生产环境应使用Redis或数据库）==========
# 会话存储：{session_id: {"messages": [...], "created_at": ..., "updated_at": ...}}
_sessions_storage: Dict[str, Dict[str, Any]] = {}

# 用户会话索引：{user_id: [session_id1, session_id2, ...]}
_user_sessions: Dict[str, List[str]] = {}

# ========== 请求/响应模型 ==========


class SessionListResponse(BaseModel):
    """会话列表响应"""
    success: bool
    sessions: List[Dict[str, Any]] = []
    total: int = 0


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str


class FeedbackRequest(BaseModel):
    """反馈请求"""
    session_id: str
    message_id: str
    feedback_type: str = Field(..., description="反馈类型: up/down")
    comment: Optional[str] = Field(None, description="可选评论")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    message: str


# ========== 辅助函数 ==========

def _get_user_id(request_headers: Dict[str, str]) -> str:
    """从请求头获取用户ID（简化版，生产环境应使用JWT）"""
    # 从自定义头部获取用户ID
    user_id = request_headers.get("X-User-ID", "anonymous")
    return user_id


def _create_session(user_id: str) -> str:
    """创建新会话"""
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }

    _sessions_storage[session_id] = session_data

    # 添加到用户会话索引
    if user_id not in _user_sessions:
        _user_sessions[user_id] = []
    _user_sessions[user_id].insert(0, session_id)  # 最新的在前

    # 限制每个用户最多保存50个会话
    if len(_user_sessions[user_id]) > 50:
        old_session_id = _user_sessions[user_id].pop()
        if old_session_id in _sessions_storage:
            del _sessions_storage[old_session_id]

    return session_id


def _add_message_to_session(session_id: str, role: str, content: str, **metadata):
    """向会话添加消息"""
    if session_id not in _sessions_storage:
        return None

    message_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    message = {
        "message_id": message_id,
        "role": role,  # "user" or "assistant"
        "content": content,
        "timestamp": now,
        **metadata
    }

    _sessions_storage[session_id]["messages"].append(message)
    _sessions_storage[session_id]["updated_at"] = now

    return message_id


def _get_or_create_session(session_id: Optional[str], user_id: str) -> str:
    """获取或创建会话"""
    if session_id and session_id in _sessions_storage:
        # 验证会话是否属于该用户
        if _sessions_storage[session_id]["user_id"] == user_id:
            return session_id

    # 创建新会话 - 如果用户提供了session_id但不存在，使用该ID创建
    if session_id:
        return _create_session_with_id(user_id, session_id)

    # 否则创建随机ID的新会话
    return _create_session(user_id)


def _create_session_with_id(user_id: str, session_id: str) -> str:
    """使用指定ID创建新会话（用于支持客户端提供的session_id）"""
    now = datetime.now().isoformat()

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }

    _sessions_storage[session_id] = session_data

    # 添加到用户会话索引
    if user_id not in _user_sessions:
        _user_sessions[user_id] = []
    _user_sessions[user_id].insert(0, session_id)

    # 限制每个用户最多保存50个会话
    if len(_user_sessions[user_id]) > 50:
        old_session_id = _user_sessions[user_id].pop()
        if old_session_id in _sessions_storage:
            del _sessions_storage[old_session_id]

    return session_id


# ========== API端点 ==========

@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取用户的历史会话列表

    返回最近的会话列表，每个会话包含：
    - session_id: 会话ID
    - title: 会话标题（取第一条用户消息的前30个字符）
    - created_at: 创建时间
    - updated_at: 更新时间
    - message_count: 消息数量
    """
    try:
        # TODO: 从请求获取真实用户ID
        # 这里简化处理，返回所有会话
        user_id = "default_user"

        session_ids = _user_sessions.get(user_id, [])

        # 分页
        session_ids = session_ids[offset:offset + limit]

        sessions = []
        for sid in session_ids:
            if sid in _sessions_storage:
                session = _sessions_storage[sid]
                messages = session.get("messages", [])

                # 生成标题（取第一条用户消息）
                title = "新对话"
                for msg in messages:
                    if msg.get("role") == "user":
                        title = msg.get("content", "")[:30]
                        if len(msg.get("content", "")) > 30:
                            title += "..."
                        break

                sessions.append({
                    "session_id": sid,
                    "title": title,
                    "created_at": session.get("created_at"),
                    "updated_at": session.get("updated_at"),
                    "message_count": len(messages)
                })

        return SessionListResponse(
            success=True,
            sessions=sessions,
            total=len(sessions)
        )

    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(session_id: str):
    """
    获取单个会话的完整消息历史

    返回该会话的所有消息，按时间顺序排列
    """
    try:
        if session_id not in _sessions_storage:
            raise HTTPException(status_code=404, detail="会话不存在")

        session = _sessions_storage[session_id]

        return SessionDetailResponse(
            success=True,
            session_id=session_id,
            messages=session.get("messages", []),
            created_at=session.get("created_at"),
            updated_at=session.get("updated_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除单个会话

    删除指定的会话及其所有消息
    """
    try:
        if session_id not in _sessions_storage:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 从用户索引中移除
        session = _sessions_storage[session_id]
        user_id = session.get("user_id", "default_user")

        if user_id in _user_sessions:
            if session_id in _user_sessions[user_id]:
                _user_sessions[user_id].remove(session_id)

        # 删除会话
        del _sessions_storage[session_id]

        return {
            "success": True,
            "message": "会话已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions")
async def clear_all_sessions():
    """
    清空用户的所有会话

    删除用户的所有历史会话
    """
    try:
        # TODO: 从请求获取真实用户ID
        user_id = "default_user"

        if user_id not in _user_sessions:
            return {
                "success": True,
                "message": "没有需要清除的会话",
                "deleted_count": 0
            }

        session_ids = _user_sessions[user_id][:]
        deleted_count = 0

        for session_id in session_ids:
            if session_id in _sessions_storage:
                del _sessions_storage[session_id]
                deleted_count += 1

        _user_sessions[user_id] = []

        return {
            "success": True,
            "message": f"已清除 {deleted_count} 个会话",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"清空会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    提交对AI回答的反馈

    用户可以对AI的回答进行评价（有帮助/没帮助）
    """
    try:
        # TODO: 在生产环境中，应该将反馈存储到数据库
        logger.info(
            f"收到反馈: session={feedback.session_id}, "
            f"message={feedback.message_id}, "
            f"type={feedback.feedback_type}"
        )

        return FeedbackResponse(
            success=True,
            message="反馈已提交"
        )

    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    手机端API健康检查

    检查会话存储状态
    """
    return {
        "status": "healthy",
        "service": "MobileAPI",
        "active_sessions": len(_sessions_storage),
        "timestamp": datetime.now().isoformat()
    }
