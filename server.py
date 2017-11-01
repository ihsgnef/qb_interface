import sys
import json
import time
import random
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

def sleep(delay):
    d = Deferred()
    reactor.callLater(delay, d.callback, None)
    return d

class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(payload, self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.streamer = None
        self.users = []
        # latest response from the streamer
        self.streamer_response = None
        # latest responses from users
        self.user_responses = dict()

        self.scores = defaultdict(lambda: 0)
        self.buzzed = defaultdict(lambda: False)

        with open('sample_questions.json', 'r') as f:
            self.questions = json.loads(f.read())[:1]
        self.question_idx = -1

        print('[server] number of questions: {}'.format(len(self.questions)))
        
        # a bunch of callbacks and their corresponding conditions
        self._deferreds = []

    def end_of_game(self):
        print('****** Game Over ******')
        print('Final Score:')
        for user in self.users:
            print(self.scores[user.peer])
        print('***********************')

        self.unregister(self.streamer)
        for user in self.users:
            self.unregister(user)

    def _check_streamer(self, key, value, wait=5):
        if self.streamer_response is None or \
                key not in self.streamer_response or \
                self.streamer_response[key] != value:
            return False
        else:
            return True

    def new_question(self):
        self._new_question_0()

    def _new_question_0(self):
        print('new question 0')
        # forward question index
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            self.end_of_game()
            return

        self.question = self.questions[self.question_idx]

        # notify streamer of a new question
        msg = {'type': MSG_TYPE_NEW, 'qid': self.question['qid'], 
                'text': self.question['text']}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

        def callback(x):
            print('[server] streamer check passed')
            self._new_question_1()

        condition = partial(self._check_streamer, 'qid', self.question['qid'])
        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(3, reactor)
            deferred.addCallbacks(callback,
                    lambda x: print('[server] streamer timed out'))
            self._deferreds.append((deferred, condition, 'streamer check'))

    def _new_question_1(self):
        print('[server] new question 1')
        msg = {'type': MSG_TYPE_NEW, 'qid': self.question['qid'], 
                'text': 'new question 1'}
        for user in self.users:
            user.sendMessage(json.dumps(msg).encode('utf-8'))
        self.buzzed = defaultdict(lambda: False)

        _qid = self.question['qid']
        try:
            for user in self.users:
                def callback(x):
                    print('[server] user {} ready'.format(user.peer))
                
                def errback(x):
                    print('[server] user {} timed out'.format(user.peer))
                    self.unregister(user)

                condition = partial(self._check_user, user.peer, 'qid', _qid)

                if condition():
                    callback(None)
                else:
                    deferred = Deferred()
                    deferred.addTimeout(3, reactor)
                    deferred.addCallbacks(callback, errback)
                    self._deferreds.append((deferred, condition, 'user check'))
        except Exception as e:
            print(e)

        condition = lambda: len(self._deferreds) == 1
        def callback():
            if len(self._deferreds) == 0:
                print('[server] starting game')
                self._new_question_2()
            else:
                print('[server] cannot start game')
        reactor.callLater(3, callback)

    def _new_question_2(self):
        print('[server] new question 2')
        msg = {'type': MSG_TYPE_RESUME, 'qid': self.question['qid']}
        self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

    def register(self, client):
        # assume that the first client is the streamer
        if self.streamer is None:
            self.streamer = client
            print("[server] registered streamer {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 'text': 'Welcome, streamer',
                    'qid': 0}
            self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))

        elif client not in self.users:
            self.users.append(client)
            print("[server] registered user {}".format(client.peer))
            msg = {'type': MSG_TYPE_NEW, 
                    'text': 'Welcome, player {}'.format(len(self.users) - 1),
                    'qid': 0}
            self.users[-1].sendMessage(json.dumps(msg).encode('utf-8'))
        if len(self.users) > 0:
            self.new_question()

    def unregister(self, client):
        if client == self.streamer:
            print("[server] unregistered streamer {}".format(client.peer))
            self.streamer = None
        elif client in self.users:
            print("[server] unregistered user {}".format(client.peer))
            self.users.remove(client)

    def _check_user(self, uid, key, value, wait=5):
        if uid not in self.user_responses or \
                key not in self.user_responses[uid] or \
                self.user_responses[uid][key] != value:
            return False
        else:
            return True

    def receive_streamer_msg(self, msg):
        if msg['type'] == MSG_TYPE_RESUME:
            for user in self.users:
                print('sent to user', user.peer)
                user.sendMessage(json.dumps(msg).encode('utf-8'))
            '''
            # TODO
            # 0. include game state in message
                user_check = yield self._check_user(
                        user.peer, 'qid', self.question['qid'])
                if not user_check:
                    print('[server] user {} cannot be updated'.format(user.peer))
                    self.unregister(user)
            # if any one wants to buzz, check who wins the buzz
            if any(x['type'] == MSG_TYPE_BUZZING_REQUEST for x in
                    self.user_responses):
                terminate = self.handle_buzzing()
                if not terminate:
                    self.handle_end_of_question()
                    self.new_question()
            # 3. ask the streamer for another one
            msg = {'type': MSG_TYPE_RESUME, 'qid': self.question['qid']}
            self.streamer.sendMessage(json.dumps(msg).encode('utf-8'))
            '''
        '''
        elif msg['type'] == MSG_TYPE_END:
            self.handle_end_of_question()
            self.new_question()
        '''

    def handle_buzzing(self):
        # TODO
        buzzing_inds = []
        for i, user in enumerate(self.users):
            if self.buzzed[user.peer]:
                continue
            # user_check = yield self._check_user(
            #         user.peer, 'type', MSG_TYPE_BUZZING_REQUEST)
            # if user_check:
            #     buzzing_inds.append(i)
            if self.user_responses[user.peer]['type'] == MSG_TYPE_BUZZING_REQUEST:
                buzzing_inds.append(i)


        if len(buzzing_inds) == 0:
            return

        # TODO do we need to verify buzzing positions here?
        random.shuffle(buzzing_inds)
        buzzing_idx = buzzing_inds[0]

        print('[server] player {} please provide answer'.format(buzzing_idx))
        
        red_msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.question['qid']}
        for i, user in enumerate(self.users):
            if i != buzzing_idx:
                user.sendMessage(json.dumps(red_msg).encode('utf-8'))
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.question['qid']}
        b_user = users[buzzing_idx]
        b_user.sendMessage(json.dumps(green_msg).encode('utf-8'))

        user_check = yield self._check_user(b_user.peer, 'type', MSG_TYPE_BUZZING_ANSWER)
        if not user_check:
            print('[server] player {} did not answer in time'.format(buzzing_idx))
            return

        # evaluation
        terminate = False
        self.buzzed[b_user.peer] = True
        answer = self.user_responses[b_user.peer]
        if answer == self.question['answer']:
            print('[server] answer is correct')
            self.scores[b_user.peer] += 10
            terminate = True
        else:
            print('[server] answer is wrong')
            self.scores[b_user.peer] -= 5

        return terminate

    def handle_end_of_question(self):
        # TODO update states to the end of question
        
        buzzing_inds = []
        for i, user in enumerate(users):
            if self.buzzed[user.peer] is False:
                buzzing_inds.append(i)

        if len(buzzing_inds) == 0:
            return

        random.shuffle(buzzing_inds)
        buzzing_idx = buzzing_inds[0]

        print('[server] player {} please provide answer'.format(buzzing_idx))
        
        red_msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.question['qid']}
        for i, user in enumerate(self.users):
            if i != buzzing_idx:
                user.sendMessage(json.dumps(red_msg).encode('utf-8'))
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.question['qid']}
        b_user = users[buzzing_idx]
        b_user.sendMessage(json.dumps(green_msg).encode('utf-8'))

        user_check = yield self._check_user(b_user.peer, 'type', MSG_TYPE_BUZZING_ANSWER)
        if not user_check:
            print('[server] player {} did not answer in time'.format(buzzing_idx))
            return

        # evaluation
        self.buzzed[b_user.peer] = True
        answer = self.user_responses[b_user.peer]
        if answer == self.question['answer']:
            print('[server] answer is correct')
            self.scores[b_user.peer] += 10
            terminate = True
        else:
            print('[server] answer is wrong')

        self.new_question()

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

    def receive(self, msg, client):
        try:
            msg = json.loads(msg.decode('utf-8'))
        except TypeError:
            print("[server] message must be json string")
            return
        
        if client == self.streamer:
            self.streamer_response = msg
            self.check_deferreds()
            self.receive_streamer_msg(msg)
        elif client in self.users:
            self.user_responses[client.peer] = msg
            self.check_deferreds()
        else:
            print("[server] unknown source {}".format(client))
            print("[server] message: {}".format(msg))

if __name__ == '__main__':
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000")
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
