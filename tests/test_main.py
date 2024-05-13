import pytest
from websockets import WebSocketClientProtocol

from pydglabws.client import DGLabWSClient
from pydglabws.server import DGLabWSServer
from websockets.client import connect


@pytest.fixture(name="dg_lab_ws_server", scope="session")
@pytest.mark.asyncio
async def dg_lab_ws_server_fixture():
    async with DGLabWSServer(
        "localhost",
        5678,
        10
    ) as dg_lab_ws_server:
        yield dg_lab_ws_server

@pytest.fixture(name="websocket", scope="session")
@pytest.mark.asyncio
async def websocket_fixture():
    async with connect("wss://localhost:5678") as websocket:
        yield websocket

@pytest.fixture(name="dg_lab_ws_client", scope="session")
def dg_lab_ws_client_fixture(websocket: WebSocketClientProtocol):
    return DGLabWSClient(websocket)
