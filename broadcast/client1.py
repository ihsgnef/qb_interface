import sys
import json
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS


class BroadcastClientProtocol(WebSocketClientProtocol):

    def sendHello(self):
        self.sendMessage(json.dumps(True).encode('utf8'))

    def onOpen(self):
        self.sendHello()

    def onMessage(self, payload, isBinary):
        if not isBinary:
            print("Text message received: {}".format(payload.decode('utf8')))


if __name__ == '__main__':
    factory = WebSocketClientFactory("ws://127.0.0.1:9000")
    factory.protocol = BroadcastClientProtocol
    connectWS(factory)
    reactor.run()
