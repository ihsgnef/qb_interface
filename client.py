import json

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED

class UserProtocol(WebSocketClientProtocol):

    def onOpen(self):
        # TODO initialize model
        self.qid = None
        self.text = ''
        self.position = 0

    def new_question(self, msg):
        print('[user] new question')
        print('[user]', msg['text'])
        self.qid = msg['qid']
        self.text = ''
        self.position = 0
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid}
        self.sendMessage(json.dumps(msg).encode('utf-8'))
        print('[user] ready for question {}'.format(self.qid))

    def buzz(self):
        return self.position > 10

    def update_question(self, msg):
        self.position += 1
        print(msg['text'])
        self.text += msg['text']
        '''
        if self.buzz():
            msg = {'type': MSG_TYPE_BUZZING_REQUEST, 'text': 'buzzing',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg).encode('utf-8'))
        else:
            msg = {'type': MSG_TYPE_RESUME, 'text': 'no answer',
                    'qid': self.qid, 'position': self.position}
            self.sendMessage(json.dumps(msg).encode('utf-8'))
        '''

    def send_answer(self, msg):
        print('[player] answering')
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'text': 'answer',
                'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf-8'))
        if msg['type'] == MSG_TYPE_NEW:
            self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            self.update_question(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_GREEN:
            # I'm buzzing, send answer
            self.send_answer(msg)
        elif msg['type'] == MSG_TYPE_BUZZING_RED:
            pass


if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = UserProtocol
    connectWS(factory)
    reactor.run()
