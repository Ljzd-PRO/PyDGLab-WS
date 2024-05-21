# 终端基础类的属性和方法

[`DGLabClient`][pydglab_ws.client.base.DGLabClient] 是终端基类，包含
本地终端 [`DGLabLocalClient`][pydglab_ws.client.local.DGLabLocalClient]
和 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient]
共有的一些属性和方法

## 获取自身的各项信息

可获取终端自身的 ID、绑定的 App 的 ID、是否已从 WebSocket 服务端注册，即获取 ID（`clientId`）以及是否已和 DG-Lab App 绑定。

!!! info
    ID 属性 [`client_id`][pydglab_ws.client.base.DGLabClient.client_id]
    和 [`target_id`][pydglab_ws.client.base.DGLabClient.target_id]
    可能为返回空，原因是终端未注册或还没有与 App 绑定。

### 可用属性

::: pydglab_ws.client.base.DGLabClient.client_id
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.client.base.DGLabClient.target_id
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.client.base.DGLabClient.not_registered
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

::: pydglab_ws.client.base.DGLabClient.not_bind
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        await client.bind()
        print(f"终端 {client.client_id} 已与 App {client.target_id} 成功绑定")
        ...
```

- - -

## 注册（获取终端 ID）

终端连接至 WebSocket 服务端后，需要先从服务端获取终端 ID（`clientId`），此处称为注册，
不过一般情况下 PyDGLab-WS 会在异步上下文管理中完成该步骤，即以下用法：

- 使用连接器 [`DGLabWSConnect`][pydglab_ws.client.connect.DGLabWSConnect]
  创建 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient]
- 手动创建 WebSocket 终端 [`DGLabWSClient`][pydglab_ws.client.ws.DGLabWSClient] 对象，
  并在异步上下文管理（即 `async with` 中使用）
- 从 WebSocket 服务端 [`DGLabWSServer`][pydglab_ws.server.server.DGLabWSServer]
  创建本地终端 [`DGLabLocalClient`][pydglab_ws.client.local.DGLabLocalClient]

### 可用方法

::: pydglab_ws.client.base.DGLabClient.register
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

- - -

## 获取二维码，绑定 DG-Lab App

从 WebSocket 服务端获取终端 ID（`clientId`）后，即可生成终端二维码，
DG-Lab App 进入 Socket 被控界面后，扫码二维码即可绑定

!!! info
    注意此处生成的二维码 **仅仅是二维码内容/数据**，二维码图像需要自行从返回的数据生成

!!! info
    App 断开连接后，重新连接至服务端时 `targetId` 可能发生变化，因此最好是再调用一次
    [`rebind`][pydglab_ws.client.base.DGLabClient.rebind] 方法，重新等待绑定并更新 `targetId`

!!! warning
    生成二维码后，需要调用绑定方法来等待 App 绑定，此时该异步事件会阻塞直到绑定完成

### 可用方法

::: pydglab_ws.client.base.DGLabClient.get_qrcode
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.client.base.DGLabClient.bind
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.client.base.DGLabClient.rebind
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect

def print_qrcode(_: str):
    """输出二维码到终端界面"""
    ...

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        # 获取二维码
        url = client.get_qrcode()
        print("请用 DG-Lab App 扫描二维码以连接")
        print_qrcode(url)

        # 等待绑定
        await client.bind()
        print(f"已与 App {client.target_id} 成功绑定")
        ...
```

- - -

## 获取 App 数据更新和服务端通知

可获取如下数据：

- 通道强度数据
- App 触发的反馈按钮
- App 返回的错误码
- 服务端发送的心跳
- 服务端发送的 App 断开连接通知

!!! info
    [`data_generator`][pydglab_ws.client.base.DGLabClient.data_generator]
    会不断从队列中读取消息并解析，队列为空时则会阻塞该异步事件，
    如果需要退出，可使用 `break`

