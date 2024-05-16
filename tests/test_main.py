import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Tuple, List, Callable, Coroutine, Literal

import pytest
import pytest_asyncio
from websockets import WebSocketClientProtocol
from websockets.client import connect

from pydglab_ws.client import DGLabWSClient, DGLabLocalClient, DGLabClient, DGLabWSConnect
from pydglab_ws.enums import FeedbackButton, Channel, MessageType, StrengthOperationType, RetCode
from pydglab_ws.models import StrengthData
from pydglab_ws.server import DGLabWSServer
from tests.app_simulator import DGLabAppSimulator

WEBSOCKET_HOST = "127.0.0.1"
WEBSOCKET_PORT = 5678
WEBSOCKET_URI = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
HEARTBEAT_INTERVAL: float = 1
HEARTBEAT_TEST_TIMES: int = 3
HEARTBEAT_TEST_EXTRA_WAIT: float = 1

ClientAppPair = Tuple[
    DGLabClient,
    DGLabAppSimulator
]


@dataclass
class CallbackData:
    values = []


@asynccontextmanager
async def locks_context_manager(*locks: asyncio.Lock):
    for lock in locks:
        await lock.acquire()
    yield
    for lock in locks:
        lock.release()


@pytest.fixture(name="global_lock", scope="session")
def global_lock_fixture() -> asyncio.Lock:
    return asyncio.Lock()


@pytest_asyncio.fixture(name="local_register_lock", scope="session")
async def local_register_lock_fixture() -> asyncio.Lock:
    # 先锁上，只有执行注册的测试不需要获得锁，以实现先注册
    lock = asyncio.Lock()
    await lock.acquire()
    return lock


@pytest_asyncio.fixture(name="ws_register_lock", scope="session")
async def ws_register_lock_fixture() -> asyncio.Lock:
    # 先锁上，只有执行注册的测试不需要获得锁，以实现先注册
    lock = asyncio.Lock()
    await lock.acquire()
    return lock


@pytest_asyncio.fixture(name="local_bind_lock", scope="session")
async def local_bind_lock_fixture(local_register_lock: asyncio.Lock) -> asyncio.Lock:
    # 先锁上，只有执行绑定的测试不需要获得锁，以实现先绑定
    await local_register_lock.acquire()
    return local_register_lock


@pytest_asyncio.fixture(name="ws_bind_lock", scope="session")
async def ws_bind_lock_fixture(ws_register_lock: asyncio.Lock) -> asyncio.Lock:
    # 先锁上，只有执行绑定的测试不需要获得锁，以实现先绑定
    await ws_register_lock.acquire()
    return ws_register_lock


@pytest.fixture(name="callback_data", scope="session")
def callback_data_fixture():
    return CallbackData()


@pytest_asyncio.fixture(name="dg_lab_ws_server", scope="session")
async def dg_lab_ws_server_fixture(callback_data: CallbackData) -> DGLabWSServer:
    async with DGLabWSServer(
            WEBSOCKET_HOST,
            WEBSOCKET_PORT,
            HEARTBEAT_INTERVAL
    ) as dg_lab_ws_server:
        def remove_receive_callback():
            pass

        def remove_connection_callback():
            pass

        async def async_callback(x, y):
            callback_data.values.append((x, y))

        # Test add then remove
        assert dg_lab_ws_server.add_receive_callback(
            MessageType.MSG,
            remove_receive_callback
        ) is True
        assert dg_lab_ws_server.add_connection_callback(
            "new_connect",
            remove_connection_callback
        ) is True
        assert dg_lab_ws_server.remove_receive_callback(
            MessageType.MSG,
            remove_receive_callback
        ) is True
        assert dg_lab_ws_server.remove_connection_callback(
            "new_connect",
            remove_connection_callback
        ) is True

        # Test failed
        assert dg_lab_ws_server.add_receive_callback(
            MessageType.HEARTBEAT,
            remove_receive_callback
        ) is False
        assert dg_lab_ws_server.remove_receive_callback(
            MessageType.MSG,
            remove_receive_callback
        ) is False
        assert dg_lab_ws_server.remove_connection_callback(
            "new_connect",
            remove_connection_callback
        ) is False

        # Test add and run
        assert dg_lab_ws_server.add_receive_callback(
            MessageType.MSG,
            lambda x, y: callback_data.values.append((x, y))
        ) is True
        assert dg_lab_ws_server.add_receive_callback(
            MessageType.BIND,
            async_callback
        ) is True
        assert dg_lab_ws_server.add_connection_callback(
            "new_connect",
            lambda x, y: callback_data.values.append((x, y))
        ) is True
        assert dg_lab_ws_server.add_connection_callback(
            "disconnect",
            async_callback
        ) is True

        yield dg_lab_ws_server


