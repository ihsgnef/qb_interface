import sys
import json
import time
import select
import threading
import logging

from twisted.internet import reactor

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from client import PlayerProtocol
from util import MSG_TYPE_BUZZING_ANSWER
''' Listens to the user's keyboard for key presses that indicate a buzz'''

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('human_client')

buzzed = threading.Event()
buzzing_lock = threading.Lock()

class KeyboardProtocol(PlayerProtocol):

    def buzz(self):
        global buzzed
        buzzing = buzzed.is_set()
        buzzed.clear()
        return buzzing

    def send_answer(self, msg):
        logger.info('Answering: {}'.format(self.answer))
        buzzing_lock.acquire()
        i, o, e = select.select([sys.stdin], [], [], 5)
        if i:
            self.answer = sys.stdin.readline().strip()
        else:
            logger.info('Answering time out')
        buzzing_lock.release()
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'text': self.answer,
                'qid': self.qid, 'position': self.position}
        self.sendMessage(json.dumps(msg).encode('utf-8'))

class KeyPoller(threading.Thread):
    
    def run(self):
        global buzzed
        while True:
            with buzzing_lock:
                ch = sys.stdin.read(1)
                if ch == 'b':
                    buzzed.set()
            time.sleep(0.1)

if __name__ == '__main__':
    KeyPoller().start()
    factory = WebSocketClientFactory(u"ws://127.0.0.1:9000")
    factory.protocol = KeyboardProtocol
    connectWS(factory)
    reactor.run()