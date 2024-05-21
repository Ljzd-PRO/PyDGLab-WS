"""
此处提供一些工具函数
"""
import json

from pydantic import UUID4

from .enums import StrengthOperationType, Channel, MessageDataHead, FeedbackButton
from .exceptions import InvalidStrengthData, InvalidFeedbackData, InvalidPulseOperation, PulseDataTooLong
from .models import StrengthData, WS_MESSAGE_MAX_LENGTH
from .typing import PulseOperation

__all__ = (
    "PULSE_DATA_MAX_LENGTH",
    "dump_pulse_operation",
    "dg_lab_client_qrcode",
    "dump_strength_operation",
    "parse_strength_data",
    "dump_add_pulses",
    "dump_clear_pulses",
    "parse_feedback_data"
)

# {"type":"msg","clientId":"","targetId":"","message":"pulse-A:[]"} - 65bit
# {"type":"msg","clientId":"`32bit`","targetId":"`32bit`","message":"pulse-A:[]"} - 129bit
# \"`16bit`\", - 21bit
# {"type":"msg","clientId":"`32bit`","targetId":"`32bit`","message":"pulse-A:[\"`16bit`\",\"`16bit`\"]"}
PULSE_DATA_MAX_LENGTH = (WS_MESSAGE_MAX_LENGTH - 129 + 1) // 21  # 86
"""
波形操作列表最大长度，计算结果为 ``86``

``(WS_MESSAGE_MAX_LENGTH - 129 + 1) // 21``
"""


def parse_strength_data(data: str) -> StrengthData:
    """
    解析消息中的强度数据

    :param data: WebSocket 消息中的 ``message``
    :raise InvalidStrengthData: [`InvalidStrengthData`][pydglab_ws.exceptions.InvalidStrengthData]
    """
    try:
        values = data.split("-")[1].split("+")
        return StrengthData(
            a=int(values[0]),
            b=int(values[1]),
            a_limit=int(values[2]),
            b_limit=int(values[3]),
        )
    except (IndexError, ValueError) as e:
        raise InvalidStrengthData(data) from e


def parse_feedback_data(data: str) -> FeedbackButton:
    """
    解析消息中的 App 反馈数据

    :param data: WebSocket 消息中的 ``message``
    :raise InvalidFeedbackData: [`InvalidFeedbackData`][pydglab_ws.exceptions.InvalidFeedbackData]
    """
    try:
        return FeedbackButton(int(data.split("-")[1]))
    except IndexError as e:
        raise InvalidFeedbackData(data) from e


def dump_strength_operation(
        channel: Channel,
        operation_type: StrengthOperationType,
        value: int
) -> str:
    """
    生成强度操作的数据

    :param channel: 通道选择
    :param operation_type: 强度变化模式
    :param value: 强度数值，范围在 [0, 200]
    :return: 返回数据可作为 WebSocket 消息中的 ``message``
    """
    return f"{MessageDataHead.STRENGTH.value}-{channel.value}+{operation_type.value}+{value}"


def dump_clear_pulses(channel: Channel) -> str:
    """
    生成波形清空操作的数据

    :param channel: 通道选择
    :return: 返回数据可作为 WebSocket 消息中的 ``message``
    """
    return f"{MessageDataHead.CLEAR.value}-{channel.value}"


def dump_pulse_operation(pulse: PulseOperation) -> str:
    """
    生成波形操作的数据

    :param pulse: 波形操作数据
    :return: 返回数据与蓝牙协议类似
    :raise InvalidPulseOperation: [`InvalidPulseOperation`][pydglab_ws.exceptions.InvalidPulseOperation]
    """
    try:
        pulse_bytes = bytes().join(
            # int.to_bytes Python 3.11 才添加了 length, byteorder 的默认参数值
            value.to_bytes(
                length=1,
                byteorder='big'
            ) for operation in pulse for value in operation
        )
    except (TypeError, AttributeError, OverflowError) as e:
        raise InvalidPulseOperation(pulse) from e
    else:
        return pulse_bytes.hex()


def dump_add_pulses(
        channel: Channel,
        *pulses: PulseOperation
) -> str:
    """
    生成下放波形操作的数据

    :param channel: 通道选择
    :param pulses: 波形操作数据
    :return: 返回数据可作为 WebSocket 消息中的 ``message``
    :raise InvalidPulseOperation: [`InvalidPulseOperation`][pydglab_ws.exceptions.InvalidPulseOperation]
    :raise PulseDataTooLong: 波形操作数据过长，最大长度应为 [`PULSE_DATA_MAX_LENGTH`][pydglab_ws.utils.PULSE_DATA_MAX_LENGTH]
    """
    if (pulses_length := len(pulses)) > PULSE_DATA_MAX_LENGTH:
        raise PulseDataTooLong(pulses_length)
    return (f"{MessageDataHead.PULSE.value}-{channel.name}"
            f":{json.dumps([dump_pulse_operation(pulse) for pulse in pulses], separators=(',', ':'))}")


def dg_lab_client_qrcode(uri: str, client_id: UUID4) -> str:
    """
    生成终端二维码，二维码图像需要自行生成

    :param uri: WebSocket 服务端 URI，例如：``ws://107.47.91.92:4567``
            （注意末尾不能有 ``/``）
    :param client_id: 终端 ID
    :return: 终端二维码内容，二维码图像需要自行生成
    """
    return (f"https://www.dungeon-lab.com/app-download.php"
            f"#DGLAB-SOCKET"
            f"#{uri}/{client_id}")
