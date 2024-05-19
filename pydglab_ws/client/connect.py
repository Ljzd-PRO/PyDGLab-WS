from websockets.client import connect as ws_connect

from .ws import DGLabWSClient

__all__ = ["DGLabWSConnect"]


class DGLabWSConnect:
    """
    DG-Lab 终端的 WebSocket 连接管理器

    示例：
    ```python3
    async with DGLabWSConnect("ws://localhost:5678") as client:
        await client.bind()
        print("成功绑定")
    ```

    :param uri: WebSocket 服务端 Uri
    :param register_timeout: 终端注册（获取 ``clientId``）超时时间
    :param kwargs: :class:`websockets.client.connect` 的其他参数
    :raise asyncio.Timeout: 终端注册（获取 ``clientId``）超时
    """

    def __init__(self, uri: str, register_timeout: float = None, **kwargs):
        self._connect = ws_connect(uri=uri, **kwargs)
        self._register_timeout = register_timeout

    async def __aenter__(self) -> DGLabWSClient:
        websocket = await self._connect.__aenter__()
        dg_lab_ws_client = DGLabWSClient(websocket, self._register_timeout)
        await dg_lab_ws_client.__aenter__()
        return dg_lab_ws_client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._connect.__aexit__(exc_type, exc_val, exc_tb)
