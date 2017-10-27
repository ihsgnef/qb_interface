import json

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_EOQ, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED

class UserProtocol(WebSocketClientProtocol):

    def onOpen(self):
        # TODO initialize model
        self.qid = None
        self.text = ''
        self.position = 0

    def new_question(self, msg):
        self.qid = msg['qid']
        self.text = ''
        self.position = 0
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid}
        self.sendMessage(json.dumps(msg))

    def buzz(self):
        return self.position > 10

    def update_question(self, msg):
        self.position += 1
        self.text += msg['text']
        if self.buzz():
            msg = {'type': MSG_TYPE_BUZZING_REQUEST, 'text': 'buzzing',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg))
        else:
            msg = {'type': MSG_TYPE_RESUME, 'text': 'no answer',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg))

    def send_answer(self, msg):
        print('[player] answering')
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'text': 'answer',
                'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg))

    def onMessage(self, payload, isBinary):
        msg = json.loads(payload)
        if msg['type'] == MSG_TYPE_NEW:
            self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            self.update_question(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_GREEN:
            # I'm buzzing, send answer
            self.send_answer(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_RED:
            pass
