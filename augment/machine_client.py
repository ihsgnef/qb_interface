import logging
import numpy as np
import chainer

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer
from qanta.experimental.get_highlights import get_highlights

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logger = logging.getLogger('guesser_buzzer_client')


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
        # gspec = AbstractGuesser.list_enabled_guessers()[0]
        guesser_dir = 'data/guesser'
        self.guesser = ElasticSearchWikidataGuesser.load(guesser_dir)

        if chainer.cuda.available:
            self.buzzer = RNNBuzzer(
                model_dir=buzzer_model_dir,
                word_skip=conf['buzzer_word_skip'],
            )
        else:
            self.buzzer = StupidBuzzer()

        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.matches = []

    def new_question(self, qid):
        self.buzzer.new_round()
        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.matches = []

    def buzz(self, text, position):
        guesses = self.guesser.guess_single(text)
        if not isinstance(guesses, dict):
            guesses = {x[0]: x[1] for x in guesses}

        buzz_scores = [0, 1]  # [wait, buzz]
        if self.ok_to_buzz:
            buzz_scores = self.buzzer.buzz(guesses)
            if isinstance(buzz_scores, np.ndarray):
                buzz_scores = buzz_scores.tolist()

        guesses = sorted(guesses.items(), key=lambda x: x[1])[::-1]
        self.guesses = guesses
        if len(guesses) > 0:
            self.answer = guesses[0][0]
        self.matches = get_highlights(text)
        return buzz_scores


if __name__ == '__main__':
    # factory = WebSocketClientFactory(u"ws://play.qanta.org:9000")
    # factory.protocol = GuesserBuzzerProtocol
    # connectWS(factory)
    # reactor.run()
    pass
