import json
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, \
    MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
    MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
    MSG_TYPE_RESULT_MINE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')

class PlayerProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''

    def onClose(self, wasClean, code, reason):
        logger.warning('Connection closed')

    def new_question(self, msg):
        logger.info('')
        logger.info('New question')
        self.qid = msg['qid']
        self.text = ''
        self.position = 0
        msg = {
            'type': MSG_TYPE_NEW,
            'qid': self.qid,
            'is_machine': True,
            'player_name': 'QANTA'
        }
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def buzz(self):
        self.answer = 'Chubakka'
        return self.position > 5

    def update_question(self, msg):
        print(msg['text'], end=' ', flush=True)
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
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = PlayerProtocol
    connectWS(factory)
    reactor.run()
