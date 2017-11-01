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

    def get_deferred(self, delay=3):
        d = Deferred()
        d.addTimeout(delay, reactor)
        return d

    def check0(self):
        _condition = lambda: self.count > 0

        def _callback(x):
            print('check0 pass')
            self.check1()

        if _condition():
            _callback(None)
        else:
            self._deferred = Deferred()
            self._condition = _condition
            self._deferred.addTimeout(3, reactor)
            self._deferred.addCallback(_callback)
            self._deferred.addErrback(lambda x: print('check0 time out'))

    def check1(self):
        _condition = lambda: self.count > 1

        def _callback(x):
            print('check1 pass')
            self.check2()

        if _condition():
            _callback(None)
        else:
            self._deferred = Deferred()
            self._condition = _condition
            self._deferred.addTimeout(3, reactor)
            self._deferred.addCallback(_callback)
            self._deferred.addErrback(lambda x: print('check1 time out'))
        
    def check2(self):
        _condition = lambda: self.count > 2

        def _callback(x):
            print('check2 pass')

        if _condition():
            _callback(None)
        else:
            self._deferred = Deferred()
            self._condition = _condition
            self._deferred.addTimeout(3, reactor)
            self._deferred.addCallback(_callback)
            self._deferred.addErrback(lambda x: print('check2 time out'))

    def check(self):
        self.check0()

    def receive(self, msg, client):
        if msg:
            print('check')
            self.check()
        else:
            self.count += 1
            if self._condition():
                print('firing callback')
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
