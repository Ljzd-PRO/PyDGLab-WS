import asyncio
from typing import Callable, Any, Coroutine

from pydantic import UUID4

from .base import DGLabClient
from ..models import WebSocketMessage

__all__ = ["DGLabLocalClient"]

try:
    WebSocketMessageQueue = asyncio.Queue[WebSocketMessage]
except TypeError:
    WebSocketMessageQueue = asyncio.Queue


class DGLabLocalClient(DGLabClient):
    # noinspection SpellCheckingInspection
    """
        DG-Lab 终端，并不实际发送 WebSocket 消息，而是直接与本地服务端进行通信

        本地服务端指同一线程下的 [`DGLabWSServer`][pydglab_ws.server.server.DGLabWSServer]

        :param client_id: 终端 ID
        :param sender: 用于客户端发送消息的回调函数
        :param queue_setter: 回调函数，用于服务端设置客户端的消息队列
        :param max_queue: 消息队列最大长度
        """

    def __init__(
            self,
            client_id: UUID4,
            sender: Callable[[WebSocketMessage], Coroutine[Any, Any, Any]],
            queue_setter: Callable[[UUID4, WebSocketMessageQueue], Any],
            max_queue: int = 2 ** 5
    ):
        super().__init__()
        self._client_id = client_id
        self._send_callable = sender
        self._message_queue: WebSocketMessageQueue = asyncio.Queue(max_queue)
        queue_setter(client_id, self._message_queue)

    async def _recv(self) -> WebSocketMessage:
        return await self._message_queue.get()

    async def _send(self, message: WebSocketMessage):
        await self._send_callable(message)
