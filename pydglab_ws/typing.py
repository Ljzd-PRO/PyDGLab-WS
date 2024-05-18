"""
此处创建了一些自定义类型
"""
from typing import Tuple

__all__ = (
    "WaveformFrequency",
    "WaveformStrength",
    "WaveformFrequencyOperation",
    "WaveformStrengthOperation",
    "PulseOperation"
)

WaveformFrequency = int
"""波形频率，范围在 [10, 240]"""
WaveformStrength = int
"""波形强度，范围在 [0, 100]"""
WaveformFrequencyOperation = Tuple[
    WaveformFrequency, WaveformFrequency, WaveformFrequency, WaveformFrequency
]
"""波形频率操作数据"""
WaveformStrengthOperation = Tuple[
    WaveformStrength, WaveformStrength, WaveformStrength, WaveformStrength
]
"""波形强度操作数据"""
PulseOperation = Tuple[
    WaveformFrequencyOperation,
    WaveformStrengthOperation
]
"""波形操作数据"""
