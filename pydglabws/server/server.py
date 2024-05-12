import asyncio
from asyncio import Task
from json import JSONDecodeError
from typing import Union, Optional, Sequence, Dict, Callable, Coroutine, Any

from pydantic import UUID4
from websockets import WebSocketServerProtocol
from websockets.server import serve as ws_serve

from pydglabws import WebSocketMessage, MessageType
from pydglabws.enums import MessageDataHead, RetCode


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
        self._ws_client_id_to_ws: Dict[UUID4, WebSocketServerProtocol] = {}
        self._client_id_to_target_id: Dict[UUID4, UUID4] = {}
        self._target_id_to_client_id: Dict[UUID4, UUID4] = {}
        self._message_type_to_handler: Dict[
            MessageType,
            Callable[
                [DGLabWSServer, WebSocketMessage, WebSocketServerProtocol],
                Coroutine[Any, Any, None]
            ]
        ] = {
            MessageType.BIND: self._handle_bind,
            MessageType.MSG: self._handle_msg
        }
        self._heartbeat_interval = heartbeat_interval
        self._stop_heartbeat = False
        self._heartbeat_task: Optional[Task] = None
        self._heartbeat_lock = asyncio.Lock()

    async def __aenter__(self):
        await self._serve.__aenter__()
        if self._heartbeat_interval is not None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_sender())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stop_heartbeat = True
        # 等待心跳包停止发送
        async with self._heartbeat_lock:
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
    def ws_client_ids(self):
        """
        所有的 WebSocket 客户端

        :return: A set-like object providing a view on IDs
        """
        return self._ws_client_id_to_ws.keys()

    @staticmethod
    async def _send(
            message: WebSocketMessage,
            *wss: WebSocketServerProtocol
    ):
        """
        发送 WebSocket 消息

        :param message: 要发送的消息
        :param wss: 发送目标连接
        """
        for websocket in wss:
            await websocket.send(message.model_dump_json(by_alias=True))

    async def _heartbeat_sender(self):
        """
        心跳包发送器
        """
        async with self._heartbeat_lock:
            while not self._stop_heartbeat:
                for uuid4, websocket in self._ws_client_id_to_ws.items():
                    await self._send(
                        WebSocketMessage(
                            type=MessageType.HEARTBEAT,
                            client_id=uuid4,
                            target_id=self._client_id_to_target_id.get(uuid4),
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
        uuid4 = UUID4()
        self._ws_client_id_to_ws[uuid4] = websocket
        await self._send(
            WebSocketMessage(
                type=MessageType.BIND,
                client_id=uuid4,
                message=MessageDataHead.TARGET_ID.value
            ),
            websocket
        )

        # 响应消息
        async for message in websocket:
            try:
                parsed_message = WebSocketMessage.model_validate_strings(message)
            except JSONDecodeError:
                await self._send(
                    WebSocketMessage(
                        type=MessageType.MSG,
                        message=str(RetCode.NON_JSON_CONTENT)
                    )
                )
            else:
                await self._message_handler(parsed_message, websocket)

        # 掉线处理
        self._ws_client_id_to_ws.pop(uuid4)
        if uuid4 in self._client_id_to_target_id.keys():
            notice_id = self._client_id_to_target_id[uuid4]
            self._client_id_to_target_id.pop(uuid4)
            message = WebSocketMessage(
                type=MessageType.BREAK,
                client_id=uuid4,
                target_id=notice_id,
                message=str(RetCode.CLIENT_DISCONNECTED)
            )
        else:
            notice_id = self._target_id_to_client_id[uuid4]
            self._target_id_to_client_id.pop(uuid4)
            message = WebSocketMessage(
                type=MessageType.BREAK,
                client_id=notice_id,
                target_id=uuid4,
                message=str(RetCode.CLIENT_DISCONNECTED)
            )
        await self._send(message, self._ws_client_id_to_ws[notice_id])

    async def _message_handler(
            self,
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol
    ):
        """
        消息接收器，接收消息并进行处理

        :param message: 收到的已解析的消息
        :param websocket: 消息来源连接
        """
        # 非法消息来源拒绝
        if self._ws_client_id_to_ws[message.client_id] != websocket \
                and self._ws_client_id_to_ws[message.target_id] != websocket:
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
            websocket: WebSocketServerProtocol
    ):
        """
        响应关系绑定（``bind`` 类型）消息

        :param self: :class:`DGLabWSServer` 对象
        :param message: 关系绑定消息
        :param websocket: 消息来源连接
        """
        if message.message == MessageDataHead.DG_LAB \
                and message.client_id is not None \
                and message.target_id is not None:
            msg_to_send = message.model_copy()

            # 服务端中存在 client_id 和 target_id
            if message.client_id in self._ws_client_id_to_ws and message.target_id in self._ws_client_id_to_ws:
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

            await self._send(
                msg_to_send,
                self._ws_client_id_to_ws[message.client_id],
                websocket,
            )

    @staticmethod
    async def _handle_msg(
            self: "DGLabWSServer",
            message: WebSocketMessage,
            websocket: WebSocketServerProtocol
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
                await self._send(msg_to_send, websocket)
            elif (target_ws := self._ws_client_id_to_ws[message.target_id]) == websocket:
                await self._send(msg_to_send, self._ws_client_id_to_ws[message.client_id])
            else:
                await self._send(msg_to_send, target_ws)
