import json
from uuid import uuid4

from pydglab_ws.enums import MessageType, MessageDataHead, RetCode
from pydglab_ws.models import WebSocketMessage


def test_web_socket_message():
    raw_message = WebSocketMessage(
        type=MessageType.BIND,
        message=MessageDataHead.DG_LAB
    ).model_dump_json(by_alias=True, context={"separators": (",", ":")})
    assert json.loads(raw_message) == {
        "type": "bind",
        "clientId": "",
        "targetId": "",
        "message": "DGLAB"
    }

    client_id = uuid4()
    target_id = uuid4()

    raw_message = WebSocketMessage(
        type=MessageType.MSG,
        client_id=client_id,
        target_id=target_id,
        message=MessageDataHead.TARGET_ID
    ).model_dump_json(by_alias=True, context={"separators": (",", ":")})
    assert json.loads(raw_message) == {
        "type": "msg",
        "clientId": str(client_id),
        "targetId": str(target_id),
        "message": "targetId"
    }

    raw_message = WebSocketMessage(
        type=MessageType.BIND,
        client_id=client_id,
        target_id=target_id,
        message=RetCode.SUCCESS
    ).model_dump_json(by_alias=True, context={"separators": (",", ":")})
    assert json.loads(raw_message) == {
        "type": "bind",
        "clientId": str(client_id),
        "targetId": str(target_id),
        "message": "200"
    }
