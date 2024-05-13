from typing import Optional

from websockets import WebSocketClientProtocol

from .base import DGLabClient
from ..models import WebSocketMessage

__all__ = ["DGLabWSClient"]


class DGLabWSClient(DGLabClient):
    """
    DG-Lab WebSocket 终端

    :param websocket: 与 WebSocket 服务端的连接
    """

    def __init__(self, websocket: WebSocketClientProtocol):
        super().__init__()
        self._websocket = websocket

    async def _recv(self) -> WebSocketMessage:
        raw_message = await self._websocket.recv()
        return WebSocketMessage.model_validate_strings(raw_message)

    async def _send(self, message: WebSocketMessage):
        await self._websocket.send(message.model_dump_json(by_alias=True))

    def get_qrcode(self, host: str = None, port: int = None) -> Optional[str]:
        if host is None or port is None:
            host, port = self._websocket.remote_address or (None, None)
        return super().get_qrcode(host, port)
