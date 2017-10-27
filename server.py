import sys
import json
import time
import random
from collections import defaultdict

from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from twisted.internet.defer import Deferred, \
    inlineCallbacks, \
    returnValue

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, \
    listenWS

from util import MSG_TYPE_NEW, MSG_TYPE_RESUME, MSG_TYPE_EOQ, \
        MSG_TYPE_BUZZING_REQUEST, MSG_TYPE_BUZZING_ANSWER, \
        MSG_TYPE_BUZZING_GREEN, MSG_TYPE_BUZZING_RED
from util import sleep

class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(msg, self)

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
            self.questions = json.loads(f.read())
        self.question_idx = -1

        print('[server] number of questions: {}'.format(len(self.questions)))

        self.sanity_check()

    def sanity_check(self):
        # TODO game start
        # self.new_question()
        pass
    
    def end_of_game(self):
        print('****** Game Over ******')
        print('Final Score:')
        for user in self.users:
            print(self.scores[user.peer])
        print('***********************')

        self.unregister(self.streamer)
        for user in self.users:
            self.unregister(user)

    @inlineCallbacks
    def new_question(self):
        # forward question index
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            self.end_of_game()
            return

        self.question = self.questions[self.question_idx]

        # notify streamer of a new question
        msg = {'type': MSG_TYPE_NEW, 'qid': self.question['qid'], 
                'text': self.questions['text']}
        self.streamer.sendMessage(json.dumps(msg))

        # verify that streamer is updated
        n_attempts = 0
        while n_attempts < 5:
            if not self._check_streamer('qid', self.question['qid']):
                yield sleep(1)
                n_attempts += 1
        else:
            print('[server] streamer cannot be updated')
            return

        # notify users of a new question
        self.user_responses = dict()
        msg = {'type': MSG_TYPE_NEW, 'qid': self.question['qid']}
        for user in self.users:
            user.sendMessage(json.dumps(msg))
            n_attempts = 0
            while n_attempts < 5:
                if user.peer not in self.user_responses or \
                        self.user_responses[user.peer] != self.question['qid']:
                    yield sleep(1)
                    n_attempts += 1
            else:
                print('[server] user {} cannot be updated'.format(user.peer))
                self.unregister(user)
        self.buzzed = defaultdict(lambda: False)

    def register(self, client):
        # assume that the first client is the streamer
        if self.streamer is None:
            print("[server] registered streamer {}".format(client.peer))
            self.streamer = client
        elif client not in self.users:
            print("[server] registered user {}".format(client.peer))
            self.user.append(client)
        # when reaches two users, wait and start game

    def unregister(self, client):
        if client == self.streamer:
            print("[server] unregistered streamer {}".format(client.peer))
            self.streamer = None
        elif client in self.users:
            print("[server] unregistered user {}".format(client.peer))
            self.users.remove(client)

    def _check_user(self, uid, key, value):
        if uid not in self.user_responses:
            return False
        if key not in self.user_responses[uid]:
            return False
        if self.user_responses[uid][key] != value:
            return False
        return True

    def _check_streamer(self, key, value):
        if self.streamer_response is None:
            return False
        if key not in self.streamer_response:
            return False
        if self.streamer_response[key] != value:
            return False
        return True
    
    @inlineCallbacks
    def receive_streamer_msg(self, msg):
        ''' main game logic here '''
        msg = json.loads(msg)
        self.streamer_response = msg
        if msg['type'] == MSG_TYPE_NEW:
            pass
        elif msg['type'] == MSG_TYPE_RESUME:
            # TODO
            # 0. include game state in message
            msg = json.dumps(msg)
            for user in self.users:
                user.sendMessage(json.dumps(msg))
                n_attempts = 0
                while n_attempts < 5:
                    if not self._check_user(
                            user.peer, 'qid', self.question['qid']):
                        yield sleep(1)
                        n_attempts += 1
                else:
                    print('[server] user {} cannot be updated'.format(user.peer))
                    self.unregister(user)
            # if any one wants to buzz, check who wins the buzz
            if any(x['type'] == MSG_TYPE_BUZZING_REQUEST for x in
                    self.user_responses):
                self.handle_buzzing()
            # 3. ask the streamer for another one
            msg = {'type': MSG_TYPE_RESUME, 'qid': self.question['qid']}
            self.streamer.sendMessage(json.dumps(msg))
        elif msg['type'] == MSG_TYPE_EOQ:
            self.handle_end_of_question()
            self.new_question()
            return

    @inlineCallbacks
    def handle_buzzing(self):
        # TODO
        buzzing_inds = []
        for i, user in enumerate(self.users):
            if self.buzzed[user.peer]:
                continue
            if self._check_user(user.peer, 'type', MSG_TYPE_BUZZING_REQUEST):
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
                user.sendMessage(json.dumps(red_msg))
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.question['qid']}
        b_user = users[buzzing_idx]
        b_user.sendMessage(json.dumps(green_msg))

        n_attempts = 0
        while n_attempts < 5:
            if not self._check_user(b_user.peer, 'type', MSG_TYPE_BUZZING_ANSWER):
                yield sleep(1)
                n_attempts += 1
        else:
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

        if terminate:
            self.new_question()
            return
        else:
            # TODO go directly to the end of question
            self.handle_end_of_question()
            return

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
                user.sendMessage(json.dumps(red_msg))
        
        green_msg = {'type': MSG_TYPE_BUZZING_GREEN, 'qid': self.question['qid']}
        b_user = users[buzzing_idx]
        b_user.sendMessage(json.dumps(green_msg))

        n_attempts = 0
        while n_attempts < 5:
            if not self._check_user(b_user.peer, 'type', MSG_TYPE_BUZZING_ANSWER):
                yield sleep(1)
                n_attempts += 1
        else:
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
        return

    def receive_user_msg(self, msg, user):
        msg = json.loads(msg)
        self.user_responses[user.peer] = msg

    def receive(self, msg, client):
        try:
            msg = json.loads(msg)
        except TypeError:
            print("[server] message must be json string")
            return
        
        if client == self.streamer:
            self.receive_streamer_msg(msg)
        elif client in self.users
            self.receive_user_msg(msg, client)
        else:
            print("[server] unknown source {}".format(client))
            print("[server] message: {}".format(msg))
