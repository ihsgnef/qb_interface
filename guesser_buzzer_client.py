import json
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer

from client import UserProtocol

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logger = logging.getLogger('client')

class GuesserBuzzer:
    
    def __init__(self, buzzer_model_dir='data/neo_0.npz'):
        gspec = AbstractGuesser.list_enabled_guessers()[0]
        guesser_dir = 'data/guesser'
        self.guesser = ElasticSearchWikidataGuesser.load(guesser_dir)

        self.buzzer = RNNBuzzer(model_dir=buzzer_model_dir,
                word_skip=conf['buzzer_word_skip'])

        self.ok_to_buzz = True

    def new_question(self):
        self.buzzer.new_round()
        self.ok_to_buzz = True

    def buzz(self, text):
        guesses = self.guesser.guess_single(text)
        if not isinstance(guesses, dict):
            guesses = {x[0]: x[1] for x in guesses}
        buzz_scores = [0, 1]
        if self.ok_to_buzz:
            buzz_scores = self.buzzer.buzz(guesses)
        guesses = sorted(guesses.items(), key=lambda x: x[1])[::-1]
        if len(guesses) > 0:
            self.answer = guesses[0][0]
        return buzz_scores

guesser_buzzer = GuesserBuzzer()

class GuesserBuzzerProtocol(UserProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''

    def new_question(self, msg):
        guesser_buzzer.new_question()
        super(GuesserBuzzerProtocol, self).new_question(msg)

    def buzz(self):
        buzz_scores = guesser_buzzer.buzz(self.text)
        self.answer = guesser_buzzer.answer
        print(buzz_scores, self.answer)
        buzzing = buzz_scores[0] > buzz_scores[1]
        if buzzing:
            guesser_buzzer.ok_to_buzz = False
        return buzzing


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = GuesserBuzzerProtocol
    connectWS(factory)
    reactor.run()
