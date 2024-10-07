class Is:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other

    def __repr__(self):
        return f"Is({repr(self.value)})"
