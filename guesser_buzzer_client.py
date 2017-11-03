import json
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GuesserBuzzerProtocol(UserProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''

    def buzz(self):
        self.answer = 'Chubakka'
        return self.position > 5

class GuesserBuzzer:
    
    def __init__(self):
        self.buzzer = RNNBuzzer()

        gspec = AbstractGuesser.list_enabled_guessers()[0]
        guesser_dir = AbstractGuesser.output_path(gspec.guesser_module,
                gspec.guesser_class, '')
        self.guesser = ElasticSearchWikidataGuesser.load(guesser_dir)

    def buzz(self, text):
        guesses = self.guesser.guess_single(text)

if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = GuesserBuzzerProtocol
    connectWS(factory)
    reactor.run()