!!! info
    App 断开连接后，重新连接至服务端时 `targetId` 可能发生变化，因此最好是再调用一次
    [`rebind`][pydglab_ws.client.base.DGLabClient.rebind] 方法，重新等待绑定并更新 `targetId`

!!! danger
    **不能并发地读取** 数据更新，因为消息一旦被读出，就会从队列中移除。
    另外 [`data_generator`][pydglab_ws.client.base.DGLabClient.data_generator]
    在解析消息时，如果读出的消息不符合筛选条件，将会被丢弃，直到读到符合条件的消息

### 可用方法

::: pydglab_ws.client.base.DGLabClient.recv_data
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

::: pydglab_ws.client.base.DGLabClient.data_generator
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect, StrengthData, FeedbackButton, RetCode

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        ... # 完成了绑定
        async for data in client.data_generator():
            # 接收通道强度数据
            if isinstance(data, StrengthData):
                print(f"从 App 收到通道强度数据更新：{data}")

            # 接收 App 反馈按钮
            elif isinstance(data, FeedbackButton):
                print(f"App 触发了反馈按钮：{data.name}")

            # 接收 心跳 / App 断开通知
            elif data == RetCode.CLIENT_DISCONNECTED:
                print("App 已断开连接，你可以尝试重新扫码进行连接绑定")
```

- - -

## 设置通道强度

可设置郊狼 A 通道、B 通道 的强度，并有几个变化模式可选。

### 可用方法

::: pydglab_ws.client.base.DGLabClient.set_strength
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect, Channel, StrengthOperationType

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        ... # 完成了绑定
        await client.set_strength(
            Channel.A,
            StrengthOperationType.INCREASE,
            10
        )   # A 通道 增加 10 强度
        ...
```

- - -

## 下发波形数据

可向 App 下发波形操作，参数中的 `*pulses` 是位置参数，可传入多个
[`PulseOperation`][pydglab_ws.typing.PulseOperation]

!!! question
    [`PulseOperation`][pydglab_ws.typing.PulseOperation]
    **波形操作** 数据是由一个波形 **频率** 操作数据 [`WaveformFrequencyOperation`][pydglab_ws.typing.WaveformFrequencyOperation]
    和一个波形 **强度** 操作数据 [`WaveformStrengthOperation`][pydglab_ws.typing.WaveformStrengthOperation]
    组合成的元组。波形 **频率** 操作数据和波形 **强度** 操作数据 则都是由 **4** 个 [`int`][int] 整数组成的元组，代表了目标数值

### 可用方法

::: pydglab_ws.client.base.DGLabClient.add_pulses
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect, Channel, StrengthOperationType

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        ... # 完成了绑定
        await client.add_pulses(
            Channel.A,
            ((10, 10, 20, 30), (0, 5, 10, 50)), # 波形频率4条 {10,10,20,30}，波形强度4条 {0,5,10,50}
            ((10, 10, 20, 30), (0, 5, 10, 50)), # 同上
            ((10, 10, 20, 30), (0, 5, 10, 50))  # 同上
        )   # 向 A 通道波形队列增加了持续 300 毫秒的操作
        ...
```

- - -

## 清空波形队列

App 中的波形执行是基于波形队列，遵循先进先出的原则，并且队列可以缓存 500 条波形数据 (50s 的数据)。

当波形队列中还有尚未执行完的波形数据时，第三方终端希望立刻执行新的波形数据，则需要先将对应通道的波形队列执行清空操作后，再发送波形数据，
即可实现立刻执行新的波形数据的需求。

> 来自DG-LAB [官方文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/socket/README.md) 解释

### 可用方法

::: pydglab_ws.client.base.DGLabClient.clear_pulses
    options:
        heading_level: 4
        show_root_heading: true
        show_root_full_path: false
        show_source: false

### 示例

```python3
from pydglab_ws import DGLabWSConnect, Channel, StrengthOperationType

async def main():
    async with DGLabWSConnect("ws://192.168.1.161:5678") as client:
        ... # 完成了绑定
        await client.clear_pulses(Channel.A)    # 清空 A 通道波形队列
        ...
```