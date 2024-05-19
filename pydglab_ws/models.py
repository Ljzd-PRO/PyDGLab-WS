"""
此处定义了一些 Pydantic 模型，使用 Pydantic V2
"""
from enum import IntEnum
from typing import Optional, Any, Union

from pydantic import BaseModel, UUID4, ConfigDict, field_serializer, AliasGenerator, model_validator, \
    field_validator
from pydantic.alias_generators import to_camel, to_snake
from pydantic_core.core_schema import SerializerFunctionWrapHandler, FieldSerializationInfo

from .enums import MessageType, RetCode, MessageDataHead

__all__ = ("WebSocketMessage", "StrengthData")


# noinspection PyNestedDecorators
class WebSocketMessage(BaseModel):
    """
    WebSocket 消息

    :ivar type: 消息类型
    :ivar client_id: 第三方终端 ID
    :ivar target_id: App ID
    :ivar message: 消息 / 指令
    """
    # 仅在序列化时将键转为驼峰命名法作为别名
    # 验证时不取别名的原因是，取别名会影响对象初始化参数名，而 AliasChoices 不知为何不起作用
    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel
        )
    )

    type: MessageType
    client_id: Optional[UUID4] = None
    target_id: Optional[UUID4] = None
    message: Union[str, RetCode, MessageDataHead]

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: Any):
        """自动先行尝试解析 `message`"""
        if isinstance(value, str):
            try:
                return RetCode(int(value))
            except ValueError:
                try:
                    return MessageDataHead(value)
                except ValueError:
                    pass
        return value

    @field_serializer("message", mode="wrap")
    def _serialize_message(self, value: Any, nxt: SerializerFunctionWrapHandler, _: FieldSerializationInfo):
        """对于 ``IntEnum`` 的枚举，转化为 ``str``"""
        if isinstance(value, IntEnum):
            return str(value.value)
        else:
            return nxt(value)

    @field_serializer("client_id", "target_id")
    def _serialize_id(self, value: Optional[UUID4]):
        """序列化时，当值为 ``None``，序列化成空字符串"""
        return value or ""

    @field_validator("client_id", "target_id", mode="before")
    @classmethod
    def _validate_id(cls, value: Any):
        """验证 UUID 值时，当值为空字符串，更改为 ``None``，与 :meth:`serialize_id` 相对应"""
        return value if value != "" else None

    @model_validator(mode="before")
    @classmethod
    def _field_to_pascal(cls, data: Any):
        """
        验证模型时，将所有的键名更改为蛇形命名法（下划线）

        验证时不取别名的原因是，取别名会影响对象初始化参数名，而 ``AliasChoices`` 不知为何不起作用
        """
        if isinstance(data, dict):
            for key in list(data.keys()):
                data[to_snake(key)] = data.pop(key)
        return data


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
