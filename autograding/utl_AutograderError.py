class AutograderError(Exception):
    def __init__(self, message, expected=None, actual=None, context=None):
        super().__init__(message)
        self.expected = expected
        self.actual = actual
        self.context = context

    def __str__(self):
        error_msg = super().__str__()
        if self.actual or self.expected:
            error_msg += f"\nExpected: {repr(self.expected)}\nActual: {repr(self.actual)}"
        if self.context:
            error_msg += f"\nContext: {self.context}"
        return error_msg