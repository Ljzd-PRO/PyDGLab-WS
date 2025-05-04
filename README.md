<h1 align="center">
  PyDGLab-WS
</h1>

<p align="center">
  一个用于创建郊狼 3.0 DG-Lab App Socket 控制终端和服务端的 Python 库
</p>

<p align="center">
  <a href="https://pydglab-ws.readthedocs.io">📖 完整文档</a>
</p>

<p align="center">
  <a href="https://www.codefactor.io/repository/github/ljzd-pro/pydglab-ws">
    <img src="https://www.codefactor.io/repository/github/ljzd-pro/pydglab-ws/badge" alt="CodeFactor" />
  </a>

  <a href="https://codecov.io/gh/Ljzd-PRO/PyDGLab-WS" target="_blank">
      <img src="https://codecov.io/gh/Ljzd-PRO/PyDGLab-WS/branch/master/graph/badge.svg?token=VTr0LB1yWF" alt="codecov"/>
  </a>

  <a href="https://github.com/Ljzd-PRO/PyDGLab-WS/actions/workflows/codecov.yml" target="_blank">
    <img alt="Test Result" src="https://img.shields.io/github/actions/workflow/status/Ljzd-PRO/PyDGLab-WS/codecov.yml">
  </a>

  <a href='https://pydglab-ws.readthedocs.io/'>
    <img src='https://readthedocs.org/projects/pydglab-ws/badge/?version=latest' alt='Documentation Status' />
  </a>

  <a href="https://github.com/Ljzd-PRO/PyDGLab-WS/activity">
    <img src="https://img.shields.io/github/last-commit/Ljzd-PRO/PyDGLab-WS/master" alt="Last Commit"/>
  </a>

  <a href="./LICENSE">
    <img src="https://img.shields.io/github/license/Ljzd-PRO/PyDGLab-WS" alt="BSD 3-Clause"/>
  </a>

  <a href="https://pypi.org/project/pydglab-ws" target="_blank">
    <img src="https://img.shields.io/github/v/release/Ljzd-PRO/PyDGLab-WS?logo=python" alt="Version">
  </a>
</p>

## 💡 特性

- 通过该库可开发 Python 程序，接入 DG-Lab App
- 完全使用 asyncio 异步，并发执行各项操作
- 可部署第三方终端与 Socket 服务一体的服务端，降低部署复杂度和延迟
- 使用异步生成器、上下文管理器等，结合语言特性
- 通过 Pydantic, 枚举 管理消息结构和常量，便于开发

### 🔧 DG-Lab App 的 Socket 被控功能支持的操作

- 获取 A, B 通道强度 以及 通道强度上限 的数据更新
- 对 A, B 通道强度进行操作，支持增加、减少、设定到指定值
- 向 App 发送持续一段时间的波形操作数据
- 清空 App 波形操作队列
- 获取 App 按下反馈按钮的通知

## 🚀 快速开始

📖 更多用法和完整 API 请查看文档：https://pydglab-ws.readthedocs.io

> [!Note]
> 注意，您可能需要先大致了解一下第三方终端通过 WebSocket 连接控制 DG-Lab App 的基本流程和原理 \
> 官方文档：https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/socket/README.md

### 🔨 安装

```bash
pip3 install pydglab-ws
```

### 📡 搭建服务端

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

更多演示请查看 [`examples/server.py`](examples/server.py)

### 🕹️ 搭建客户端 / 第三方终端

当进入 `DGLabWSServer` 的异步生成器时，从 WebSocket 服务端获取 `clientId` 的操作会 **自动完成**

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

更多演示请查看 [`examples/ws_client.py`](examples/ws_client.py)

### 🕹️ 搭建与第三方终端一体的 WebSocket 服务端

这段代码不仅提供 DG-Lab WebSocket 服务端服务，还生成了一个本地终端可供 App 连接。

> [!Tip]
> 不管是本地终端 `DGLabLocalClient` 还是 WebSocket 终端 `DGLabWSClient`，**包含的主要方法都相同** \
> 因此在该段代码中，终端相关的逻辑与上面的独立的 WebSocket 终端的实现基本相同。 \
> 这种方式，省去了终端连接 WebSocket 服务端的环节，终端与 WebSocket 服务端一体，**网络延迟更低，部署更方便**。

```python3
import asyncio
from pydglab_ws import DGLabWSServer


def print_qrcode(_: str):
    """输出二维码到终端界面"""
    ...


async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        client = server.new_local_client()

        url = client.get_qrcode("ws://192.168.1.161:5678")
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

更多演示请查看 [`examples/local_client_with_server.py`](examples/server_with_local_client.py)

## 📌 更多

如果您在开发过程中，发现要实现一些常用的功能时并不方便，或者您有什么建议能够使开发更简单快捷，欢迎在 Issues 中提出~

### 相关项目

下列为采用了 PyDGLab-WS 的一些项目：
- [Ljzd-PRO/nonebot-plugin-dg-lab-play](https://github.com/Ljzd-PRO/nonebot-plugin-dg-lab-play)：nonebot2 机器人插件 - ⚡在群里和大家一起玩郊狼吧！⚡
- [Ljzd-PRO/HL2-DGLabInjuryExperienceMod](https://github.com/Ljzd-PRO/HL2-DGLabInjuryExperienceMod)：半条命 2 模组 - 用郊狼⚡模拟一下自己和敌人的受伤痛觉~
  > 其中的 PyDGLab-WS-Connector

如果你的项目也应用了 PyDGLab-WS，欢迎在 Issues 页面分享。

### 🔗 链接

- PyPI: 🔗[pydglab-ws](https://pypi.org/project/pydglab-ws/)

### 📐 代码覆盖率

![codecov.io](https://codecov.io/github/Ljzd-PRO/PyDGLab-WS/graphs/tree.svg?token=VTr0LB1yWF)

### 许可证

PyDGLab-WS 使用 BSD 3-Clause 许可证.

Copyright © 2024 by Ljzd-PRO.
