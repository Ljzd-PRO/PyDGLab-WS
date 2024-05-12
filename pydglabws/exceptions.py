class InvalidStrengthData(Exception):
    def __init__(self, strength_data: str):
        super().__init__(f"Invalid strength data: {strength_data}")


class InvalidFeedbackData(Exception):
    def __init__(self, feedback_data: str):
        super().__init__(f"Invalid strength data: {feedback_data}")
