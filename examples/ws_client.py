"""
请先安装 qrcode：``pip install qrcode``
"""
import asyncio
import io

import qrcode
from websockets import ConnectionClosedOK

from pydglab_ws import DGLabWSConnect, StrengthData, FeedbackButton, Channel, StrengthOperationType, RetCode


def print_qrcode(data: str):
    """输出二维码到终端界面"""
    qr = qrcode.QRCode()
    qr.add_data(data)
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())


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

    except ConnectionClosedOK:
        print("Socket 服务端断开连接")


if __name__ == "__main__":
    asyncio.run(main())
