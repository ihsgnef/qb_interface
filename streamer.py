import json
import time
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('streamer')

class StreamerProtocol(WebSocketClientProtocol):

    def onOpen(self):
        self.qid = None
        self.text = None
        self.position = 0
        self.length = 0

    def onClose(self, wasClean, code, reason):
        logger.warning('Connection closed')
        
    def new_question(self, msg):
        self.qid = msg['qid']
        self.text = msg['text']
        logger.info('')
        logger.info("New quetion qid: {}".format(self.qid))
        if isinstance(self.text, str):
            self.text = self.text.split()
        self.length = len(self.text)
        self.position = 0
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def update_question(self, msg):
        if msg['qid'] != self.qid:
            logger.error("Inconsistent qids: expect {}, received {}"\
                    .format(self.qid, msg['qid']))
            raise ValueError()
        if self.position < self.length:
            msg = {'type': MSG_TYPE_RESUME, 'text': self.text[self.position],
                    'qid': self.qid, 'position': self.position}
            print(msg['text'], end=' ', flush=True)
        else:
            msg = {'type': MSG_TYPE_END,
                    'qid': self.qid, 'position': self.position}
        self.position += 1
        self.sendMessage(json.dumps(msg).encode('utf-8'))

    def send_rest(self):
        logger.info('\nSending the rest of question')
        text = ' '.join(self.text[self.position:])
        self.position = self.length
        msg = {'type': MSG_TYPE_RESUME, 'text': text,
               'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg).encode('utf-8'))
        print(msg['text'], flush=True)
        print('--------')
            
    def onMessage(self, payload, isBinary):
        msg = json.loads(payload.decode('utf-8'))
        if msg['type'] == MSG_TYPE_NEW:
            if msg['qid'] != 0:
                self.new_question(msg)
        elif msg['type'] == MSG_TYPE_RESUME:
            reactor.callLater(0.3, self.update_question, msg)
        elif msg['type'] == MSG_TYPE_END:
            self.send_rest()

if __name__ == '__main__':
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = StreamerProtocol
    connectWS(factory)
    reactor.run()
