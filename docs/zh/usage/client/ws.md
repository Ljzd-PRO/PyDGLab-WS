## 创建 WebSocket 第三方终端

有两种方法：

1. 【推荐】使用连接器 [`DGLabWSConnect`][pydglab_ws.client.connect.DGLabWSConnect] 创建 WebSocket 终端
  [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient]
2. 手动创建 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient] 对象，
  并在异步上下文管理（即 `async with` 中使用）

### 参数说明

::: pydglab_ws.client.connect.DGLabWSConnect
    options:
        show_root_heading: true
        show_root_full_path: false
        show_source: false
        heading_level: 4
        show_docstring_description: false
        members: false

::: pydglab_ws.client.ws.DGLabWSClient
    options:
        show_root_heading: true
        show_root_full_path: false
        show_source: false
        heading_level: 4
        show_docstring_description: false
        members: false

### 示例

#### 方法 1

```python3
from pydglab_ws import DGLabWSConnect

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        # 获取二维码
        _ = client.get_qrcode()
        ...
        # 等待绑定
        await client.bind()
        print(f"已与 App {client.target_id} 成功绑定")
        ...
```

#### 方法 2

```python3
from websockets.client import connect
from pydglab_ws import DGLabWSClient

async def main():
    async with connect("ws://192.168.1.161:5678") as websocket:
        async with DGLabWSClient(websocket) as client:
            # 获取二维码
            _ = client.get_qrcode()
            ...
            # 等待绑定
            await client.bind()
            print(f"已与 App {client.target_id} 成功绑定")
            ...
```

- - -

## 获取终端的 WebSocket 连接对象

### 可用属性

::: pydglab_ws.client.ws.DGLabWSClient.websocket
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        print(f"与服务端的延迟为 {client.websocket.latency} 秒")
        ...
```