import asyncio
from asyncio import Task
from typing import Union, Optional, Sequence, Dict, Callable, Coroutine, Any, Set
from uuid import uuid4

from pydantic import UUID4
from websockets import WebSocketServerProtocol, ConnectionClosedError
from websockets.server import serve as ws_serve

from ..client.local import DGLabLocalClient
from ..enums import MessageDataHead, RetCode, MessageType
from ..models import WebSocketMessage

__all__ = ["DGLabWSServer"]


class DGLabWSServer:
    """
    DG-Lab WebSocket 服务器

    :param host: WebSocket 服务器绑定的接口
    :param port: 监听端口
    :param heartbeat_interval: 心跳包发送间隔（秒）
    :param kwargs: :class:`websockets.server.serve` 的其他参数
    """

    def __init__(
            self,
            host: Union[str, Sequence[str]],
            port: Optional[int] = None,
            heartbeat_interval: float = None,
            **kwargs
    ):
        self._serve = ws_serve(
            self._ws_handler,
            host=host,
            port=port,
            **kwargs
        )
        self._client_id_to_queue: Dict[UUID4, asyncio.Queue] = {}
        self._uuid_to_ws: Dict[UUID4, WebSocketServerProtocol] = {}
        self._client_id_to_target_id: Dict[UUID4, UUID4] = {}
        self._target_id_to_client_id: Dict[UUID4, UUID4] = {}
        self._message_type_to_handler: Dict[
            MessageType,
            Callable[
                [DGLabWSServer, WebSocketMessage, Optional[WebSocketServerProtocol]],
                Coroutine[Any, Any, None]
            ]
        ] = {
            MessageType.BIND: self._handle_bind,
            MessageType.MSG: self._handle_msg
        }
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[Task] = None

    @property
    def heartbeat_interval(self) -> Optional[float]:
        """心跳包发送间隔，可修改（秒）"""
        return self._heartbeat_interval

    @heartbeat_interval.setter
    def heartbeat_interval(self, value: float):
        if value is not None and self.heartbeat_enabled:
            self._heartbeat_interval = value

    @property
    def heartbeat_enabled(self) -> bool:
        """是否开启了心跳包发送计时器"""
        return self._heartbeat_interval is not None

    async def __aenter__(self) -> "DGLabWSServer":
        await self._serve.__aenter__()
        if self.heartbeat_enabled:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_sender())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.heartbeat_enabled:
            self._heartbeat_task.cancel()
        await self._serve.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def client_id_to_target_id(self) -> Dict[UUID4, UUID4]:
        """
        ``client_id`` 到 ``target_id`` 的映射
        """
        return self._client_id_to_target_id.copy()

    @property
    def target_id_to_client_id(self) -> Dict[UUID4, UUID4]:
        """
        ``target_id`` 到 ``client_id`` 的映射
        """
        return self._target_id_to_client_id.copy()

    @property
    def ws_client_ids(self) -> Set[UUID4]:
        """
        所有的 WebSocket 客户端 ID（包含终端与 App）
        """
        return set(self._uuid_to_ws.keys())

    @property
    def local_client_ids(self) -> Set[UUID4]:
        """
        所有的本地终端 ID
        """
        return set(self._client_id_to_queue.keys())

    def new_local_client(self, max_queue: int = 2 ** 5) -> DGLabLocalClient:
        """
        创建新的本地终端 :class:`DGLabLocalClient`，记录并返回
        :param max_queue: 终端消息队列最大长度
        :return: 创建好的本地终端对象
        """
        client_id = uuid4()
        return DGLabLocalClient(
            client_id,
            self._message_handler,
            self._client_id_to_queue.setdefault,
            max_queue
        )

    async def _send(
            self,
            message: WebSocketMessage,
            *wss: WebSocketServerProtocol,
            to_local_client: bool = False
    ):
        """
        发送 WebSocket 消息

        :param message: 要发送的消息
        :param wss: 发送目标连接
        """
        for websocket in wss:
            if websocket is not None:
                await websocket.send(message.model_dump_json(by_alias=True))
        if to_local_client:
            if queue := self._client_id_to_queue.get(message.client_id):
                await queue.put(message)

    async def _heartbeat_sender(self):
        """
        心跳包发送器
        """
        while True:
            for uuid, websocket in self._uuid_to_ws.items():
                await self._send(
                    WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                        client_id=uuid,
                        target_id=self._client_id_to_target_id.get(uuid),
                        message=str(RetCode.SUCCESS)
                    ),
                    websocket
                )
            await asyncio.sleep(self._heartbeat_interval)

    async def _ws_handler(self, websocket: WebSocketServerProtocol):
        """
        WebSocket 连接接收器，响应处理每个连接
        """
        # 登记 WebSocket 客户端
        uuid = uuid4()
        self._uuid_to_ws[uuid] = websocket
        await self._send(
            WebSocketMessage(
                type=MessageType.BIND,
                client_id=uuid,
                message=MessageDataHead.TARGET_ID.value
            ),
            websocket
        )

        # 响应消息
        try:
            async for message in websocket:
                try:
                    parsed_message = WebSocketMessage.model_validate_json(message)
                except ValueError:
                    await self._send(
                        WebSocketMessage(
                            type=MessageType.MSG,
                            message=str(RetCode.NON_JSON_CONTENT)
                        )
                    )
                else:
                    await self._message_handler(parsed_message, websocket)
        except ConnectionClosedError:
            pass

        # 掉线处理
        # 与官方标准相比，补充了解绑操作
        self._uuid_to_ws.pop(uuid)
        # 第三方终端掉线
        if notice_id := self._client_id_to_target_id.get(uuid):
            self._client_id_to_target_id.pop(uuid)
            self._target_id_to_client_id.pop(notice_id)
            message = WebSocketMessage(
                type=MessageType.BREAK,
                client_id=uuid,
                target_id=notice_id,
                message=str(RetCode.CLIENT_DISCONNECTED)
            )
        # App 掉线
        elif notice_id := self._target_id_to_client_id.get(uuid):
            self._target_id_to_client_id.pop(uuid)
            self._client_id_to_target_id.pop(notice_id)
            message = WebSocketMessage(
                type=MessageType.BREAK,
                client_id=notice_id,
                target_id=uuid,
                message=str(RetCode.CLIENT_DISCONNECTED)
            )
        else:
            message = None
        if message is not None:
            await self._send(
                message,
                is_client_id := self._uuid_to_ws.get(notice_id),
                to_local_client=is_client_id is None
            )

    async def _message_handler(
            self,
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol = None
    ):
        """
        消息接收器，接收消息并进行处理

        :param message: 收到的已解析的消息
        :param websocket: 消息来源连接
        """
        # 非法消息来源拒绝
        if websocket is not None \
                and self._uuid_to_ws.get(message.client_id) != websocket \
                and self._uuid_to_ws.get(message.target_id) != websocket:
            await self._send(
                WebSocketMessage(
                    type=MessageType.MSG,
                    message=str(RetCode.RECIPIENT_NOT_FOUND)
                )
            )
        handler = self._message_type_to_handler.get(message.type)
        if handler:
            await handler(self, message, websocket)

    @staticmethod
    async def _handle_bind(
            self: "DGLabWSServer",
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol = None
    ):
        """
        响应关系绑定（``bind`` 类型）消息

        :param self: :class:`DGLabWSServer` 对象
        :param message: 关系绑定消息
        :param websocket: 消息来源连接
        """
        if message.message == MessageDataHead.DG_LAB.value \
                and message.client_id is not None \
                and message.target_id is not None:
            msg_to_send = message.model_copy()

            # 服务端中存在 client_id 和 target_id
            if (message.client_id in self._uuid_to_ws or message.client_id in self._client_id_to_queue) \
                    and message.target_id in self._uuid_to_ws:
                # 双方均未被绑定
                if message.client_id not in self._client_id_to_target_id.keys() \
                        and message.target_id not in self._target_id_to_client_id.keys():
                    self._client_id_to_target_id[message.client_id] = message.target_id
                    self._target_id_to_client_id[message.target_id] = message.client_id
                    msg_to_send.message = str(RetCode.SUCCESS)
                else:
                    msg_to_send.message = str(RetCode.ID_ALREADY_BOUND)
            else:
                msg_to_send.message = str(RetCode.TARGET_CLIENT_NOT_FOUND)

            client_ws = self._uuid_to_ws.get(message.client_id)
            await self._send(
                msg_to_send,
                self._uuid_to_ws.get(message.client_id),
                websocket,
                to_local_client=client_ws is None
            )

    @staticmethod
    async def _handle_msg(
            self: "DGLabWSServer",
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol = None
    ):
        """
        响应 `msg` 类型的消息

        :param self: :class:`DGLabWSServer` 对象
        :param message: `msg` 类型的消息
        :param websocket: 消息来源连接
        """
        if message.client_id is not None and message.target_id is not None:
            msg_to_send = message.model_copy()
            # 检查是否为绑定关系
            if self._client_id_to_target_id.get(message.client_id) != message.target_id:
                msg_to_send.type = MessageType.BIND
                msg_to_send.message = str(RetCode.INCOMPATIBLE_RELATIONSHIP)
                await self._send(
                    msg_to_send,
                    websocket,
                    to_local_client=websocket is None
                )
            # 进行转发
            elif (target_ws := self._uuid_to_ws[message.target_id]) == websocket:
                client_ws = self._uuid_to_ws.get(message.client_id)
                await self._send(
                    msg_to_send,
                    client_ws,
                    to_local_client=client_ws is None
                )
            else:
                await self._send(msg_to_send, target_ws)
