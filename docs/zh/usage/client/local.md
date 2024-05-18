## 创建本地终端

不管是本地终端 [`DGLabLocalClient`][pydglab_ws.DGLabLocalClient]
还是 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.DGLabWSClient]，
**包含的主要方法都相同**，本地终端省去了终端连接 WebSocket 服务端的环节，
与 WebSocket 服务端一体，**网络延迟更低，部署更方便**。

### 可用方法

::: pydglab_ws.DGLabWSServer.new_local_client
    options:
        heading_level: 4
        show_root_heading: true
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSServer

async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        client = server.new_local_client()
        # 获取二维码
        _ = client.get_qrcode("ws://192.168.1.161:5678") # (1)
        ...
        # 等待绑定
        await client.bind()
        ...
```

1.  此处的 URI 为服务端 WebSocket URI，需要是 DG-Lab 可以连接上的，通常是内网或公网，而不是本地环回地址
