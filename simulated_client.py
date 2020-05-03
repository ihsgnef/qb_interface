import json
import pickle
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, \
    MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
    MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
    MSG_TYPE_RESULT_MINE
from util import QBQuestion
from util import VIZ
from client import PlayerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')


class SimulatedPlayerProtocol(PlayerProtocol):

    def onOpen(self):
        super().onOpen()

    def buzz(self):
        if self.buzzed:
            return False

        if self.position > 10:
            if sum(self.enabled_viz.values()) > 1:
                self.answer = self.questions[self.qid].answer.replace('_', ' ')
            return True
        else:
            return False


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://play.qanta.org:9000")
    factory.protocol = SimulatedPlayerProtocol
    connectWS(factory)
    reactor.run()
