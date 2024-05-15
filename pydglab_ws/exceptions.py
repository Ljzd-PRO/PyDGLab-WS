"""
此处定义了一些异常类
"""
__all__ = ("InvalidStrengthData", "InvalidFeedbackData", "InvalidPulseOperation")

from typing import Any


class InvalidStrengthData(Exception):
    def __init__(self, strength_data: str):
        super().__init__(f"Invalid strength data: {strength_data}")


class InvalidFeedbackData(Exception):
    def __init__(self, feedback_data: str):
        super().__init__(f"Invalid strength data: {feedback_data}")


class InvalidPulseOperation(Exception):
    def __init__(self, pulse_operation: Any):
        super().__init__(f"Invalid pulse operation: {pulse_operation}")
