import sys
import json
import threading

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

buzzed = threading.Event()

class BroadcastClientProtocol(WebSocketClientProtocol):

    def sendHello(self):
        self.sendMessage(json.dumps(False).encode('utf8'))

    def onOpen(self):
        self.sendHello()

    def onMessage(self, payload, isBinary):
        global buzzed
        if not isBinary:
            print("Text message received: {}".format(payload.decode('utf8')))
            if buzzed:
                print('+++')

class KeypressPoller(threading.Thread):

    def run(self):
        global buzzed
        ch = sys.stdin.read(1)
        if ch == 'b':
            buzzed.set()
        else:
            buzzed.clear()

if __name__ == '__main__':
    poller = KeypressPoller()
    poller.start()
    factory = WebSocketClientFactory("ws://127.0.0.1:9000")
    factory.protocol = BroadcastClientProtocol
    connectWS(factory)
    reactor.run()
