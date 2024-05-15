"""
此处定义了一些常量枚举
"""
import enum
from enum import Enum, IntEnum

__all__ = (
    "MessageType",
    "RetCode",
    "MessageDataHead",
    "StrengthOperationType",
    "FeedbackButton",
    "Channel"
)


@enum.unique
class MessageType(str, Enum):
    """
    WebSocket 消息类型

    :ivar HEARTBEAT: 心跳包数据
    :ivar BIND: ID 关系绑定
    :ivar MSG: 波形下发/强度变化/队列清空等数据指令
    :ivar BREAK: 连接断开
    :ivar ERROR: 服务错误
    """
    HEARTBEAT = "heartbeat"
    BIND = "bind"
    MSG = "msg"
    BREAK = "break"
    ERROR = "error"


@enum.unique
class RetCode(IntEnum):
    """
    WebSocket 消息错误码枚举

    :ivar SUCCESS: 成功
    :ivar CLIENT_DISCONNECTED: 对方客户端已断开
    :ivar INVALID_CLIENT_ID: 二维码中没有有效的 ``clientId``
    :ivar SERVER_DELAY: Socket 连接上了，但服务器迟迟不下发 App 端的 ID 来绑定
    :ivar ID_ALREADY_BOUND: 此 ID 已被其他客户端绑定关系
    :ivar TARGET_CLIENT_NOT_FOUND: 要绑定的目标客户端不存在
    :ivar INCOMPATIBLE_RELATIONSHIP: 收信方和寄信方不是绑定关系
    :ivar NON_JSON_CONTENT: 发送的内容不是标准 JSON 对象
    :ivar RECIPIENT_NOT_FOUND: 未找到收信人（离线）
    :ivar MESSAGE_TOO_LONG: 下发的 ``message`` 长度大于 1950
    :ivar SERVER_INTERNAL_ERROR: 服务器内部异常
    """
    SUCCESS = 200
    CLIENT_DISCONNECTED = 209
    INVALID_CLIENT_ID = 210
    SERVER_DELAY = 211
    ID_ALREADY_BOUND = 400
    TARGET_CLIENT_NOT_FOUND = 401
    INCOMPATIBLE_RELATIONSHIP = 402
    NON_JSON_CONTENT = 403
    RECIPIENT_NOT_FOUND = 404
    MESSAGE_TOO_LONG = 405
    SERVER_INTERNAL_ERROR = 500


@enum.unique
class MessageDataHead(str, Enum):
    """
    WebSocket 消息数据开头部分

    :ivar TARGET_ID: Socket 通道与终端绑定
    :ivar DG_LAB: 关系绑定
    :ivar STRENGTH: 强度操作
    :ivar PULSE: 波形操作
    :ivar CLEAR: 清空波形队列
    :ivar FEEDBACK: App 反馈
    """
    TARGET_ID = "targetId"
    # noinspection SpellCheckingInspection
    DG_LAB = "DGLAB"
    STRENGTH = "strength"
    PULSE = "pulse"
    CLEAR = "clear"
    FEEDBACK = "feedback"


@enum.unique
class StrengthOperationType(IntEnum):
    """
    强度变化模式

    :ivar DECREASE: 通道强度减少
    :ivar INCREASE: 通道强度增加
    :ivar SET_TO: 通道强度变化为指定数值
    """
    DECREASE = 0
    INCREASE = 1
    SET_TO = 2


# class StrengthOperationType(Enum):
#     """
#     强度变化模式
#
#     :ivar NONE: 代表对应通道强度不做改变，对应通道的强度设定值无论是什么都无效
#     :ivar INCREASE: 代表对应通道强度相对增加变化
#     :ivar DECREASE: 代表对应通道强度相对减少变化
#     :ivar SET_TO: 代表对应通道强度绝对变化
#     """
#     NONE = 0b00
#     INCREASE = 0b01
#     DECREASE = 0b10
#     SET_TO = 0b11


@enum.unique
class FeedbackButton(IntEnum):
    """
    App 反馈按钮

    * A 通道 5 个按钮（从左至右）的角标为 0,1,2,3,4
    * B 通道 5 个按钮（从左至右）的角标为 5,6,7,8,9
    """
    A1 = 0
    A2 = 1
    A3 = 2
    A4 = 3
    A5 = 4
    B1 = 5
    B2 = 6
    B3 = 7
    B4 = 8
    B5 = 9


@enum.unique
class Channel(IntEnum):
    """
    通道

    :ivar A: A 通道
    :ivar B: B 通道
    """
    A = 1
    B = 2
