class BaseLoRa:
    """
    Abstract base class for LoRa drivers.
    Concrete implementations (e.g., SX1262) must override all methods.
    """

    def begin(self):
        raise NotImplementedError

    def end(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def begin_packet(self):
        raise NotImplementedError

    def end_packet(self, timeout: int) -> bool:
        raise NotImplementedError

    def write(self, data, length: int):
        raise NotImplementedError

    def request(self, timeout: int) -> bool:
        raise NotImplementedError

    def available(self):
        raise NotImplementedError

    def read(self, length: int):
        raise NotImplementedError

    def wait(self, timeout: int) -> bool:
        raise NotImplementedError

    def status(self):
        raise NotImplementedError
