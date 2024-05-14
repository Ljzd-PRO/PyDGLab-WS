from typing import Tuple, List, Callable, Coroutine

import pytest
import pytest_asyncio
from websockets import WebSocketClientProtocol
from websockets.client import connect

from pydglabws.client import DGLabWSClient, DGLabLocalClient, DGLabClient
from pydglabws.enums import FeedbackButton
from pydglabws.models import StrengthData
from pydglabws.server import DGLabWSServer
from tests.app_simulator import DGLabAppSimulator

WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 5678
WEBSOCKET_URI = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
HEARTBEAT_INTERVAL: float = 10

ClientAppPair = Tuple[
    DGLabClient,
    DGLabAppSimulator
]


@pytest_asyncio.fixture(name="dg_lab_ws_server", scope="session")
async def dg_lab_ws_server_fixture() -> DGLabWSServer:
    async with DGLabWSServer(
            WEBSOCKET_HOST,
            WEBSOCKET_PORT,
            HEARTBEAT_INTERVAL
    ) as dg_lab_ws_server:
        yield dg_lab_ws_server


@pytest.fixture(name="dg_lab_local_client", scope="session")
def dg_lab_local_client_fixture(dg_lab_ws_server: DGLabWSServer) -> DGLabLocalClient:
    return dg_lab_ws_server.new_local_client()


@pytest_asyncio.fixture(name="client_websocket", scope="session")
async def client_websocket_fixture() -> WebSocketClientProtocol:
    async with connect(WEBSOCKET_URI) as client_websocket:
        yield client_websocket


@pytest.fixture(name="dg_lab_ws_client", scope="session")
def dg_lab_ws_client_fixture(client_websocket: WebSocketClientProtocol) -> DGLabWSClient:
    return DGLabWSClient(client_websocket)


@pytest_asyncio.fixture(name="app_simulator_for_local", scope="session")
async def app_simulator_for_local_fixture() -> DGLabAppSimulator:
    async with connect(WEBSOCKET_URI) as app_ws:
        yield DGLabAppSimulator(app_ws)


@pytest_asyncio.fixture(name="app_simulator_for_ws", scope="session")
async def app_simulator_for_ws_fixture() -> DGLabAppSimulator:
    async with connect(WEBSOCKET_URI) as app_ws:
        yield DGLabAppSimulator(app_ws)


@pytest_asyncio.fixture(name="client_app_pairs", scope="session")
def client_app_pairs_fixture(
        dg_lab_local_client: DGLabLocalClient,
        dg_lab_ws_client: DGLabWSClient,
        app_simulator_for_local: DGLabAppSimulator,
        app_simulator_for_ws: DGLabAppSimulator,
) -> List[ClientAppPair]:
    return [
        (dg_lab_local_client, app_simulator_for_local),
        (dg_lab_ws_client, app_simulator_for_ws)
    ]


@pytest.mark.parametrize(
    "interval,expected",
    [
        (HEARTBEAT_INTERVAL + 1, HEARTBEAT_INTERVAL + 1),
        (None, HEARTBEAT_INTERVAL)
    ]
)
def test_dg_lab_ws_server(
        interval: float,
        expected,
        dg_lab_ws_server: DGLabWSServer
):
    assert dg_lab_ws_server.heartbeat_enabled is True
    assert dg_lab_ws_server.heartbeat_interval == HEARTBEAT_INTERVAL
    dg_lab_ws_server.heartbeat_interval = interval
    assert dg_lab_ws_server.heartbeat_interval == expected
    dg_lab_ws_server.heartbeat_interval = HEARTBEAT_INTERVAL


@pytest.mark.asyncio
async def test_dg_lab_local_register(
        dg_lab_ws_server: DGLabWSServer,
        dg_lab_local_client: DGLabLocalClient
):
    assert dg_lab_local_client.client_id is not None
    assert dg_lab_local_client.not_registered is False
    assert dg_lab_local_client.not_bind is True

    # Local client will register when initializing
    await dg_lab_local_client.register()

    assert dg_lab_local_client.client_id in dg_lab_ws_server.local_client_ids
    assert dg_lab_local_client.client_id is not None
    assert dg_lab_local_client.not_registered is False
    assert dg_lab_local_client.not_bind is True


@pytest.mark.asyncio
async def test_dg_lab_ws_register(
        dg_lab_ws_server: DGLabWSServer,
        dg_lab_ws_client: DGLabWSClient
):
    assert dg_lab_ws_client.client_id is None
    assert dg_lab_ws_client.not_registered is True
    assert dg_lab_ws_client.not_bind is True

    await dg_lab_ws_client.register()

    assert dg_lab_ws_client.client_id in dg_lab_ws_server.ws_client_ids
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


@pytest.mark.asyncio
@pytest.mark.order(
    after=[
        "test_dg_lab_ws_register",
        "test_dg_lab_local_register"
    ]
)  # After registered
async def test_dg_lab_client_bind(
        client_app_pairs: List[ClientAppPair],
        dg_lab_ws_server: DGLabWSServer
):
    assert not dg_lab_ws_server.client_id_to_target_id
    assert not dg_lab_ws_server.target_id_to_client_id

    for (client, app), get_bind in zip(
            client_app_pairs,
            [
                lambda x: x.bind(),
                lambda x: x.ensure_bind()
            ]
    ):  # type: (DGLabClient, DGLabAppSimulator), Callable[[DGLabClient], Coroutine]
        await app.register()
        await app.bind(client.client_id)
        await get_bind(client)

        assert dg_lab_ws_server.client_id_to_target_id.get(client.client_id) == app.target_id
        assert dg_lab_ws_server.target_id_to_client_id.get(app.target_id) == client.client_id
        assert client.target_id == app.target_id
        assert client.not_bind is not True


@pytest.mark.asyncio
@pytest.mark.order(after="test_dg_lab_client_bind")  # After bind
@pytest.mark.parametrize(
    "strength_data",
    [
        StrengthData(a=0, b=0, a_limit=0, b_limit=0),
        StrengthData(a=200, b=0, a_limit=0, b_limit=0),
        StrengthData(a=0, b=200, a_limit=0, b_limit=0),
        StrengthData(a=0, b=0, a_limit=200, b_limit=0),
        StrengthData(a=0, b=0, a_limit=0, b_limit=200),
    ]
)
async def test_dg_lab_client_recv_strength(
        strength_data: StrengthData,
        client_app_pairs: List[ClientAppPair],
        app_simulator_for_ws: DGLabAppSimulator,
):
    for client, app in client_app_pairs:
        await app.send_strength(strength_data)
        assert await client.recv_app_data() == strength_data


@pytest.mark.asyncio
@pytest.mark.order(after="test_dg_lab_client_bind")  # After bind
@pytest.mark.parametrize(
    "feedback_button",
    [
        FeedbackButton(0),
        FeedbackButton(4),
        FeedbackButton(5),
        FeedbackButton(9),
    ]
)
async def test_dg_lab_client_recv_feedback(
        feedback_button: FeedbackButton,
        client_app_pairs: List[ClientAppPair],
        app_simulator_for_ws: DGLabAppSimulator,
):
    for client, app in client_app_pairs:
        await app.send_feedback(feedback_button)
        assert await client.recv_app_data() == feedback_button
