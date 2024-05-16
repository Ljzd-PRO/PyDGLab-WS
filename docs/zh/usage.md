## 📡 搭建服务端

```python3
import asyncio
from pydglab_ws.server import DGLabWSServer


async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        while True:
            print(f"已连接的 WebSocket 客户端（终端/App）：{list(server.uuid_to_ws.keys())}")
            print(f"已连接的本地终端：{list(server.local_client_ids)}")
            print(f"关系绑定：{server.client_id_to_target_id}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
```
更多演示请查看 [`examples/server.py`](examples/server.md)

## 🕹️ 搭建客户端 / 第三方终端

当进入 [`DGLabWSServer`][pydglab_ws.DGLabWSServer] 的异步生成器时，从 WebSocket 服务端获取 `clientId` 的操作会 **自动完成**

```python3
import asyncio
from websockets import ConnectionClosedOK
from pydglab_ws import DGLabWSConnect

def print_qrcode(_: str):
    """输出二维码到终端界面"""
    ...

async def main():
    try:
        async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
            # 获取二维码
            url = client.get_qrcode()
            print("请用 DG-Lab App 扫描二维码以连接")
            print_qrcode(url)

            # 等待绑定
            await client.bind()
            print(f"已与 App {client.target_id} 成功绑定")

            # 从 App 接收数据更新，并进行远控操作
            async for data in client.data_generator():
                print(f"收取到数据：{data}")
    except ConnectionClosedOK:
        print("Socket 服务端断开连接")

if __name__ == "__main__":
    asyncio.run(main())
```
更多演示请查看 [`examples/ws_client.py`](examples/ws_client.md)

## 🕹️ 搭建与第三方终端一体的 WebSocket 服务端

这段代码不仅提供 DG-Lab WebSocket 服务端服务，还生成了一个本地终端可供 App 连接。

!!! tip
    不管是本地终端 [`DGLabLocalClient`][pydglab_ws.DGLabLocalClient]
    还是 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.DGLabWSClient]，
    **包含的主要方法都相同**，因此在该段代码中，终端相关的逻辑与上面的独立的 WebSocket 终端的实现基本相同。
    这种方式，省去了终端连接 WebSocket 服务端的环节，终端与 WebSocket 服务端一体，**网络延迟更低，部署更方便**。

```python3
import asyncio
from pydglab_ws import DGLabWSServer

def print_qrcode(_: str):
    """输出二维码到终端界面"""
    ...

async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        client = server.new_local_client()

        url = client.get_qrcode("ws://192.168.1.161:5678") # (1)
        print("请用 DG-Lab App 扫描二维码以连接")
        print_qrcode(url)

        # 等待绑定
        await client.bind()
        print(f"已与 App {client.target_id} 成功绑定")

        # 从 App 接收数据更新，并进行远控操作
        async for data in client.data_generator():
            print(f"收取到数据：{data}")

if __name__ == "__main__":
    asyncio.run(main())

```

1.  此处的 URI 需要是 DG-Lab 可以连接上的，通常是内网或公网，而不是本地环回地址

更多演示请查看 [`examples/server_with_local_client.py`](examples/server_with_local_client.md)