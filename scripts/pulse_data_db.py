import itertools
import json
import math
from pathlib import Path
from typing import List, Tuple, Any

from pydantic import BaseModel, RootModel, field_validator


class PointData(BaseModel):
    x: int
    y: float
    anchor: bool


class PulseData(BaseModel):
    """
    | AX	| 脉冲频率 0-83
    | JX	| 小节时长 0-100
    | L	    | 休息时长 0-100
    | JIEX	| 启用小节 0-1
    | PCX	| 脉冲频率变化规律 1-4
    | BX	| 节内渐变第二参数 0-83
    | CX	| 元内渐变第二参数 0-83

    """
    BG_A0: int
    BG_A1: int
    BG_A2: int
    BG_B0: int
    BG_B1: int
    BG_B2: int
    BG_C0: int
    BG_C1: int
    BG_C2: int
    BG_J0: int
    BG_J1: int
    BG_J2: int
    BG_JIE1: int
    BG_JIE2: int
    BG_L: int
    BG_PC0: int
    BG_PC1: int
    BG_PC2: int
    BG_ZY: int
    BG_bg_createTime: str
    BG_bg_id: int
    BG_bg_updateTime: str
    BG_classic: int
    BG_defaultName: int
    BG_playRate: int
    BG_pluseID: str
    BG_points1: List[PointData]
    BG_points2: List[PointData]
    BG_points3: List[PointData]
    BG_waveName: str
    BG_waveNameEn: str

    @field_validator(
        "BG_points1",
        "BG_points2",
        "BG_points3",
        mode="before"
    )
    @classmethod
    def validate_points(cls, value: Any):
        if isinstance(value, str):
            return json.loads(value)
        else:
            return value


class PulseDataTable(RootModel):
    root: List[PulseData]


class CustomPulseDataJSONEncoder(json.JSONEncoder):
    def iterencode(self, obj, *args, **kwargs):
        if isinstance(obj, dict):
            items = []
            for key, value in obj.items():
                items.append(f"\n{' ' * self.indent}{self.encode(key)}: {self.encode(value)}")
            return '{' + ','.join(items) + '\n}'
        else:
            return super().iterencode(obj, *args, **kwargs)

    def encode(self, o: Any):
        if isinstance(o, list) or isinstance(o, tuple):
            return '[' + ', '.join(self.encode(element) for element in o) + ']'
        else:
            return super().encode(o)


def read_pulse_data_from_json(path: Path) -> List[PulseData]:
    with path.open(encoding="utf-8") as f:
        return PulseDataTable.model_validate_json(f.read()).root


def ms_to_frequency(data: int) -> int:
    if 10 <= data <= 100:
        return data
    elif 101 <= data <= 600:
        return round((data - 100) / 5 + 100)
    elif 601 <= data <= 1000:
        return round((data - 600) / 10 + 200)
    else:
        return 10


def parse_frequency(data: int) -> int:
    boundary_multiple_pair = ((40, 1), (15, 2), (4, 5), (10, 10), (6, 100 / 3), (4, 50), (4, 100))

    accumulate, frequency_value, multiple = 0, 0, 0
    for accumulate, frequency_value, multiple in zip(
            itertools.accumulate(
                map(lambda x: x[0], boundary_multiple_pair)
            ),
            itertools.accumulate(
                map(lambda x: x[0] * x[1], boundary_multiple_pair)
            ),
            map(lambda x: x[0], boundary_multiple_pair)
    ):
        accumulate: int
        frequency_value: float
        multiple: float
        if accumulate >= data:
            break
    return round(frequency_value - (accumulate - data) * multiple)


def parse_part_time(data: int) -> int:
    known_data_to_value = {
        0: 0.1,
        6: 0.2,
        20: 0.9,
        22: 1.0,
        25: 1.2,
        33: 1.8,
        35: 2.0,
        36: 2.1,
        39: 2.3,
        40: 2.4,
        41: 2.5,
        44: 2.8,
        45: 2.9,
        53: 3.7,
    }
    if value := known_data_to_value.get(data):
        return value
    else:
        print(f"parse_part_time: {data} not in known values")
        raise KeyError


