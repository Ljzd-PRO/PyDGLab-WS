"""
这段代码仅提供 DG-Lab WebSocket 服务端服务
"""
import asyncio

from pydglab_ws.server import DGLabWSServer


async def main():
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        while True:
            print(f"已连接的 WebSocket 客户端（终端/App）：{list(server.ws_client_ids)}")
            print(f"已连接的本地终端：{list(server.local_client_ids)}")
            print(f"关系绑定：{server.client_id_to_target_id}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
