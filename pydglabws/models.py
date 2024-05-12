from typing import Optional

from pydantic import BaseModel, UUID4, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel

from pydglabws.enums import MessageType


class WebSocketMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    type: MessageType
    client_id: Optional[UUID4]
    target_id: Optional[UUID4]
    message: str

    @field_serializer("client_id", "target_id", when_used="json")
    def serialize_id(self, value: Optional[UUID4]):
        return value or ""


class StrengthData(BaseModel):
    a: int
    b: int
    a_limit: int
    b_limit: int
