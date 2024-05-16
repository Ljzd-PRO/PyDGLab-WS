"""
此处定义了一些异常类
"""
__all__ = ("InvalidStrengthData", "InvalidFeedbackData", "InvalidPulseOperation")

from typing import Any


class InvalidStrengthData(Exception):
    """强度数据不合法"""

    def __init__(self, strength_data: str):
        super().__init__(f"Invalid strength data: {strength_data}")


class InvalidFeedbackData(Exception):
    """App 反馈按钮数据不合法"""

    def __init__(self, feedback_data: str):
        super().__init__(f"Invalid strength data: {feedback_data}")


class InvalidPulseOperation(Exception):
    """波形操作数据不合法"""

    def __init__(self, pulse_operation: Any):
        super().__init__(f"Invalid pulse operation: {pulse_operation}")
