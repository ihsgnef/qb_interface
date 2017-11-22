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
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED, \
        MSG_TYPE_RESULT_MINE, MSG_TYPE_RESULT_OTHER
from db import QBDB
from db import COL_QID, COL_UID, COL_START, COL_GUESS, COL_HELPS

ANSWER_TIME_OUT = 8

logging.basicConfig(level=logging.INFO)
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

    def __init__(self, url, questions, db, loop=False):
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
        self.db = db
        self.question_idx = -1
        self.loop = loop
        logger.info('Loaded {} questions'.format(len(self.questions)))
        
        # a bunch of callbacks and their corresponding conditions
        self._deferreds = []
        # things to be broadcasted to all users
        self.evidence = dict()
        # rows to be written to DB
        self.rows = dict()

    def register(self, client):
        # assume that the first client is the streamer
        if self.streamer is None:
            self.streamer = client
            logger.info("Registered streamer {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 'qid': 0}
            self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))
            self.new_question()
        elif client not in self.users:
            self.users.append(client)
            logger.info("Registered user {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 'qid': 0}
            self.users[-1].sendMessage(json.dumps(msg).encode('utf-8'))
            self.rows[client.peer] = {COL_UID: client.peer, COL_QID: self.qid,
                    COL_START: self.position}

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
            if 'evidence' in msg:
                self.evidence = msg['evidence']
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
            self.position = msg['position']
            msg['evidence'] = self.evidence
            self.broadcast(self.users, msg)
            # if any one wants to buzz, check who wins the buzz
            if any([x['type'] == MSG_TYPE_BUZZING_REQUEST 
                for x in self.user_responses.values()]):
                self.handle_buzzing()
            else:
                self.resume_streamer()
        elif msg['type'] == MSG_TYPE_END:
            self.broadcast(self.users, msg)
            self.handle_buzzing(end_of_question=True)

    def new_question(self):
        # forward question index
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            if self.loop:
                random.shuffle(self.questions)
                self.question_idx = 0
            else:
                self.end_of_game()
                return

        self.question = self.questions[self.question_idx]
        self.question_length = len(self.question['text'].split())
        self.qid = self.question['qid']
        self.position = 0

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
                'text': 'new question', 
                'length': self.question_length}
        self.broadcast(self.users, msg)
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
            self.new_question_2()
            # if len(self._deferreds) == 0:
            #     logger.info('Starting question qid: {} (Answer: {})'\
            #             .format(self.qid, self.question['answer']))
            # else:
            #     logger.error('Cannot start game with {} deferreds'\
            #             .format(len(self._deferreds)))
        reactor.callLater(0.5, callback)

    def new_question_2(self):
        self.rows = {x.peer: {COL_UID: x.peer,
                              COL_QID: self.qid,
                              COL_START: 0}
                    for x in self.users}
        self.resume_streamer()

    def eoq_send_answer(self):
        msg = {'text': '', 'type': MSG_TYPE_END, 'qid': self.qid,
                'evidence': {'answer': self.question['answer']}}
        self.broadcast(self.users, msg)

    def handle_buzzing(self, end_of_question=False):
        buzzing_inds = []
        for i, user in enumerate(self.users):
            if self.buzzed[user.peer]:
                continue
            if end_of_question:
                buzzing_inds.append(i)
                continue
            if user.peer in self.user_responses and \
                    'type' in self.user_responses[user.peer]:
                rsp_type = self.user_responses[user.peer]['type']
                if rsp_type == MSG_TYPE_BUZZING_REQUEST:
                    buzzing_inds.append(i)

        if len(buzzing_inds) == 0:
            if end_of_question:
                self.eoq_send_answer()
            return

        random.shuffle(buzzing_inds)
        buzzing_idx = buzzing_inds[0]

        logger.info('[buzzing] Player {} answering'.format(buzzing_idx))

        red_msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.qid, 'uid':
                buzzing_idx, 'length': 8}
        red_users = self.users[:buzzing_idx] + self.users[buzzing_idx+1:]
        self.broadcast(red_users, red_msg)
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.qid, 'length': 8}
        green_user = self.users[buzzing_idx]
        green_user.sendMessage(json.dumps(green_msg).encode('utf-8'))

        self.buzzed[green_user.peer] = True

        condition = partial(self._check_user, green_user.peer, 
                'type', MSG_TYPE_BUZZING_ANSWER)
        callback = partial(self.handle_buzzing_ok, buzzing_idx, end_of_question)
        errback = partial(self.handle_buzzing_timeout, buzzing_idx, 
                end_of_question)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self._deferreds.append(
                    (deferred, condition, 'wait for user answer'))

    def handle_buzzing_ok(self, buzzing_idx, end_of_question, x):
        green_user = self.users[buzzing_idx]
        red_users = self.users[:buzzing_idx] + self.users[buzzing_idx+1:]
        response = self.user_responses[green_user.peer]
        answer = reponse['text']
        position = response['position']
        result = (answer == self.question['answer'])
        score = 10 if result else (0 if end_of_question else -5)
        self.rows[green_user.peer]['guess'] = {
                'position': max(self.position, position),
                'guess': answer,
                'result': result,
                'score': score}

        logger.info('[buzzing] answer [{}] is {}'.format(answer, result))
        self.scores[green_user.peer] += score
        msg = {'type': MSG_TYPE_RESULT_MINE, 'qid': self.qid, 'result': result,
                'score': score,'uid': buzzing_idx, 'guess': answer}
        self.broadcast([green_user], msg)

        msg['type'] = MSG_TYPE_RESULT_OTHER
        self.broadcast(red_users, msg)

        if end_of_question or result:
            self.eoq_send_answer()
            reactor.callLater(3, self.new_question)
        else:
            reactor.callLater(2, self.stop_streamer)

    def handle_buzzing_timeout(self, buzzing_idx, end_of_question, x):
        logger.warning('[buzzing] Player answer time out')
        green_user = self.users[buzzing_idx]
        red_users = self.users[:buzzing_idx] + self.users[buzzing_idx+1:]
        self.user_responses[green_user.peer] = {'type': MSG_TYPE_BUZZING_ANSWER,
                'qid': self.qid, 'text': '_TIME_OUT_'}
        _score = 0 if end_of_question else -5
        self.scores[green_user.peer] +=  _score
        msg = {'type': MSG_TYPE_RESULT_MINE, 'qid': self.qid, 'result': False,
                'score': _score, 'uid': buzzing_idx, 'guess': 'TIME OUT'}
        self.broadcast([green_user], msg)

        msg['type'] = MSG_TYPE_RESULT_OTHER
        self.broadcast(red_users, msg)

        if end_of_question:
            self.eoq_send_answer()
            reactor.callLater(3, self.new_question)
        else:
            reactor.callLater(2, self.stop_streamer)

    def resume_streamer(self):
        msg = {'type': MSG_TYPE_RESUME, 'qid': self.qid}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))
    
    def stop_streamer(self):
        msg = {'type': MSG_TYPE_END, 'qid': self.qid}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

    def end_of_game(self):
        logger.info('Final Score:')
        for user in self.users:
            logger.info('{}: {}'.format(user.peer, self.scores[user.peer]))

        self.unregister(self.streamer)
        for user in self.users:
            self.unregister(user)

    def broadcast(self, users, msg):
        for user in users:
            user.sendMessage(json.dumps(msg).encode('utf-8'))


if __name__ == '__main__':
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
        random.shuffle(questions)

    db = QBDB()
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000", questions,
            db, loop=True)
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
