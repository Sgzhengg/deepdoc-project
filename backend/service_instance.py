"""
全局服务实例 - 用于在模块间共享服务
"""
_chat_service = None
_embedding_service = None
_vector_storage = None


def set_chat_service(service):
    """设置聊天服务"""
    global _chat_service
    _chat_service = service


def get_chat_service():
    """获取聊天服务"""
    return _chat_service


def set_embedding_service(service):
    """设置嵌入服务"""
    global _embedding_service
    _embedding_service = service


def get_embedding_service():
    """获取嵌入服务"""
    return _embedding_service


def set_vector_storage(service):
    """设置向量存储服务"""
    global _vector_storage
    _vector_storage = service


def get_vector_storage():
    """获取向量存储服务"""
    return _vector_storage
