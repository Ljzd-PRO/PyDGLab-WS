import ipaddress
from ssl import SSLSocket
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

    async def __aenter__(self) -> "DGLabWSClient":
        await self.register()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _recv(self) -> WebSocketMessage:
        raw_message = await self._websocket.recv()
        return WebSocketMessage.model_validate_json(raw_message)

    async def _send(self, message: WebSocketMessage):
        await self._websocket.send(message.model_dump_json(by_alias=True))

    def get_qrcode(self, uri: str = None) -> Optional[str]:
        if uri is None and (remote_address := self._websocket.remote_address):
            host, port = remote_address
            try:
                is_v6 = ipaddress.ip_address(host).version == 6
            except ValueError:
                pass
            else:
                host = f"[{host}]" if is_v6 else host
            socket = self._websocket.transport.get_extra_info("socket")
            secure = isinstance(socket, SSLSocket)
            uri = f"{'wss' if secure else 'ws'}://{host}:{port}"
        return super().get_qrcode(uri)

    @property
    def websocket(self) -> WebSocketClientProtocol:
        """
        终端的 WebSocket 连接对象

        可用来获取连接延迟等信息，但不建议调用它的 recv, send 等方法，可能会影响
        [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient] 的各项功能
        """
        return self._websocket
