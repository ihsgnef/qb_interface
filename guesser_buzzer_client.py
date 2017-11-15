import json
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer

from client import PlayerProtocol
from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
        MSG_TYPE_RESULT_MINE, MSG_TYPE_RESULT_OTHER

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logger = logging.getLogger('guesser_buzzer_client')


def colorize(words, color_array):
    # words is a list of words
    # color_array is an array of numbers between 0 and 1 of length equal to words
    cmap = matplotlib.cm.get_cmap('RdBu')
    template = '<span class="barcode"; style="color: black; background-color: {}">{}</span>'
    colored_string = ''
    for word, color in zip(words, color_array):
        color = matplotlib.colors.rgb2hex(cmap(color)[:3])
        colored_string += template.format(color, '&nbsp' + word + '&nbsp')
    return colored_string

class StupidBuzzer:

    def __init__(self):
        self.step = 0

    def new_round(self):
        self.step = 0
    
    def buzz(self, guesses):
        self.step += 1
        if self.step > 40:
            return [1, 0]
        else:
            return [0, 1]

class GuesserBuzzer:
    
    def __init__(self, buzzer_model_dir='data/neo_0.npz'):
        gspec = AbstractGuesser.list_enabled_guessers()[0]
        guesser_dir = 'data/guesser'
        self.guesser = ElasticSearchWikidataGuesser.load(guesser_dir)

        # self.buzzer = RNNBuzzer(model_dir=buzzer_model_dir,
        #         word_skip=conf['buzzer_word_skip'])
        self.buzzer = StupidBuzzer()

        self.ok_to_buzz = True

    def new_question(self):
        self.buzzer.new_round()
        self.ok_to_buzz = True

    def buzz(self, text):
        guesses = self.guesser.guess_single(text)
        if not isinstance(guesses, dict):
            guesses = {x[0]: x[1] for x in guesses}
        buzz_scores = [0, 1] # [wait, buzz]
        if self.ok_to_buzz:
            buzz_scores = self.buzzer.buzz(guesses)
        guesses = sorted(guesses.items(), key=lambda x: x[1])[::-1]
        self.guesses = guesses
        if len(guesses) > 0:
            self.answer = guesses[0][0]
        return buzz_scores

guesser_buzzer = GuesserBuzzer()

class GuesserBuzzerProtocol(PlayerProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.highlight = ''
        self.position = 0
        self.answer = ''
        self.evidence = dict()

    def new_question(self, msg):
        self.text = ''
        self.highlight = ''
        guesser_buzzer.new_question()
        self.evidence = dict()
        super(GuesserBuzzerProtocol, self).new_question(msg)

    def buzz(self):
        buzz_scores = guesser_buzzer.buzz(self.text) # [wait, buzz]
        self.answer = guesser_buzzer.answer
        if self.evidence is None:
            self.evidence = dict()
        self.evidence['guesses'] = guesser_buzzer.guesses
        self.evidence['highlight'] = self.highlight
        print(buzz_scores, self.answer)
        buzzing = buzz_scores[0] > buzz_scores[1] # [wait, buzz]
        if buzzing:
            guesser_buzzer.ok_to_buzz = False
        return buzzing

    def update_question(self, msg):
        # print(msg['text'], end=' ', flush=True)
        self.text += ' ' + msg['text']
        words = msg['text'].split()
        weights = np.random.uniform(size=len(words))
        self.highlight += colorize(words, weights)
        if self.evidence is None:
            self.evidence = dict()
        msg = {'type': MSG_TYPE_BUZZING_REQUEST,
                'qid': self.qid, 'position': self.position,
                'evidence': self.evidence}
        if self.buzz():
            logger.info("\nBuzzing on answer: {}".format(self.answer))
            msg['type'] = MSG_TYPE_BUZZING_REQUEST
            msg['text'] = 'buzzing'
        else:
            msg['type'] = MSG_TYPE_RESUME
            msg['text'] = 'not buzzing'
        self.sendMessage(json.dumps(msg).encode('utf-8'))
        self.position += 1


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = GuesserBuzzerProtocol
    connectWS(factory)
    reactor.run()
