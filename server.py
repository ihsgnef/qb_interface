import sys
import json
import time
import random
import logging
from threading import Thread
from functools import partial
from collections import defaultdict

from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from twisted.internet.defer import Deferred, inlineCallbacks

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, listenWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_END, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('server')

class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(payload, self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url, questions):
        WebSocketServerFactory.__init__(self, url)
        self.streamer = None
        self.users = []
        # latest response from the streamer
        self.streamer_response = None
        # latest responses from users
        self.user_responses = dict()

        self.scores = defaultdict(lambda: 0)
        self.buzzed = defaultdict(lambda: False)

        self.questions = questions
        self.question_idx = -1
        logger.info('Loaded {} questions'.format(len(self.questions)))
        
        # a bunch of callbacks and their corresponding conditions
        self._deferreds = []

    def register(self, client):
        # assume that the first client is the streamer
        if self.streamer is None:
            self.streamer = client
            logger.info("Registered streamer {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 'text': 'Welcome, streamer',
                    'qid': 0}
            self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

        elif client not in self.users:
            self.users.append(client)
            logger.info("Registered user {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 'qid': 0,
                    'text': 'Welcome, player {}'.format(len(self.users) - 1)}
            self.users[-1].sendMessage(json.dumps(msg).encode('utf-8'))
        if len(self.users) > 0:
            self.new_question()

    def unregister(self, client):
        if client == self.streamer:
            logger.info("Unregistered streamer {}".format(client.peer))
            self.streamer = None
        elif client in self.users:
            logger.info("Unregistered user {}".format(client.peer))
            self.users.remove(client)

    def _check_user(self, uid, key, value):
        if uid not in self.user_responses or \
                key not in self.user_responses[uid] or \
                self.user_responses[uid][key] != value:
            return False
        else:
            return True

    def _check_streamer(self, key, value):
        if self.streamer_response is None or \
                key not in self.streamer_response or \
                self.streamer_response[key] != value:
            return False
        else:
            return True

    def receive(self, msg, client):
        try:
            msg = json.loads(msg.decode('utf-8'))
        except TypeError:
            logger.error("Message must be json string.")
            return
        
        if client == self.streamer:
            self.streamer_response = msg
            self.check_deferreds()
            self.receive_streamer_msg(msg)
        elif client in self.users:
            self.user_responses[client.peer] = msg
            self.check_deferreds()
        else:
            logger.warning("Unknown source {}:\n{}".format(client, msg))

    def check_deferreds(self):
        keep_ids = []
        for i, (deferred, cond, info) in enumerate(self._deferreds):
            if deferred.called:
                continue
            elif cond():
                deferred.callback(None)
            else:
                keep_ids.append(i)
        self._deferreds = [self._deferreds[i] for i in keep_ids]

    def receive_streamer_msg(self, msg):
        if msg['type'] == MSG_TYPE_RESUME:
            for user in self.users:
                user.sendMessage(json.dumps(msg).encode('utf-8'))
            # if any one wants to buzz, check who wins the buzz
            if any([x['type'] == MSG_TYPE_BUZZING_REQUEST 
                for x in self.user_responses.values()]):
                self.handle_buzzing()
            else:
                msg = {'type': MSG_TYPE_RESUME, 'qid': self.qid}
                self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))
        elif msg['type'] == MSG_TYPE_END:
            self.new_question()

    def new_question(self):
        self.new_question_0()

    def new_question_0(self):
        # forward question index
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            self.end_of_game()
            return

        self.question = self.questions[self.question_idx]
        self.qid = self.question['qid']

        # notify streamer of a new question
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid, 
                'text': self.question['text']}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

        def callback(x):
            self.new_question_1()

        def errback(x):
            logger.warning('[new question] streamer timed out')

        condition = partial(self._check_streamer, 'qid', self.qid)
        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(3, reactor)
            deferred.addCallbacks(callback, errback)
            self._deferreds.append((deferred, condition, 'streamer check'))

    def new_question_1(self):
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid, 
                'text': 'new question'}
        for user in self.users:
            user.sendMessage(json.dumps(msg).encode('utf-8'))
        self.buzzed = defaultdict(lambda: False)

        for user in self.users:
            def callback(x):
                logger.info('[new question] User {} ready'.format(user.peer))
            
            def errback(x):
                logger.warning('[new question] user {} timed out'\
                        .format(user.peer))
                self.unregister(user)

            condition = partial(self._check_user, user.peer, 'qid', self.qid)

            if condition():
                callback(None)
            else:
                deferred = Deferred()
                deferred.addTimeout(3, reactor)
                deferred.addCallbacks(callback, errback)
                self._deferreds.append((deferred, condition, 'user check'))

        condition = lambda: len(self._deferreds) == 1
        def callback():
            if len(self._deferreds) == 0:
                logger.info('Starting question qid: {} (Answer: {})'\
                        .format(self.qid, self.question['answer']))
                self.new_question_2()
            else:
                logger.error('Cannot start game with {} deferreds'\
                        .format(len(self._deferreds)))
        reactor.callLater(3, callback)

    def new_question_2(self):
        msg = {'type': MSG_TYPE_RESUME, 'qid': self.qid,
                'text': 'streamer new question start'}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

    def handle_buzzing(self):
        self.handle_buzzing_0()

    def handle_buzzing_0(self):
        buzzing_inds = []
        for i, user in enumerate(self.users):
            if self.buzzed[user.peer]:
                continue
            if self.user_responses[user.peer]['type'] == MSG_TYPE_BUZZING_REQUEST:
                buzzing_inds.append(i)

        if len(buzzing_inds) == 0:
            return

        random.shuffle(buzzing_inds)
        buzzing_idx = buzzing_inds[0]

        logger.info('[buzzing] Player {} answering'.format(buzzing_idx))

        red_msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.qid}
        for i, user in enumerate(self.users):
            if i != buzzing_idx:
                user.sendMessage(json.dumps(red_msg).encode('utf-8'))
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.qid}
        b_user = self.users[buzzing_idx]
        b_user.sendMessage(json.dumps(green_msg).encode('utf-8'))

        self.buzzed[b_user.peer] = True

        condition = partial(self._check_user, b_user.peer, 
                'type', MSG_TYPE_BUZZING_ANSWER)
        callback = partial(self.handle_buzzing_1, b_user)
        errback = partial(self.handle_buzzing_2, b_user)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(5, reactor)
            deferred.addCallbacks(callback, errback)
            self._deferreds.append(
                    (deferred, condition, 'wait for user answer'))

    def handle_buzzing_1(self, b_user, x):
        answer = self.user_responses[b_user.peer]['text']
        if answer == self.question['answer']:
            logger.info('[buzzing] answer [{}] is correct'.format(answer))
            self.scores[b_user.peer] += 10
            msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'qid': self.qid, 'text': True}
            b_user.sendMessage(json.dumps(msg).encode('utf-8'))
        else:
            logger.info('[buzzing] answer [{}] is wrong'.format(answer))
            self.scores[b_user.peer] -= 5
            msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'qid': self.qid, 'text': False}
            b_user.sendMessage(json.dumps(msg).encode('utf-8'))
        msg = {'type': MSG_TYPE_END}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

    def handle_buzzing_2(self, b_user, x):
        logger.warning('[buzzing] Player answer time out')
        self.user_responses[b_user.peer] = {'type': MSG_TYPE_BUZZING_ANSWER,
                'qid': self.qid, 'text': '_TIME_OUT_'}
        self.scores[b_user.peer] -= 5
        msg = {'type': MSG_TYPE_BUZZING_ANSWER, 'qid': self.qid, 'text': False}
        b_user.sendMessage(json.dumps(msg).encode('utf-8'))
        msg = {'type': MSG_TYPE_END}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

    def end_of_game(self):
        logger.info('Final Score:')
        for user in self.users:
            logger.info('{}: {}'.format(user.peer, self.scores[user.peer]))

        self.unregister(self.streamer)
        for user in self.users:
            self.unregister(user)


if __name__ == '__main__':
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
        random.shuffle(questions)
        questions = questions[:10]

    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000", questions)
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