@pytest.fixture(name="dg_lab_local_client", scope="session")
def dg_lab_local_client_fixture(dg_lab_ws_server: DGLabWSServer) -> DGLabLocalClient:
    return dg_lab_ws_server.new_local_client()


@pytest_asyncio.fixture(name="client_websocket", scope="session")
async def client_websocket_fixture() -> WebSocketClientProtocol:
    async with connect(WEBSOCKET_URI) as client_websocket:
        yield client_websocket


@pytest_asyncio.fixture(name="app_new_websocket_for_local", scope="session")
async def app_new_websocket_for_local_fixture() -> WebSocketClientProtocol:
    async with connect(WEBSOCKET_URI) as app_new_websocket_for_local:
        yield app_new_websocket_for_local


@pytest_asyncio.fixture(name="app_new_websocket_for_ws", scope="session")
async def app_new_websocket_for_ws_fixture() -> WebSocketClientProtocol:
    async with connect(WEBSOCKET_URI) as app_new_websocket_for_ws:
        yield app_new_websocket_for_ws


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


@pytest.mark.asyncio
async def test_dg_lab_ws_connect(dg_lab_ws_server: DGLabWSServer):
    async with DGLabWSConnect(WEBSOCKET_URI) as client:
        assert client.client_id in dg_lab_ws_server.uuid_to_ws.keys()
        assert client.client_id is not None
        assert client.not_registered is False
        assert client.not_bind is True


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
        dg_lab_local_client: DGLabLocalClient,
        local_register_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with global_lock:
        assert dg_lab_local_client.client_id is not None
        assert dg_lab_local_client.not_registered is False
        assert dg_lab_local_client.not_bind is True

        # Local client will register when initializing
        await dg_lab_local_client.register()

        assert dg_lab_local_client.client_id in dg_lab_ws_server.local_client_ids
        assert dg_lab_local_client.client_id is not None
        assert dg_lab_local_client.not_registered is False
        assert dg_lab_local_client.not_bind is True

        local_register_lock.release()


@pytest.mark.asyncio
async def test_dg_lab_ws_register(
        dg_lab_ws_server: DGLabWSServer,
        dg_lab_ws_client: DGLabWSClient,
        ws_register_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with global_lock:
        assert dg_lab_ws_client.client_id is None
        assert dg_lab_ws_client.not_registered is True
        assert dg_lab_ws_client.not_bind is True

        await dg_lab_ws_client.register()

        assert dg_lab_ws_client.client_id in dg_lab_ws_server.uuid_to_ws.keys()
        assert dg_lab_ws_client.client_id is not None
        assert dg_lab_ws_client.not_registered is False
        assert dg_lab_ws_client.not_bind is True

        ws_register_lock.release()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uri,expected_generator,only_for",
    [
        (
                "ws://localhost:8080",
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#ws://localhost:8080/{uuid}",
                None
        ),
        (
                "ws://153.216.254.135:5678",
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#ws://153.216.254.135:5678/{uuid}",
                None
        ),
        (
                "wss://website.cir:4567",
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#wss://website.cir:4567/{uuid}",
                None
        ),
        (
                "ws://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:4567",
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#ws://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:4567/{uuid}",
                None
        ),
        (
                None,
                lambda uuid: "https://www.dungeon-lab.com/app-download.php"
                             "#DGLAB-SOCKET"
                             f"#ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/{uuid}",
                "ws"
        ),
        (
                None,
                lambda _: None,
                "local"
        ),
    ]
)
async def test_dg_lab_client_get_qrcode(
        uri: str,
        only_for: Literal["local", "ws"],
        expected_generator,
        dg_lab_local_client: DGLabLocalClient,
        dg_lab_ws_client: DGLabWSClient,
        local_register_lock: asyncio.Lock,
        ws_register_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_register_lock,
            ws_register_lock,
            global_lock
    ):
        for client in dg_lab_local_client, dg_lab_ws_client:
            if (
                    (only_for == "local" and isinstance(client, DGLabWSClient)) or
                    (only_for == "ws" and isinstance(client, DGLabLocalClient))
            ):
                continue
            assert client.get_qrcode(uri) == expected_generator(client.client_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_message",
    [
        "f05f7b2c-921f-426e-a79b-f275fa5623b4",
        "[]",
        "{type=bind}",
        '""',
        "{'type':'bind','clientId':'','targetId':'','message':''}",
        '{"type":"bind","clientId":"","targetId":""}'
    ]
)
async def test_dg_lab_non_json_content(
        raw_message: str,
        app_simulator_for_local: DGLabAppSimulator,
        app_simulator_for_ws: DGLabAppSimulator,
        global_lock: asyncio.Lock  # 只需要全局锁，因为此处只有 App 需要注册
):
    async with global_lock:
        for app in app_simulator_for_local, app_simulator_for_ws:
            if app.target_id is None:
                await app.register()
            await app.websocket.send(raw_message)
            assert await app.recv_non_json_content() == RetCode.NON_JSON_CONTENT


