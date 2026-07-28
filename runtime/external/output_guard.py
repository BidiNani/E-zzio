
class OutputGuard:

    def __init__(self, max_size=65536):
        self.max_size = max_size
        self._buffer = []
        self._error_buffer = []
        self.truncated = False


    def feed(self, data):
        if data is None:
            return

        text = str(data)

        current = len(self.get_output())

        if current + len(text) > self.max_size:
            remaining = self.max_size - current

            if remaining > 0:
                self._buffer.append(text[:remaining])

            self.truncated = True
        else:
            self._buffer.append(text)


    def feed_error(self, data):
        if data:
            self._error_buffer.append(str(data))


    def get_output(self):
        return "".join(self._buffer)


    def get_error(self):
        return "".join(self._error_buffer)


    def is_success(self):
        return True


    def clear(self):
        self._buffer.clear()
        self._error_buffer.clear()
        self.truncated=False
