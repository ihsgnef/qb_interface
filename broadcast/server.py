import sys
import json
from functools import partial

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, \
    listenWS


class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(json.loads(payload.decode('utf8')), self.peer)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.count = 0
        self._deferred = None
        self._condition = lambda: False

    def register(self, client):
        if client not in self.clients:
            print("registered client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print("unregistered client {}".format(client.peer))
            self.clients.remove(client)

    def _compare(self, value):
        return self.count > value

    def get_deferred(self, delay=3):
        d = Deferred()
        d.addTimeout(delay, reactor)
        return d

    def _check(self, value):
        self._condition = partial(self._compare, value)
        d = self._deferred = self.get_deferred()
        return d

    def check(self):
        print('check0')
        self.d = self._check(0)
        self.d.addCallback(lambda x: print('check0 pass'))
        self.d.addErrback(lambda x: print('check0 timeout'))

        self.d.addCallback(lambda x: print('check1'))
        self.d.addCallback(self._check, 1)
        self.d.addCallback(lambda x: print('check1 pass'))
        self.d.addErrback(lambda x: print('check1 timeout'))

        self.d.addCallback(lambda x: print('check2'))
        self.d.addCallback(self._check, 2)
        self.d.addCallback(lambda x: print('check2 pass'))
        self.d.addErrback(lambda x: print('check2 timeout'))

    def receive(self, msg, client):
        if msg:
            print('check')
            self.check()
        else:
            self.count += 1
            if self._condition():
                if self._deferred and not self._deferred.called:
                    self._deferred.callback(None)
            print('self.count', self.count)
        
    def broadcast(self, msg):
        print("broadcasting message '{}' ..".format(msg))
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))
            print("message sent to {}".format(c.peer))


if __name__ == '__main__':
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000")
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)
    reactor.run()