@pytest.mark.asyncio
async def test_dg_lab_client_bind(
        client_app_pairs: List[ClientAppPair],
        dg_lab_ws_server: DGLabWSServer,
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with global_lock:
        assert not dg_lab_ws_server.client_id_to_target_id
        assert not dg_lab_ws_server.target_id_to_client_id

        for (client, app), get_bind in zip(
                client_app_pairs,
                [
                    lambda x: x.bind(),
                    lambda x: x.ensure_bind()
                ]
        ):  # type: (DGLabClient, DGLabAppSimulator), Callable[[DGLabClient], Coroutine]
            if app.target_id is None:
                await app.register()
            await app.bind(client.client_id)
            await get_bind(client)

            assert dg_lab_ws_server.client_id_to_target_id.get(client.client_id) == app.target_id
            assert dg_lab_ws_server.target_id_to_client_id.get(app.target_id) == client.client_id
            assert client.target_id == app.target_id
            assert client.not_bind is not True

        for lock in local_bind_lock, ws_bind_lock:
            lock.release()


@pytest.mark.asyncio
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
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await app.send_strength(strength_data)
            while True:
                data = await client.recv_data()
                if isinstance(data, StrengthData):
                    assert data == strength_data
                    break


@pytest.mark.asyncio
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
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await app.send_feedback(feedback_button)
            if isinstance(client, DGLabWSClient):
                # 顺便测试一下异步生成器
                async for data in client.data_generator(FeedbackButton):
                    assert data == feedback_button
                    break
            else:
                assert await client.recv_data() == feedback_button


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args,expected",
    [
        ((
                 Channel.A,
                 StrengthOperationType.DECREASE,
                 0
         ), "strength-1+0+0"),
        ((
                 Channel.A,
                 StrengthOperationType.INCREASE,
                 100
         ), "strength-1+1+100"),
        ((
                 Channel.A,
                 StrengthOperationType.SET_TO,
                 200
         ), "strength-1+2+200"),
    ]
)
async def test_dg_lab_client_set_strength(
        args,
        expected,
        client_app_pairs: List[ClientAppPair],
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await client.set_strength(*args)
            message = await app.recv_msg_type_data()

            assert message.type == MessageType.MSG
            assert message.client_id == client.client_id
            assert message.target_id == app.target_id
            assert message.message == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args,expected",
    [
        ((
                 Channel.A,
                 *[((0, 0, 0, 0), (0, 0, 0, 0))]
         ), {"pulse-1": ["0000000000000000"]}),
        ((
                 Channel.B,
                 *[((0, 0, 0, 0), (10, 10, 10, 10)), ((15, 15, 15, 15), (15, 15, 15, 15))]
         ), {"pulse-2": ["000000000a0a0a0a", "0f0f0f0f0f0f0f0f"]}),
    ]
)
async def test_dg_lab_client_add_pulses(
        args,
        expected,
        client_app_pairs: List[ClientAppPair],
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await client.add_pulses(*args)
            message = await app.recv_msg_type_data()

            assert message.type == MessageType.MSG
            assert message.client_id == client.client_id
            assert message.target_id == app.target_id
            assert json.loads(message.message) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "channel,expected",
    [
        (Channel.A, "clear-1"),
        (Channel.B, "clear-2"),
    ]
)
async def test_dg_lab_clear_pulses(
        channel,
        expected,
        client_app_pairs: List[ClientAppPair],
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await client.clear_pulses(channel)
            message = await app.recv_msg_type_data()

            assert message.type == MessageType.MSG
            assert message.client_id == client.client_id
            assert message.target_id == app.target_id
            assert message.message == expected


@pytest.mark.asyncio
@pytest.mark.timeout(HEARTBEAT_INTERVAL * HEARTBEAT_TEST_TIMES + HEARTBEAT_TEST_EXTRA_WAIT)
async def test_dg_lab_heartbeat(
        dg_lab_ws_server: DGLabWSServer,
        dg_lab_ws_client: DGLabWSClient,
        app_simulator_for_ws: DGLabAppSimulator,
        ws_register_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(ws_register_lock, global_lock):
        if app_simulator_for_ws.target_id is None:
            await app_simulator_for_ws.register()
        await asyncio.sleep(HEARTBEAT_INTERVAL * HEARTBEAT_TEST_TIMES)

        received_heartbeat = 0
        async for code in dg_lab_ws_client.data_generator(RetCode):
            if code == RetCode.SUCCESS:
                received_heartbeat += 1
                if received_heartbeat == HEARTBEAT_TEST_TIMES:
                    break

        received_heartbeat = 0
        while received_heartbeat != HEARTBEAT_TEST_TIMES:
            if (await app_simulator_for_ws.recv_heartbeat()) == RetCode.SUCCESS:
                received_heartbeat += 1
                if received_heartbeat == HEARTBEAT_TEST_TIMES:
                    break


@pytest.mark.asyncio
async def test_dg_lab_app_disconnect(
        dg_lab_ws_server: DGLabWSServer,
        client_app_pairs: List[ClientAppPair],
        app_new_websocket_for_local: WebSocketClientProtocol,
        app_new_websocket_for_ws: WebSocketClientProtocol,
        local_bind_lock: asyncio.Lock,
        ws_bind_lock: asyncio.Lock,
        global_lock: asyncio.Lock
):
    async with locks_context_manager(
            local_bind_lock,
            ws_bind_lock,
            global_lock
    ):
        for client, app in client_app_pairs:
            await app.websocket.close()
            async for code in client.data_generator(RetCode):
                if code == RetCode.CLIENT_DISCONNECTED:
                    # App 重新建立连接，并注册和绑定
                    if isinstance(client, DGLabLocalClient):
                        app.websocket = app_new_websocket_for_local
                    else:
                        app.websocket = app_new_websocket_for_ws
                    await app.register()
                    await app.bind(client.client_id)
                    await client.bind()
                    break


@pytest.mark.asyncio
async def test_dg_lab_ws_client_disconnect(dg_lab_ws_server: DGLabWSServer):
    # 创建新的终端和 App，防止干扰到其他测试
    async with DGLabWSConnect(WEBSOCKET_URI) as ws_client:
        async with ws_client:
            async with connect(WEBSOCKET_URI) as websocket:
                app = DGLabAppSimulator(websocket)
                await app.register()
                await app.bind(ws_client.client_id)
                await ws_client.bind()
                await ws_client.websocket.close()
                assert await app.recv_disconnect() == RetCode.CLIENT_DISCONNECTED


@pytest.mark.asyncio
async def test_dg_lab_ws_server_remove_local_client(dg_lab_ws_server: DGLabWSServer):
    # 创建新的终端和 App，防止干扰到其他测试
    local_client = dg_lab_ws_server.new_local_client()
    async with connect(WEBSOCKET_URI) as websocket:
        app = DGLabAppSimulator(websocket)
        await app.register()
        await app.bind(local_client.client_id)
        await local_client.bind()
        assert await dg_lab_ws_server.remove_local_client(app.target_id) is False
        assert await dg_lab_ws_server.remove_local_client(app.client_id) is True
        assert await app.recv_disconnect() == RetCode.CLIENT_DISCONNECTED
