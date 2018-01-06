import re
import json
import pickle
import logging
import numpy as np
from bs4 import BeautifulSoup
import chainer
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer
from qanta.new_expo.hook import HighlightHook
from client import PlayerProtocol
from util.constants import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
        MSG_TYPE_RESULT_MINE, MSG_TYPE_RESULT_OTHER

import spacy
from nltk.corpus import stopwords as sw
''' Contains the different 'guessers' and 'buzzers' that implement the core of the QA system.
Also contains functions for doing the in-text highlighting using beautiful soup '''

stopwords = set(sw.words('english'))
nlp = spacy.load('en')
        
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logger = logging.getLogger('guesser_buzzer_client')

highlight_color = '#ecff6d'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'
highlight_template = highlight_prefix + '{}' + highlight_suffix

def get_matched(text):
    matches = HightlightHook.get_highlights(text)
    matches = matches['qb'][:2] + matches['wiki'][:2]
    match_words = set()
    for match in matches:
        soup = BeautifulSoup(match)
        match = [x.text.lower() for x in soup.find_all('em') 
                    if x.text not in stopwords and len(x.text) > 2]
        match_words.update(match)

    text = nlp(text)
    highlighted = ''    
    matched_words = set()
    for word in text:
        if word.lower_ in match_words:
            highlighted += ' ' + highlight_prefix + word.text + highlight_suffix
            matched_words.add(word.lower_)
        else:
            highlighted += ' ' + word.text
    
    _matches = []
    for match in matches:
        soup = BeautifulSoup(match)
        match = soup.find('p')
        if match is None:
            match = soup.find('body')
        if match is None:
            continue
        _match = ''
        for w in match.children:
            if w.name is None:
                _match += w
                continue
            if w.name == 'em':
                if w.text.lower() in matched_words:
                    _match += highlight_prefix + w.text + highlight_suffix
                else:
                    _match += w.text
        _matches.append(_match)
                    
    return highlighted, _matches

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
        # return [0, 1]

class GuesserBuzzer:
    
    def __init__(self, buzzer_model_dir='data/neo_0.npz'):
        gspec = AbstractGuesser.list_enabled_guessers()[0]
        guesser_dir = 'data/guesser'
        self.guesser = ElasticSearchWikidataGuesser.load(guesser_dir)

        if chainer.cuda.available:
            self.buzzer = RNNBuzzer(model_dir=buzzer_model_dir,
                word_skip=conf['buzzer_word_skip'])
        else:
            self.buzzer = StupidBuzzer()

        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.evidence = dict()

    def new_question(self, qid):
        self.buzzer.new_round()
        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.evidence = dict()

    def buzz(self, text, position):
        guesses = self.guesser.guess_single(text)
        if not isinstance(guesses, dict):
            guesses = {x[0]: x[1] for x in guesses}

        buzz_scores = [0, 1] # [wait, buzz]
        if self.ok_to_buzz:
            buzz_scores = self.buzzer.buzz(guesses)
            if isinstance(buzz_scores, np.ndarray):
                buzz_scores = buzz_scores.tolist()

        guesses = sorted(guesses.items(), key=lambda x: x[1])[::-1]
        self.guesses = guesses
        if len(guesses) > 0:
            self.answer = guesses[0][0]

        self.evidence = dict()
        self.highlighted, self.matches = get_matched(text)
        self.evidence = {'highlight': self.highlighted, 
                         'guesses': self.guesses,
                         'matches': self.matches}
        return buzz_scores

class CachedGuesserBuzzer:

    def __init__(self, record_dir):
        self.guesser_buzzer = GuesserBuzzer()
        with open(record_dir, 'rb') as f:
            self.cache = pickle.load(f)
        self.in_cache = False
        self.position = 0
        self.ok_to_buzz = True

    def new_question(self, qid):
        self.guesser_buzzer.new_question(qid)
        self.evidence = dict()
        self.position = 0
        self.qid = qid
        self.ok_to_buzz = True
        if self.qid in self.cache:
            self.in_cache = True
            self.record = self.cache[self.qid]
        print(self.in_cache)

    def buzz(self, text, position):
        self.position = position
        pos = position - 1
        if self.in_cache and pos in self.record:
            self.answer = self.record[pos]['answer']
            self.evidence = self.record[pos]['evidence']
            self.buzz_scores = self.record[pos]['buzz_scores']
        else:
            self.buzz_scores = self.guesser_buzzer.buzz(text, position)
            self.answer = self.guesser_buzzer.answer
            self.evidence = self.guesser_buzzer.evidence
        return self.buzz_scores if self.ok_to_buzz else [0, 1]

guesser_buzzer = CachedGuesserBuzzer('data/guesser_buzzer_cache.pkl')
# guesser_buzzer = GuesserBuzzer()

class GuesserBuzzerProtocol(PlayerProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''
        self.evidence = dict()

    def new_question(self, msg):
        self.text = ''
        self.position = 0
        guesser_buzzer.new_question(msg['qid'])
        self.evidence = dict()
        super(GuesserBuzzerProtocol, self).new_question(msg)

    def buzz(self):
        buzz_scores = guesser_buzzer.buzz(self.text, self.position) # [wait, buzz]
        self.answer = guesser_buzzer.answer
        self.evidence = guesser_buzzer.evidence
        buzzing = buzz_scores[0] > buzz_scores[1] # [wait, buzz]
        if buzzing:
            guesser_buzzer.ok_to_buzz = False
        return buzzing

    def update_question(self, msg):
        self.text = msg['text']
        self.position = msg['position']
        msg = {'qid': self.qid, 'position': self.position,
               'evidence': self.evidence,
               'helps': {'qanta': True}}
        if self.buzz():
            logger.info("\nBuzzing on answer: {}".format(self.answer))
            msg['type'] = MSG_TYPE_BUZZING_REQUEST
            msg['text'] = 'buzzing'
        else:
            msg['type'] = MSG_TYPE_RESUME
            msg['text'] = 'not buzzing'
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def send_answer(self, msg):
        logger.info('Answering: {}'.format(self.answer))
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'text': self.answer,
                'qid': self.qid, 'position': self.position,
                'helps': {'qanta': True}}
        self.sendMessage(json.dumps(msg).encode('utf-8'))


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://qbinterface.club:9000")
    factory.protocol = GuesserBuzzerProtocol
    connectWS(factory)
    reactor.run()
