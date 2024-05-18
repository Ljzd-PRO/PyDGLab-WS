from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Any, Union, Dict, Callable, Literal, Type, TypeVar

from pydantic import UUID4

from ..enums import MessageDataHead, RetCode, StrengthOperationType, Channel, FeedbackButton, MessageType
from ..models import StrengthData
from ..models import WebSocketMessage
from ..typing import PulseOperation
from ..utils import dg_lab_client_qrcode, parse_strength_data, parse_feedback_data, dump_strength_operation, \
    dump_add_pulses, dump_clear_pulses

__all__ = ["DGLabClient"]

_DataType = TypeVar("_DataType", Type[StrengthData], Type[FeedbackButton], Type[RetCode])


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
        self._message_type_to_handler: Dict[
            MessageType,
            Callable[[WebSocketMessage], Any]
        ] = {
            MessageType.MSG: self._handle_msg,
            MessageType.BREAK: self._handle_break,
            MessageType.HEARTBEAT: self._handle_heartbeat
        }

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
        收取来自 WebSocket 服务端的消息，并解析为 [`WebSocketMessage`][pydglab_ws.models.WebSocketMessage]
        """
        ...

    @abstractmethod
    async def _send(self, message: WebSocketMessage):
        """
        向 WebSocket 服务端发送消息

        :param message: 解析为 [`WebSocketMessage`][pydglab_ws.models.WebSocketMessage] 的消息
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

    @staticmethod
    def _handle_msg(message: WebSocketMessage) -> Optional[Union[StrengthData, FeedbackButton]]:
        """
        处理类型为 ``msg`` 的消息

        :raise InvalidStrengthData: [`InvalidStrengthData`][pydglab_ws.exceptions.InvalidStrengthData]
        :raise InvalidFeedbackData: [`InvalidFeedbackData`][pydglab_ws.exceptions.InvalidFeedbackData]
        """
        if isinstance(message.message, str):
            if message.message.startswith(MessageDataHead.STRENGTH.value):
                return parse_strength_data(message.message)
            elif message.message.startswith(MessageDataHead.FEEDBACK.value):
                return parse_feedback_data(message.message)
        return None

    @staticmethod
    def _handle_break(message: WebSocketMessage) -> Optional[Literal[RetCode.CLIENT_DISCONNECTED]]:
        """处理类型为 ``break`` 的消息"""
        return message.message

    @staticmethod
    def _handle_heartbeat(message: WebSocketMessage) -> Optional[Literal[RetCode.SUCCESS]]:
        """处理类型为 ``heartbeat`` 的消息"""
        return message.message

    async def register(self):
        """
        从 WebSocket 服务端中获取 ``client_id`` 并保存
        """
        while self.not_registered:
            message = await self._recv()
            if message.type == MessageType.BIND and message.message == MessageDataHead.TARGET_ID:
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
            if message.type == MessageType.BIND and isinstance(message.message, RetCode):
                if message.message == RetCode.SUCCESS:
                    self._target_id = message.target_id
                return message.message

    async def recv_data(self) -> Union[StrengthData, FeedbackButton, RetCode]:
        """
        获取 WebSocket 服务端的数据

        注意，获取到的是队列中最早的数据，可能不是最新的

        :return: 可能为 **强度数据** - [`StrengthData`][pydglab_ws.models.StrengthData]、 \
            **App 反馈数据** - [`FeedbackButton`][pydglab_ws.enums.FeedbackButton] \
            、**心跳** - [`RetCode.SUCCESS`][pydglab_ws.enums.RetCode]、 \
            **App 断开连接** - [`RetCode.CLIENT_DISCONNECTED`][pydglab_ws.enums.RetCode]
        :raise InvalidStrengthData: [`InvalidStrengthData`][pydglab_ws.exceptions.InvalidStrengthData]
        :raise InvalidFeedbackData: [`InvalidFeedbackData`][pydglab_ws.exceptions.InvalidFeedbackData]
        """
        await self.ensure_bind()
        while True:
            message = await self._recv_owned()
            handler = self._message_type_to_handler.get(message.type)
            if handler and (result := handler(message)) is not None:
                return result

    async def data_generator(
            self,
            *targets: _DataType,
    ) -> AsyncGenerator[_DataType, Any]:
        """
        强度数据异步生成器

        注意，是从队列中最早的数据开始获取，可能不是最新的

        示例：
        ```python3
        async for data in client.data_generator(StrengthData, FeedbackButton):
            print(f"Got data from App: {data}")
        ```
        :param targets: 目标类型，只有为目标类型的数据会被返回，为空即默认值时则不进行限制
        :return: 可能为 **强度数据** - [`StrengthData`][pydglab_ws.models.StrengthData]、 \
            **App 反馈数据** - [`FeedbackButton`][pydglab_ws.enums.FeedbackButton] \
            、**心跳** - ``RetCode.SUCCESS``、**App 断开连接** - ``RetCode.CLIENT_DISCONNECTED``
        """
        while True:
            data = await self.recv_data()
            if not targets or type(data) in targets:
                yield data

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

        - 每条波形数据代表了 100ms 的数据，所以若每次发送的数据有 10 条，那么就是 1s 的数据。 \
          由于网络有一定延时，若要保证波形输出的连续性，建议波形数据的发送间隔略微小于波形数据的时间长度 (< 1s)
        - 数组最大长度为 100,也就是最多放置 10s 的数据，另外 App 中的波形队列最大长度为 500，即为 50s 的数据， \
          若后接收到的数据无法全部放入波形队列，多余的部分会丢弃。所以谨慎考虑您的数据长度和数据发送间隔

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
        :raise InvalidPulseOperation: [`InvalidPulseOperation`][pydglab_ws.exceptions.InvalidPulseOperation]
        """
        await self.ensure_bind()
        await self._send_owned(
            MessageType.MSG,
            dump_clear_pulses(channel)
        )
