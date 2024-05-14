from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Any, Union

from pydantic import UUID4

from ..enums import MessageDataHead, RetCode, StrengthOperationType, Channel, FeedbackButton, MessageType
from ..models import StrengthData
from ..models import WebSocketMessage
from ..typing import PulseOperation
from ..utils import dg_lab_client_qrcode, parse_strength_data, parse_feedback_data, dump_strength_operation, \
    dump_add_pulses, dump_clear_pulses

__all__ = ["DGLabClient"]


class DGLabClient(ABC):
    """
    DG-Lab 终端基础类

    :param client_id: 终端 ID
    :param target_id: App ID
    """

    def __init__(
            self,
            client_id: UUID4 = None,
            target_id: UUID4 = None
    ):
        self._client_id: Optional[UUID4] = client_id
        self._target_id: Optional[UUID4] = target_id

    @property
    def client_id(self) -> Optional[UUID4]:
        """DG-Lab 终端 ID"""
        return self._client_id

    @property
    def target_id(self) -> Optional[UUID4]:
        """DG-Lab App ID"""
        return self._target_id

    @property
    def not_registered(self) -> bool:
        """终端是否未注册"""
        return self._client_id is None

    @property
    def not_bind(self) -> bool:
        """终端是否未完成与 App 的绑定"""
        return self._client_id is None or self.target_id is None

    @abstractmethod
    async def _recv(self) -> WebSocketMessage:
        """
        收取来自 WebSocket 服务端的消息，并解析为 :class:`WebSocketMessage`
        """
        ...

    @abstractmethod
    async def _send(self, message: WebSocketMessage):
        """
        向 WebSocket 服务端发送消息

        :param message: 解析为 :class:`WebSocketMessage` 的消息
        """
        ...

    def get_qrcode(self, uri: str) -> Optional[str]:
        """
        终端二维码，二维码图像需要自行生成

        :param uri: WebSocket 服务端 URI，例如：``ws://107.47.91.92:4567``
            （注意末尾不能有 ``/``）
        :return: URL 字符串，如果需要二维码图像需要自行从返回的文本进行生成
        """
        if uri is None or self.not_registered:
            return None
        return dg_lab_client_qrcode(uri, self._client_id)

    async def _recv_owned(self) -> WebSocketMessage:
        """
        与 :meth:`_recv` 类似，但只接收目标为自身终端的消息
        """
        message = await self._recv()
        if message.client_id == self._client_id:
            return message

    async def _send_owned(self, msg_type: MessageType, msg: str):
        """
        与 :meth:`_send` 类似，但代为设置 ``client_id``, ``target_id``

        :param msg_type: :attr:`WebSocketMessage.type`
        :param msg: :attr:`WebSocketMessage.message`
        """
        message = WebSocketMessage(
            type=msg_type,
            client_id=self._client_id,
            target_id=self._target_id,
            message=msg
        )
        await self._send(message)

    async def register(self):
        """
        从 WebSocket 服务端中获取 ``client_id`` 并保存
        """
        while self.not_registered:
            message = await self._recv()
            if message.type == MessageType.BIND and message.message == MessageDataHead.TARGET_ID.value:
                self._client_id = message.client_id

    async def ensure_bind(self):
        """确保终端已完成与 App 的绑定"""
        while True:
            if self.not_registered:
                await self.register()
            elif self.not_bind:
                await self.bind()
            else:
                break

    async def bind(self) -> RetCode:
        """
        等待与 DG-Lab App 的关系绑定，并保存 ``target_id``
        :return: 响应码
        """
        while self.not_bind:
            message = await self._recv_owned()
            if message.type == MessageType.BIND and message.message.isdigit():
                ret_code = RetCode(int(message.message))
                if ret_code == RetCode.SUCCESS:
                    self._target_id = message.target_id
                return ret_code

    async def recv_app_data(self) -> Union[StrengthData, FeedbackButton]:
        """
        获取来自 DG-Lab App 的数据

        注意，获取到的是队列中最早的数据，可能不是最新的

        :return: 已解析的 **强度数据** 或 **App 反馈数据**
        """
        await self.ensure_bind()
        while True:
            message = await self._recv_owned()
            if message.type == MessageType.MSG:
                if message.message.startswith(MessageDataHead.STRENGTH.value):
                    return parse_strength_data(message.message)
                elif message.message.startswith(MessageDataHead.FEEDBACK.value):
                    return parse_feedback_data(message.message)

    async def app_data(self) -> AsyncGenerator[Union[StrengthData, FeedbackButton], Any]:
        """
        强度数据异步生成器

        注意，是从队列中最早的数据开始获取，可能不是最新的

        示例：
        ```python3
        async for data in client.app_data():
            print(f"Got data from App: {data}")
        ```
        """
        while True:
            yield await self.recv_app_data()

    async def set_strength(
            self,
            channel: Channel,
            operation_type: StrengthOperationType,
            value: int
    ):
        """
        设置强度

        :param channel: 通道选择
        :param operation_type: 强度变化模式
        :param value: 强度数值，范围在 [0, 200]
        """
        await self.ensure_bind()
        await self._send_owned(
            MessageType.MSG,
            dump_strength_operation(channel, operation_type, value)
        )

    async def add_pulses(
            self,
            channel: Channel,
            *pulses: PulseOperation
    ):
        """
        下发波形数据

        :param channel: 通道选择
        :param pulses: 波形操作数据，最大长度为 100
        """
        await self.ensure_bind()
        await self._send_owned(
            MessageType.MSG,
            dump_add_pulses(channel, *pulses)
        )

    async def clear_pulses(self, channel: Channel):
        """
        清空波形队列

        :param channel: 通道选择
        """
        await self.ensure_bind()
        await self._send_owned(
            MessageType.MSG,
            dump_clear_pulses(channel)
        )
