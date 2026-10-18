import base64
import json


class ChromeConnection:
    def __init__(self, connection):
        self.connection = connection
        self.request_number = 0
        self.session_identifier = None

    def send(self, method, parameters=None):
        self.request_number += 1
        request = {"id": self.request_number, "method": method}
        if parameters is not None:
            request["params"] = parameters
        if self.session_identifier:
            request["sessionId"] = self.session_identifier
        self.connection.send(json.dumps(request))
        return self.request_number

    def request(self, method, parameters=None):
        request_number = self.send(method, parameters)
        while True:
            response = json.loads(self.connection.recv(timeout=30))
            if response.get("id") != request_number:
                continue
            if "error" in response:
                raise RuntimeError(response["error"])
            return response.get("result", {})

    def evaluate(self, expression):
        result = self.request(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def screenshot(self, destination, width, height):
        result = self.request(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
            },
        )
        destination.write_bytes(base64.b64decode(result["data"]))
