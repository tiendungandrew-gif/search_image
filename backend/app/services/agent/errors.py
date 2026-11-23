class AgentError(Exception):
    def __init__(self, code: str, status: str = "failed"):
        self.code = code
        self.status = status
        super().__init__(code)
