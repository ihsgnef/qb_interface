import json
import pickle
import logging
import numpy as np
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, connectWS

from util import VIZ
from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, \
    MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
    MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
    MSG_TYPE_RESULT_MINE
from expected_wins import ExpectedWins

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')


class PlayerProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = 'Chubakka'
        self.buzzed = False
        self.enabled_viz = {t: False for t in VIZ}
        self.ew_score = ExpectedWins()
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
        self.enabled_viz = msg['enabled_viz']
        self.question = self.questions[self.qid]
        self.correct_answer = self.question.answer.replace('_', ' ')
        self.answer = 'Answer Placeholder'
        msg = {
            'type': MSG_TYPE_NEW,
            'qid': self.qid,
            'player_name': 'QANTA',
            'player_id': 'QANTA',
        }
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def buzz(self):
        if self.buzzed:
            return False

        if self.position > 10:
            if sum(self.enabled_viz.values()) > 1:
                self.answer = self.correct_answer
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


class SimulatedPlayerProtocol(PlayerProtocol):

    def onOpen(self):
        super().onOpen()
        self.weight = np.array([
            0.3,  # baseline
            0.21,  # guess
            0.18,  # highlight
            0.71,  # evidence
            0.21 + 0.18 + 0.025,  # guess + highlight
            0.21 + 0.71 - 0.08,  # guess + evidence
            0.18 + 0.71 - 0.02,  # highlight + evidence
            0.21 + 0.18 + 0.71 + 0.02  # everything
        ])

    def featurize(self) -> np.ndarray:
        viz = (
            + 1 * self.enabled_viz[VIZ[0]]
            + 2 * self.enabled_viz[VIZ[1]]
            + 4 * self.enabled_viz[VIZ[2]]
        )
        return np.array([
            1,  # baseline
            viz == 1,  # guess
            viz == 2,  # highlight
            viz == 3,  # evidence
            viz == 4,  # guess + highlight
            viz == 5,  # guess + evidence
            viz == 6,  # highlight + evidence
            viz == 7,  # all three
        ])

    def buzz(self):
        if self.buzzed:
            return False

        # get probability of correct from regression
        prob = 1 / (1 + np.exp(-self.weight @ self.featurize()))
        # back solve buzzing position
        buzzing_position = self.ew_score.solve(prob, self.question.length)

        if self.position > buzzing_position:
            if np.random.binomial(1, prob):
                self.answer = self.correct_answer
            return True
        else:
            return False


if __name__ == '__main__':
    # factory = WebSocketClientFactory(u"ws://play.qanta.org:9000")
    factory = WebSocketClientFactory(u"ws://localhost:9000")
    factory.protocol = SimulatedPlayerProtocol
    connectWS(factory)
    reactor.run()
