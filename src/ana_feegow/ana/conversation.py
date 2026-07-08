class Conversation:

    def __init__(self):
        self.state = "inicio"
        self.data = {}

    def update(self, key, value):
        self.data[key] = value

    def next(self, state):
        self.state = state

    def get(self):
        return {
            "state": self.state,
            "data": self.data
        }
