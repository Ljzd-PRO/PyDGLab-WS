import pytest
import pytest_asyncio
from websockets import WebSocketClientProtocol
from websockets.client import connect

from pydglabws.client import DGLabWSClient, DGLabLocalClient
from pydglabws.server import DGLabWSServer


@pytest_asyncio.fixture(name="dg_lab_ws_server", scope="session")
async def dg_lab_ws_server_fixture() -> DGLabWSServer:
    async with DGLabWSServer(
            "localhost",
            5678,
            10
    ) as dg_lab_ws_server:
        yield dg_lab_ws_server


@pytest.fixture(name="dg_lab_local_client", scope="session")
def dg_lab_local_client_fixture(dg_lab_ws_server: DGLabWSServer) -> DGLabLocalClient:
    return dg_lab_ws_server.new_local_client()


@pytest_asyncio.fixture(name="websocket", scope="session")
async def websocket_fixture() -> WebSocketClientProtocol:
    async with connect("ws://localhost:5678") as websocket:
        yield websocket


@pytest.fixture(name="dg_lab_ws_client", scope="session")
def dg_lab_ws_client_fixture(websocket: WebSocketClientProtocol) -> DGLabWSClient:
    return DGLabWSClient(websocket)


def test_dg_lab_ws_server(dg_lab_ws_server: DGLabWSServer):
    assert dg_lab_ws_server.heartbeat_interval == 10


def test_dg_lab_local_client(dg_lab_local_client: DGLabLocalClient):
    assert dg_lab_local_client.client_id is not None
    assert dg_lab_local_client.not_registered is False
    assert dg_lab_local_client.not_bind is True


@pytest.mark.asyncio
async def test_dg_lab_ws_client(dg_lab_ws_client: DGLabWSClient):
    assert dg_lab_ws_client.client_id is None
    assert dg_lab_ws_client.not_registered is True
    assert dg_lab_ws_client.not_bind is True

    await dg_lab_ws_client.register()

    assert dg_lab_ws_client.client_id is not None
    assert dg_lab_ws_client.not_registered is False
    assert dg_lab_ws_client.not_bind is True


@pytest.mark.parametrize(
    "args,expected_generator",
    [
        (
                ("localhost", 8080),
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#wss://localhost:8080/{uuid}"
        ),
        (
                ("153.216.254.135", 5678),
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#wss://153.216.254.135:5678/{uuid}"
        ),
        (
                ("website.cir", 4567),
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#wss://website.cir:4567/{uuid}"
        ),
    ]
)
def test_dg_lab_client_get_qrcode(
        args,
        expected_generator,
        dg_lab_local_client: DGLabLocalClient,
        dg_lab_ws_client: DGLabWSClient
):
    for client in dg_lab_local_client, dg_lab_ws_client:
        assert client.get_qrcode(*args) == expected_generator(client.client_id)
