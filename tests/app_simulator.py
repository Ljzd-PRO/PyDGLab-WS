from typing import Optional

from pydantic import UUID4
from websockets import WebSocketClientProtocol

from pydglab_ws.enums import MessageType, MessageDataHead, FeedbackButton, RetCode
from pydglab_ws.models import WebSocketMessage, StrengthData


class DGLabAppSimulator:
    """
    用于测试时模拟 DG-Lab App
    """

    def __init__(self, websocket: WebSocketClientProtocol):
        self.websocket = websocket
        self.target_id: Optional[UUID4] = None
        self.client_id: Optional[UUID4] = None

    async def _send(self, message: WebSocketMessage):
        await self.websocket.send(message.model_dump_json(by_alias=True))

    async def _recv(self) -> WebSocketMessage:
        raw_message = await self.websocket.recv()
        return WebSocketMessage.model_validate_json(raw_message)

    async def _recv_owned(self) -> WebSocketMessage:
        while True:
            message = await self._recv()
            if message.target_id == self.target_id:
                return message

    async def register(self):
        message = await self._recv()
        if message.type == MessageType.BIND and message.message == MessageDataHead.TARGET_ID:
            self.target_id = message.client_id

    async def bind(self, client_id: UUID4):
        await self._send(
            WebSocketMessage(
                type=MessageType.BIND,
                client_id=client_id,
                target_id=self.target_id,
                message=MessageDataHead.DG_LAB
            )
        )
        self.client_id = client_id

    async def send_strength(self, data: StrengthData):
        await self._send(
            WebSocketMessage(
                type=MessageType.MSG,
                client_id=self.client_id,
                target_id=self.target_id,
                message=f"{MessageDataHead.STRENGTH.value}-{data.a}+{data.b}+{data.a_limit}+{data.b_limit}"
            )
        )

    async def send_feedback(self, data: FeedbackButton):
        await self._send(
            WebSocketMessage(
                type=MessageType.MSG,
                client_id=self.client_id,
                target_id=self.target_id,
                message=f"{MessageDataHead.FEEDBACK.value}-{data.value}"
            )
        )

    async def recv_client_data(self) -> WebSocketMessage:
        while True:
            message = await self._recv_owned()
            if message.type == MessageType.MSG:
                return message

    async def recv_heartbeat(self) -> RetCode:
        while True:
            message = await self._recv()
            # 注意此处 clientId 为心跳包接收方 ID，targetId 为绑定方
            if message.type == MessageType.HEARTBEAT and message.client_id == self.target_id:
                return message.message

    async def recv_disconnect(self) -> RetCode:
        while True:
            message = await self._recv_owned()
            if message.type == MessageType.BREAK:
                return message.message
