import asyncio
from asyncio import Task
from typing import Union, Optional, Sequence, Dict, Callable, Coroutine, Any, Set, Literal, Tuple
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
        self._message_type_to_callbacks: Dict[
            MessageType,
            Set[Callable[[WebSocketMessage, bool], Any]]
        ] = {
            MessageType.BIND: set(),
            MessageType.MSG: set()
        }
        self._connection_callbacks: Tuple[
            Set[Callable[[UUID4, WebSocketServerProtocol], Any]],
            Set[Callable[[UUID4, WebSocketServerProtocol], Any]]
        ] = (set(), set())
        """新连接建立时 与 连接断开时"""
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
    def uuid_to_ws(self) -> Dict[UUID4, WebSocketServerProtocol]:
        """
        所有的 WebSocket 客户端 ID（包含终端与 App）到 WebSocket 连接对象的映射
        """
        return self._uuid_to_ws.copy()

    @property
    def local_client_ids(self) -> Set[UUID4]:
        """
        所有的本地终端 ID
        """
        return set(self._client_id_to_queue.keys())

    def new_local_client(self, max_queue: int = 2 ** 5) -> DGLabLocalClient:
        """
        创建新的本地终端 [`DGLabLocalClient`][pydglab_ws.client.local.DGLabLocalClient]，记录并返回
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

    async def remove_local_client(self, client_id: UUID4) -> bool:
        """
        移除已连接的本地终端，并通知 App 终端已掉线

        :param client_id: 要移除的本地终端 [`DGLabLocalClient`][pydglab_ws.client.local.DGLabLocalClient] 的 ID
        :return: 如果该终端并没有与服务端连接，返回 ``False``，否则返回 ``True``
        """
        try:
            self._client_id_to_queue.pop(client_id)
        except KeyError:
            return False
        else:
            if client_id in self._client_id_to_target_id:
                target_id = self._client_id_to_target_id.pop(client_id)
                self._target_id_to_client_id.pop(target_id)
                if websocket := self._uuid_to_ws.get(target_id):
                    message = WebSocketMessage(
                        type=MessageType.BREAK,
                        client_id=client_id,
                        target_id=target_id,
                        message=RetCode.CLIENT_DISCONNECTED
                    )
                    await self._send(message, websocket)
            return True

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

        注意此处 ``client_id`` 为心跳包接收方 ID，``target_id`` 为绑定方
        """
        while True:
            for uuid, websocket in self._uuid_to_ws.items():
                await self._send(
                    WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                        client_id=uuid,
                        target_id=self._client_id_to_target_id.get(uuid),
                        message=RetCode.SUCCESS
                    ),
                    websocket
                )
            await asyncio.sleep(self._heartbeat_interval)

    async def _ws_handler(self, websocket: WebSocketServerProtocol):
        """
        WebSocket 连接接收器，响应处理每个连接
        """
        new_connect_callbacks, disconnect_callbacks = self._connection_callbacks
        # 登记 WebSocket 客户端
        uuid = uuid4()
        self._uuid_to_ws[uuid] = websocket
        await self._send(
            WebSocketMessage(
                type=MessageType.BIND,
                client_id=uuid,
                message=MessageDataHead.TARGET_ID
            ),
            websocket
        )

        # 回调函数
        if new_connect_callbacks:
            for callback in new_connect_callbacks:
                callback_ret = callback(uuid, websocket)
                if isinstance(callback_ret, Coroutine):
                    await callback_ret

        # 响应消息
        try:
            async for message in websocket:
                try:
                    parsed_message = WebSocketMessage.model_validate_json(message)
                except ValueError:
                    await self._send(
                        WebSocketMessage(
                            type=MessageType.MSG,
                            message=RetCode.NON_JSON_CONTENT
                        ),
                        websocket
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
                message=RetCode.CLIENT_DISCONNECTED
            )
        # App 掉线
        elif notice_id := self._target_id_to_client_id.get(uuid):
            self._target_id_to_client_id.pop(uuid)
            self._client_id_to_target_id.pop(notice_id)
            message = WebSocketMessage(
                type=MessageType.BREAK,
                client_id=notice_id,
                target_id=uuid,
                message=RetCode.CLIENT_DISCONNECTED
            )
        else:
            message = None
        if message is not None:
            await self._send(
                message,
                notice_ws := self._uuid_to_ws.get(notice_id),
                to_local_client=notice_ws is None
            )

        # 回调函数
        if disconnect_callbacks:
            for callback in disconnect_callbacks:
                callback_ret = callback(uuid, websocket)
                if isinstance(callback_ret, Coroutine):
                    await callback_ret

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
                    message=RetCode.RECIPIENT_NOT_FOUND
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

        :param self: [`DGLabWSServer`][pydglab_ws.server.server.DGLabWSServer] 对象
        :param message: 关系绑定消息
        :param websocket: 消息来源连接
        """
        if message.message == MessageDataHead.DG_LAB \
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
                    msg_to_send.message = RetCode.SUCCESS
                else:
                    msg_to_send.message = RetCode.ID_ALREADY_BOUND
            else:
                msg_to_send.message = RetCode.TARGET_CLIENT_NOT_FOUND

            client_ws = self._uuid_to_ws.get(message.client_id)
            await self._send(
                msg_to_send,
                self._uuid_to_ws.get(message.client_id),
                websocket,
                to_local_client=client_ws is None
            )

            if callback_set := self._message_type_to_callbacks.get(MessageType.BIND):
                for callback in callback_set:
                    callback_ret = callback(message, msg_to_send.message == RetCode.SUCCESS)
                    if isinstance(callback_ret, Coroutine):
                        await callback_ret

    @staticmethod
    async def _handle_msg(
            self: "DGLabWSServer",
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol = None
    ):
        """
        响应 `msg` 类型的消息

        :param self: [`DGLabWSServer`][pydglab_ws.server.server.DGLabWSServer] 对象
        :param message: `msg` 类型的消息
        :param websocket: 消息来源连接
        """
        if message.client_id is not None and message.target_id is not None:
            msg_to_send = message.model_copy()
            # 检查是否为绑定关系
            if self._client_id_to_target_id.get(message.client_id) != message.target_id:
                msg_to_send.type = MessageType.BIND
                msg_to_send.message = RetCode.INCOMPATIBLE_RELATIONSHIP
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

            if callback_set := self._message_type_to_callbacks.get(MessageType.MSG):
                for callback in callback_set:
                    callback_ret = callback(message, msg_to_send.message != RetCode.INCOMPATIBLE_RELATIONSHIP)
                    if isinstance(callback_ret, Coroutine):
                        await callback_ret

    def add_receive_callback(
            self,
            message_type: Literal[MessageType.BIND, MessageType.MSG],
            func: Callable[[WebSocketMessage, bool], Any]
    ) -> bool:
        """
        添加回调函数，在收到指定类型的消息后调用
        :param message_type: 消息类型，仅支持 ``MessageType.BIND``, ``MessageType.MSG``
        :param func: 回调函数，传入消息数据和服务端处理结果，支持异步函数
        :return: 是否有找到消息类型
        """
        try:
            self._message_type_to_callbacks[message_type].add(func)
        except KeyError:
            return False
        else:
            return True

    def remove_receive_callback(
            self,
            message_type: Literal[MessageType.BIND, MessageType.MSG],
            func: Callable[[WebSocketMessage, bool], Any]
    ) -> bool:
        """
        移除在收到指定类型的消息后调用的回调函数
        :param message_type: 消息类型，仅支持 ``MessageType.BIND``, ``MessageType.MSG``
        :param func: 回调函数，传入消息数据和服务端处理结果，支持异步函数
        :return: 是否有找到消息类型和回调函数
        """
        try:
            self._message_type_to_callbacks[message_type].remove(func)
        except KeyError:
            return False
        else:
            return True

    def add_connection_callback(
            self,
            mode: Literal["new_connect", "disconnect"],
            func: Callable[[UUID4, WebSocketServerProtocol], Any]
    ) -> bool:
        """
        添加回调函数，在新的 WebSocket 连接建立时（新客户端）或连接断开时调用
        :param mode: 类型，``new_connect`` - 新连接时，处理消息之前；``disconnect`` - 连接断开时
        :param func: 回调函数，传入 终端 / App 的 ``clientId`` / ``targetId`` 和该客户端的 WebSocket 连接对象，支持异步函数
        :return: ``mode`` 参数不合法时返回 ``False``，否则返回 ``True``
        """
        new_connect_set, disconnect_set = self._connection_callbacks
        if mode == "new_connect":
            new_connect_set.add(func)
        elif mode == "disconnect":
            disconnect_set.add(func)
        else:
            return False
        return True

    def remove_connection_callback(
            self,
            mode: Literal["new_connect", "disconnect"],
            func: Callable[[UUID4, WebSocketServerProtocol], Any]
    ) -> bool:
        """
        删除在新的 WebSocket 连接建立时（新客户端）或连接断开时调用的回调函数
        :param mode: 类型，``new_connect`` - 新连接时，处理消息之前；``disconnect`` - 连接断开时
        :param func: 回调函数，传入 终端 / App 的 ``clientId`` / ``targetId`` 和该客户端的 WebSocket 连接对象，支持异步函数
        :return: ``mode`` 参数是否合法且是否找到了回调函数
        """
        new_connect_set, disconnect_set = self._connection_callbacks
        try:
            if mode == "new_connect":
                new_connect_set.remove(func)
            elif mode == "disconnect":
                disconnect_set.remove(func)
            else:
                return False
        except KeyError:
            return False
        else:
            return True
