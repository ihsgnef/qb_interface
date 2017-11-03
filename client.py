import json
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = ''
        self.position = 0
        self.answer = ''

    def onClose(self, wasClean, code, reason):
        logger.warning('Connection closed')

    def new_question(self, msg):
        logger.info('New question')
        self.qid = msg['qid']
        self.text = ''
        self.position = 0
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid}
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def buzz(self):
        self.answer = 'Chubakka'
        return self.position > 5

    def update_question(self, msg):
        print(msg['text'], end=' ', flush=True)
        self.text += ' ' + msg['text']
        if self.buzz():
            logger.info("\nBuzzing on answer: {}".format(self.answer))
            msg = {'type': MSG_TYPE_BUZZING_REQUEST, 'text': 'buzzing',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg).encode('utf-8'))
        else:
            msg = {'type': MSG_TYPE_RESUME, 'text': 'not buzzing',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg).encode('utf-8'))
        self.position += 1

    def send_answer(self, msg):
        logger.info('Answering: {}'.format(self.answer))
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'text': self.answer,
                'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf-8'))
        if msg['type'] == MSG_TYPE_NEW:
            # a new question
            if msg['qid'] != 0:
                self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            # update question text
            self.update_question(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_GREEN:
            # won buzzing, provide answer now
            self.send_answer(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_RED:
            # did not win buzzing, cannot answer
            logger.info('Did not win buzz')
        elif msg['type'] == MSG_TYPE_BUZZING_ANSWER:
            # result of answer
            result = 'correct' if msg['text'] else 'wrong'
            logger.info('Answer is {}'.format(result))


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = UserProtocol
    connectWS(factory)
    reactor.run()