def parse_sleep_time(data: int) -> float:
    return (data // 10) / 10


def parse_strength_data(data: float) -> int:
    return round((100 / 20) * data)


def get_each_x_y(x_range: Tuple[int, int], y_range: Tuple[float, float]) -> List[Tuple[int, float]]:
    x_start, x_end = x_range
    y_start, y_end = y_range

    results = {}
    for x in range(x_end - 1):
        y = y_start + (y_end - y_start) * (x - x_start) / (x_end - x_start)
        results[x] = y
    results[x_end - 1] = y_end

    return list(results.items())


def generate_static_frequency(point_num: int, ax: int, _: int, __: int) -> List[Tuple[int, ...]]:
    frequency = ms_to_frequency(parse_frequency(ax))
    return [
        tuple(frequency for _ in range(4)) for __ in range(point_num)
    ]


def generate_part_frequency(point_num: int, ax: int, bx: int, _: int) -> List[Tuple[int, ...]]:
    frequency_a = ms_to_frequency(parse_frequency(ax))
    frequency_b = ms_to_frequency(parse_frequency(bx))
    frequencies = list(
        map(
            lambda x: round(x[1]),
            get_each_x_y(
                (0, point_num * 4),
                (frequency_a, frequency_b)
            )
        )
    )
    return [
        tuple(frequencies[i:i + 4]) for i in range(0, len(frequencies), 4)
    ]


def generate_inside_point_frequency(point_num: int, ax: int, _: int, cx: int) -> List[Tuple[int, ...]]:
    frequency_a = ms_to_frequency(parse_frequency(ax))
    frequency_c = ms_to_frequency(parse_frequency(cx))
    frequencies_inside_point = list(
        map(
            lambda x: round(x[1]),
            get_each_x_y(
                (0, 4),
                (frequency_a, frequency_c)
            )
        )
    )
    return [
        tuple(frequency for frequency in frequencies_inside_point) for __ in range(point_num)
    ]


def generate_point_each_frequency(point_num: int, ax: int, _: int, cx: int) -> List[Tuple[int, ...]]:
    frequency_a = ms_to_frequency(parse_frequency(ax))
    frequency_c = ms_to_frequency(parse_frequency(cx))
    frequencies_for_points = list(
        map(
            lambda x: round(x[1]),
            get_each_x_y(
                (0, point_num),
                (frequency_a, frequency_c)
            )
        )
    )
    return [
        tuple(frequency for _ in range(4)) for frequency in frequencies_for_points
    ]


def generate_frequency(pcx: int, point_num: int, ax: int, bx: int, cx: int) -> List[Tuple[int, ...]]:
    type_to_func = {
        1: generate_static_frequency,
        2: generate_part_frequency,
        3: generate_inside_point_frequency,
        4: generate_point_each_frequency
    }
    return type_to_func[pcx](point_num, ax, bx, cx)


def generate_strength_from_strength(strength: List[int]) -> List[Tuple[int, ...]]:
    return [
        tuple(strength[i:i + 4]) for i in range(0, len(strength), 4)
    ]


def generate_strength(point_datas: List[PointData]) -> List[Tuple[int, ...]]:
    strength_data = []
    for index, point in enumerate(point_datas):
        index: int
        point: PointData
        current_strength = parse_strength_data(point.y)
        if point.anchor:
            strength_data.append(
                tuple(current_strength for _ in range(4))
            )
        else:
            last_point = point_datas[index - 1]
            last_strength = parse_strength_data(last_point.y)
            strength_data.extend(
                generate_strength_from_strength(
                    list(
                        map(
                            lambda x: round(x[1]),
                            get_each_x_y(
                                (0, (point.x - last_point.x) * 4),
                                (last_strength, current_strength)
                            )
                        )
                    )
                )
            )
    return strength_data


def generate_operations_from_sleep(sleep_time: float) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    return [
        ((0, 0, 0, 0), (0, 0, 0, 0)) for _ in range(
            round(sleep_time * 1000 / 100)
        )
    ]


def generate_operations_from_part(
        ax: int,
        bx: int,
        cx: int,
        pcx: int,
        jx: int,
        point_datas: List[PointData]
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    frequencies = generate_frequency(pcx, len(point_datas), ax, bx, cx)
    strength = generate_strength(point_datas)
    operations = list(zip(frequencies, strength))
    repeat = math.ceil(parse_part_time(jx) / len(point_datas) * 0.1)
    return operations * repeat


def generate_result_from_pulse_data(pulse_data: PulseData) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    operations = generate_operations_from_part(
        pulse_data.BG_A0,
        pulse_data.BG_B0,
        pulse_data.BG_C0,
        pulse_data.BG_PC0,
        pulse_data.BG_J0,
        pulse_data.BG_points1
    )
    if pulse_data.BG_JIE1:
        operations.extend(
            generate_operations_from_part(
                pulse_data.BG_A1,
                pulse_data.BG_B1,
                pulse_data.BG_C1,
                pulse_data.BG_PC1,
                pulse_data.BG_J1,
                pulse_data.BG_points2
            )
        )
    if pulse_data.BG_JIE2:
        operations.extend(
            generate_operations_from_part(
                pulse_data.BG_A2,
                pulse_data.BG_B2,
                pulse_data.BG_C2,
                pulse_data.BG_PC2,
                pulse_data.BG_J2,
                pulse_data.BG_points3
            )
        )
    operations.extend(
        generate_operations_from_sleep(
            parse_sleep_time(pulse_data.BG_L)
        )
    )
    return operations


def main():
    pulse_datas = read_pulse_data_from_json(
        Path("appPulseData.json")
    )
    custom_pulse_data = {}
    for pulse_data in pulse_datas:
        result = generate_result_from_pulse_data(pulse_data)
        with Path(f"{pulse_data.BG_waveName}.json").open("w", encoding="utf-8") as file:
            json.dump(result, file)
        custom_pulse_data[pulse_data.BG_waveName] = result

    with Path("customPulseData.json").open("w", encoding="utf-8") as f:
        json.dump(custom_pulse_data, f, indent=4, ensure_ascii=False, cls=CustomPulseDataJSONEncoder)

    print(custom_pulse_data)


if __name__ == "__main__":
    main()
