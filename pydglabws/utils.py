"""
此处提供一些工具函数
"""
import json

from pydantic import UUID4

from .enums import StrengthOperationType, Channel, MessageDataHead, FeedbackButton
from .exceptions import InvalidStrengthData, InvalidFeedbackData
from .models import StrengthData
from .typing import PulseOperation

__all__ = (
    "dump_pulse_operation",
    "dg_lab_client_qrcode",
    "dump_strength_operation",
    "parse_strength_data",
    "dump_add_pulses",
    "dump_clear_pulses",
    "parse_feedback_data"
)


def parse_strength_data(data: str) -> StrengthData:
    """
    解析消息中的强度数据

    :param data: WebSocket 消息中的 ``message``
    :raise InvalidStrengthData: :class:`InvalidStrengthData`
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
    :raise InvalidFeedbackData: :class:`InvalidFeedbackData`
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
    :return: 返回数据可作为 WebSocket 消息中的 ``message``
    """
    pulse_bytes = bytes().join(
        value.to_bytes() for operation in pulse for value in operation
    )
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
    """
    dict_data = {
        f"{MessageDataHead.PULSE.value}-{channel.value}": [dump_pulse_operation(pulse) for pulse in pulses]
    }
    return json.dumps(dict_data)


def dg_lab_client_qrcode(host: str, port: int, client_id: UUID4):
    """
    生成终端二维码，二维码图像需要自行生成

    :param host: WebSocket 服务端主机
    :param port: WebSocket 服务端端口
    :param client_id: 终端 ID
    :return:
    """
    return (f"https://www.dungeon-lab.com/app-download.php"
            f"#DGLAB-SOCKET"
            f"#wss://{host}:{port}/{client_id}")
