import pytest

from pytest_asyncio import is_async_test


def pytest_collection_modifyitems(items):
    # 将所有 asyncio test 标记为在会话内使用同一事件循环
    # 该操作是必须的，否则将导致测试时服务端收取不到来自 App 端的消息
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
