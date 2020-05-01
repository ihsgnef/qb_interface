import json
import pickle
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, \
    MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
    MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
    MSG_TYPE_RESULT_MINE
from util import QBQuestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')

TOOLS = ['guesses', 'highlight', 'matches']

class PlayerProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''
        self.buzzed = False
        self.enabled_tools = {t: False for t in TOOLS}
        with open('data/pace_questions.pkl', 'rb') as f:
            self.questions = pickle.load(f)
            self.questions = {x.qid: x for x in self.questions}

    def onClose(self, wasClean, code, reason):
        logger.warning('Connection closed')

    def new_question(self, msg):
        logger.info('')
        logger.info('New question')
        self.qid = msg['qid']
        self.text = ''
        self.position = 0
        self.buzzed = False
        self.enabled_tools = msg['enabled_tools']
        msg = {
            'type': MSG_TYPE_NEW,
            'qid': self.qid,
            'player_name': 'QANTA',
            'player_id': 'QANTA',
        }
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def buzz(self):
        self.answer = 'Chubakka'
        if self.buzzed:
            return False

        if self.position > 10:
            if sum(self.enabled_tools.values()) > 1:
                self.answer = self.questions[self.qid].answer.replace('_', ' ')
            return True
        else:
            return False

    def update_question(self, msg):
        if 'text' not in msg:
            return
        print(msg['text'].split()[-1], end=' ', flush=True)
        self.text += ' ' + msg['text']
        if self.buzz():
            logger.info("\nBuzzing on answer: {}".format(self.answer))
            msg = {
                'type': MSG_TYPE_BUZZING_REQUEST,
                'text': 'buzzing',
                'qid': self.qid,
                'position': self.position
            }
            self.sendMessage(json.dumps(msg).encode('utf-8'))
            self.buzzed = True
        else:
            msg = {
                'type': MSG_TYPE_RESUME,
                'text': 'not buzzing',
                'qid': self.qid,
                'position': self.position
            }
            self.sendMessage(json.dumps(msg).encode('utf-8'))
        self.position += 1

    def send_answer(self, msg):
        logger.info('Answering: {}'.format(self.answer))
        msg = {
            'type': MSG_TYPE_BUZZING_ANSWER,
            'text': self.answer,
            'qid': self.qid,
            'position': self.position
        }
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf-8'))
        if msg['type'] == MSG_TYPE_NEW:
            if msg['qid'] != 0:
                self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            self.update_question(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_GREEN:
            self.send_answer(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_RED:
            logger.info('Not buzzing')
        elif msg['type'] == MSG_TYPE_RESULT_MINE:
            result = 'correct' if msg['result'] else 'wrong'
            logger.info('Answer is {}'.format(result))


if __name__ == '__main__':
    # factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory = WebSocketClientFactory(u"ws://play.qanta.org:9000")
    factory.protocol = PlayerProtocol
    connectWS(factory)
    reactor.run()
