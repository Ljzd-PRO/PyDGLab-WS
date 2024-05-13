"""
此处定义了一些 Pydantic 模型，使用 Pydantic V2
"""
from typing import Optional

from pydantic import BaseModel, UUID4, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel

from .enums import MessageType

__all__ = ("WebSocketMessage", "StrengthData")


class WebSocketMessage(BaseModel):
    """
    WebSocket 消息

    :ivar type: 消息类型
    :ivar client_id: 第三方终端 ID
    :ivar target_id: App ID
    :ivar message: 消息 / 指令
    """
    model_config = ConfigDict(alias_generator=to_camel)

    type: MessageType
    client_id: Optional[UUID4]
    target_id: Optional[UUID4]
    message: str

    @field_serializer("client_id", "target_id", when_used="json")
    def serialize_id(self, value: Optional[UUID4]):
        return value or ""


class StrengthData(BaseModel):
    """
    强度数据

    :ivar a: A 通道强度
    :ivar b: B 通道强度
    :ivar a_limit: A 通道强度上限
    :ivar b_limit: B 通道强度上限
    """
    a: int
    b: int
    a_limit: int
    b_limit: int
