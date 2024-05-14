"""
这段代码不仅提供 DG-Lab WebSocket 服务端服务，还生成了一个本地终端可供 App 连接。

不管是本地终端 :class:`DGLabLocalClient` 还是 WebSocket 终端 :class:`DGLabWSClient`，包含的主要方法都相同，
因此在该端代码中，终端相关的逻辑与 ``ws_client.py`` WebSocket 终端的实现基本相同。

这种方式，省去了终端连接 WebSocket 服务端的环节，终端与 WebSocket 服务端一体，网络延迟更低，部署更方便。
"""
import asyncio
import io

import qrcode

from pydglab_ws import StrengthData, FeedbackButton, Channel, StrengthOperationType, RetCode, DGLabWSServer


def print_qrcode(data: str):
    """输出二维码到终端界面"""
    qr = qrcode.QRCode()
    qr.add_data(data)
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())


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
        last_strength = None
        async for data in client.data_generator():

            # 接收通道强度数据
            if isinstance(data, StrengthData):
                print(f"从 App 收到通道强度数据更新：{data}")
                last_strength = data

            # 接收 App 反馈按钮
            elif isinstance(data, FeedbackButton):
                print(f"App 触发了反馈按钮：{data.name}")

                if data == FeedbackButton.A1:
                    # 设置强度到 A 通道上限
                    print("对方按下了 A 通道圆圈按钮，加大力度")
                    if last_strength:
                        await client.set_strength(
                            Channel.A,
                            StrengthOperationType.SET_TO,
                            last_strength.a_limit
                        )

            # 接收 心跳 / App 断开通知
            elif data == RetCode.CLIENT_DISCONNECTED:
                print("App 已断开连接，你可以尝试重新扫码进行连接绑定")


if __name__ == "__main__":
    asyncio.run(main())
