from uuid import uuid4

import pytest

from pydglab_ws.enums import FeedbackButton, Channel, StrengthOperationType
from pydglab_ws.exceptions import InvalidStrengthData, InvalidFeedbackData
from pydglab_ws.models import StrengthData
from pydglab_ws.typing import PulseOperation
from pydglab_ws.utils import parse_strength_data, parse_feedback_data, dump_strength_operation, dump_clear_pulses, \
    dump_pulse_operation, dump_add_pulses, dg_lab_client_qrcode


@pytest.mark.parametrize(
    "data,expected",
    [
        ("strength-0+0+0+0", StrengthData(a=0, b=0, a_limit=0, b_limit=0)),
        ("strength-200+0+0+0", StrengthData(a=200, b=0, a_limit=0, b_limit=0)),
        ("strength-0+200+0+0", StrengthData(a=0, b=200, a_limit=0, b_limit=0)),
        ("strength-0+0+200+0", StrengthData(a=0, b=0, a_limit=200, b_limit=0)),
        ("strength-0+0+0+200", StrengthData(a=0, b=0, a_limit=0, b_limit=200)),
        ("feedback-1", InvalidStrengthData),
    ]
)
def test_parse_strength_data(data: str, expected):
    try:
        ret = parse_strength_data(data)
    except Exception as e:
        assert isinstance(e, expected)
    else:
        assert ret == expected


@pytest.mark.parametrize(
    "data,expected",
    [
        ("feedback-0", FeedbackButton(0)),
        ("feedback-4", FeedbackButton(4)),
        ("feedback-5", FeedbackButton(5)),
        ("feedback-9", FeedbackButton(9)),
        ("DGLAB", InvalidFeedbackData),
    ]
)
def test_feedback_data(data: str, expected):
    try:
        ret = parse_feedback_data(data)
    except Exception as e:
        assert isinstance(e, expected)
    else:
        assert ret == expected


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
        ((
                 Channel.B,
                 StrengthOperationType.DECREASE,
                 0
         ), "strength-2+0+0"),
        ((
                 Channel.B,
                 StrengthOperationType.INCREASE,
                 100
         ), "strength-2+1+100"),
        ((
                 Channel.B,
                 StrengthOperationType.SET_TO,
                 200
         ), "strength-2+2+200"),
    ]
)
def test_dump_strength_operation(args, expected):
    assert dump_strength_operation(*args) == expected


@pytest.mark.parametrize(
    "channel,expected",
    [
        (Channel.A, "clear-1"),
        (Channel.B, "clear-2"),
    ]
)
def test_dump_clear_pulses(channel: Channel, expected):
    assert dump_clear_pulses(channel) == expected


@pytest.mark.parametrize(
    "pulse,expected",
    [
        (((0, 0, 0, 0), (0, 0, 0, 0)), "0000000000000000"),
        (((9, 9, 9, 9), (0, 0, 0, 0)), "0909090900000000"),
        (((0, 0, 0, 0), (10, 10, 10, 10)), "000000000a0a0a0a"),
        (((15, 15, 15, 15), (15, 15, 15, 15)), "0f0f0f0f0f0f0f0f"),
    ]
)
def test_dump_pulse_operation(pulse: PulseOperation, expected):
    assert dump_pulse_operation(pulse) == expected


@pytest.mark.parametrize(
    "args,expected",
    [
        ((
                 Channel.A,
                 *[((0, 0, 0, 0), (0, 0, 0, 0))]
         ), "pulse-1:['0000000000000000']"),
        ((
                 Channel.A,
                 *[((0, 0, 0, 0), (0, 0, 0, 0)), ((9, 9, 9, 9), (0, 0, 0, 0))]
         ), "pulse-1:['0000000000000000', '0909090900000000']"),
        ((
                 Channel.B,
                 *[((0, 0, 0, 0), (10, 10, 10, 10))]
         ), "pulse-2:['000000000a0a0a0a']"),
        ((
                 Channel.B,
                 *[((0, 0, 0, 0), (10, 10, 10, 10)), ((15, 15, 15, 15), (15, 15, 15, 15))]
         ), "pulse-2:['000000000a0a0a0a', '0f0f0f0f0f0f0f0f']"),
    ]
)
def test_dump_add_pulses(args, expected):
    assert dump_add_pulses(*args) == expected


@pytest.mark.parametrize(
    "args,expected",
    [
        (
                ("ws://localhost:8080", uuid := uuid4()),
                "https://www.dungeon-lab.com/app-download.php"
                "#DGLAB-SOCKET"
                f"#ws://localhost:8080/{uuid}"
        ),
        (
                ("ws://153.216.254.135:5678", uuid := uuid4()),
                "https://www.dungeon-lab.com/app-download.php"
                "#DGLAB-SOCKET"
                f"#ws://153.216.254.135:5678/{uuid}"
        ),
        (
                ("wss://website.cir:4567", "fd94c0fb-6daf-4c4f-a385-3901506418c7"),
                "https://www.dungeon-lab.com/app-download.php"
                "#DGLAB-SOCKET"
                "#wss://website.cir:4567/fd94c0fb-6daf-4c4f-a385-3901506418c7"
        ),
        (
                ("ws://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:4567", uuid := uuid4()),
                "https://www.dungeon-lab.com/app-download.php"
                "#DGLAB-SOCKET"
                f"#ws://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:4567/{uuid}"
        ),
    ]
)
def test_dg_lab_client_qrcode(args, expected):
    assert dg_lab_client_qrcode(*args) == expected
