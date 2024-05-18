## 搭建服务端

使用 [`DGLabWSServer`][pydglab_ws.server.DGLabWSServer]。

### 参数说明

::: pydglab_ws.server.DGLabWSServer
    options:
        show_root_heading: true
        show_root_full_path: false
        show_source: false
        heading_level: 4
        show_docstring_description: false
        members: false

### 示例

```python3
import asyncio
from pydglab_ws.server import DGLabWSServer

async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60):
        await asyncio.Future()
```

- - -

## 获取连接到服务端的 终端/App 信息

可获取到 终端/App 的 ID 以及其对应的WebSocket 连接对象和相互的绑定关系。通过 WebSocket 连接对象，可以获取连接延迟等信息。

### 可用属性

::: pydglab_ws.server.DGLabWSServer.client_id_to_target_id
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.server.DGLabWSServer.target_id_to_client_id
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.server.DGLabWSServer.uuid_to_ws
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.server.DGLabWSServer.local_client_ids
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

### 示例

```python3
from pydglab_ws.server import DGLabWSServer

async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        ... # 设备连接后
        for target_id in server.target_id_to_client_id.keys():
            websocket = server.uuid_to_ws[target_id]
            print(f"App {target_id} 延迟为 {websocket.latency} 秒")
        print(f"目前已连接 {len(server.local_client_ids)} 个 本地终端")
```

- - -

## 添加回调函数，在连接建立/断开或收到指定类型的消息后调用

通过 [`DGLabWSServer`][pydglab_ws.server.DGLabWSServer] 的几个方法添加和删除回调函数。

### 可用方法

::: pydglab_ws.server.DGLabWSServer.add_receive_callback
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.server.DGLabWSServer.remove_receive_callback
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.server.DGLabWSServer.add_connection_callback
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.server.DGLabWSServer.remove_connection_callback
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

- - -

## 创建本地终端

查看 [与本地终端一体的服务端](client/local.md)