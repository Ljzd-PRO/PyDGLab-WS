"""
此处创建了一些自定义类型
"""
from typing import NewType, Tuple

__all__ = (
    "WaveformFrequency",
    "WaveformStrength",
    "WaveformFrequencyOperation",
    "WaveformStrengthOperation",
    "PulseOperation"
)

WaveformFrequency = NewType("WaveformFrequency", int)
"""波形频率"""
WaveformStrength = NewType("WaveformStrength", int)
"""波形强度"""
WaveformFrequencyOperation = NewType(
    "WaveformFrequencyOperation",
    Tuple[
        WaveformFrequency, WaveformFrequency, WaveformFrequency, WaveformFrequency
    ]
)
WaveformStrengthOperation = NewType(
    "WaveformStrengthOperation",
    Tuple[
        WaveformStrength, WaveformStrength, WaveformStrength, WaveformStrength
    ]
)
PulseOperation = NewType(
    "PulseOperation",
    Tuple[
        WaveformFrequencyOperation,
        WaveformStrengthOperation
    ]
)
"""波形操作数据，类似 DG-Lab-V3 蓝牙协议中的波形数据"""
