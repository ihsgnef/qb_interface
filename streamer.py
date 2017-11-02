import json
import time

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED

class StreamerProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = None
        self.position = 0
        self.length = 0
        
    def new_question(self, msg):
        print('[streamer]', msg['text'])
        self.qid = msg['qid']
        self.text = msg['text']
        if isinstance(self.text, str):
            self.text = self.text.split()
        self.length = len(self.text)
        self.position = 0
        self.sendMessage(json.dumps(msg).encode('utf-8'))
        print('[streamer] ready for question {}'.format(self.qid))

    def update_question(self, msg):
        if msg['qid'] != self.qid:
            raise ValueError("[streamer] inconsistent qids")
        if self.position < self.length:
            msg = {'type': MSG_TYPE_RESUME, 'text': self.text[self.position],
                    'qid': self.qid, 'position': self.position}
        else:
            msg = {'type': MSG_TYPE_END,
                    'qid': self.qid, 'position': self.position}
        self.position += 1
        self.sendMessage(json.dumps(msg).encode('utf-8'))
        print('sent', msg)

    def end_of_question(self):
        print('end of question')
        text = ' '.join(self.text[self.position:])
        self.position = self.length
        msg = {'type': MSG_TYPE_RESUME, 'text': text,
               'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg).encode('utf-8'))
            
    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf-8'))
        if msg['type'] == MSG_TYPE_NEW:
            self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            # TODO better sleeping mechanism
            reactor.callLater(1, self.update_question, msg)
        elif msg['type'] == MSG_TYPE_END:
            self.end_of_question()

if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = StreamerProtocol
    connectWS(factory)
    reactor.run()
