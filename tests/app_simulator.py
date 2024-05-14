from typing import Optional

from pydantic import UUID4
from websockets import WebSocketClientProtocol

from pydglabws.enums import MessageType, MessageDataHead
from pydglabws.models import WebSocketMessage


class DGLabAppSimulator:
    """
    用于测试时模拟 DG-Lab App
    """

    def __init__(self, websocket: WebSocketClientProtocol):
        self._websocket = websocket
        self.target_id: Optional[UUID4] = None
        self.client_id: Optional[UUID4] = None

    async def _send(self, message: WebSocketMessage):
        await self._websocket.send(message.model_dump_json(by_alias=True))

    async def _recv(self) -> WebSocketMessage:
        raw_message = await self._websocket.recv()
        return WebSocketMessage.model_validate_json(raw_message)

    async def _recv_owned(self) -> WebSocketMessage:
        message = await self._recv()
        if message.client_id == self.target_id:
            return message

    async def register(self):
        message = await self._recv()
        if message.type == MessageType.BIND and message.message == MessageDataHead.TARGET_ID.value:
            self.target_id = message.client_id

    async def bind(self, client_id: UUID4):
        await self._send(
            WebSocketMessage(
                type=MessageType.BIND,
                client_id=client_id,
                target_id=self.target_id,
                message=MessageDataHead.DG_LAB.value
            )
        )
        self.client_id = client_id

    async def recv_client_data(self) -> WebSocketMessage:
        while True:
            message = await self._recv_owned()
            if message.type == MessageType.MSG:
                return message
