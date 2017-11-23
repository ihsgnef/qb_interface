import sys
import json
import time
import random
import logging
import traceback
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
SECOND_PER_WORD = 0.5
PLAYER_RESPONSE_TIME_OUT = 3

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
        self.questions = questions
        self.db = db
        self.loop = loop
        self.question_idx = -1
        logger.info('Loaded {} questions'.format(len(self.questions)))

        self.players = []
        self.player_responses = dict()
        self.player_scores = defaultdict(lambda: 0)
        self.player_buzzed = defaultdict(lambda: False)
        self.deferreds = []

        self.qid = 0
        self.position = 0
        self.evidence = dict()
        self.db_rows = dict()

    def register(self, client):
        if client not in self.players:
            self.players.append(client)
            msg = {'type': MSG_TYPE_NEW, 'qid': self.qid}
            client.sendMessage(json.dumps(msg).encode('utf-8'))
            self.db_rows[client.peer] = {
                    COL_QID: self.qid,
                    COL_UID: client.peer,
                    COL_START: self.position}
            logger.info("Registered player {}".format(client.peer))
        if len(self.players) == 1:
            self.new_question()
    
    def unregister(self, client):
        if client in self.players:
            logger.info("Unregistered player {}".format(client.peer))
            self.players.remove(client)

    def check_player_response(self, uid, key, value):
        return uid in self.player_responses and \
                key in self.player_responses[uid] and \
                self.player_responses[uid].get(key, None) == value

    def check_deferreds(self):
        ids = []
        for i, (deferred, cond) in enumerate(self.deferreds):
            if deferred.called:
                continue
            elif cond():
                deferred.callback(None)
            else:
                ids.append(i)
        self.deferreds = [self.deferreds[i] for i in ids]

    def receive(self, msg, client):
        try:
            msg = json.loads(msg.decode('utf-8'))
        except TypeError:
            logger.error("Message must be json string.")
            return
        if client in self.players:
            self.player_responses[client.peer] = msg
            if 'evidence' in  msg:
                self.evidence = msg['evidence']
            self.check_deferreds()
        else:
            logger.warning("Unknown source {}:\n{}".format(client, msg))

    def broadcast(self, players, msg):
        for p in players:
            p.sendMessage(json.dumps(msg).encode('utf-8'))

    
    def new_question(self):
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            if self.loop:
                random.shuffle(self.questions)
                self.question_idx = 0
            else:
                self._end_of_game()
                return
        
        self.question = self.questions[self.question_idx]
        self.qid = self.question['qid']
        self.question_text = self.question['text'].split()
        self.question_length = len(self.question_text)
        self.player_buzzed = defaultdict(lambda: False)
        self.position = 0
        self.evidence = dict()
        self.db_rows = dict()

        # notify all players of new question, wait for confirmation
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid, 
                'length': self.question_length}
        self.broadcast(self.players, msg)

        for player in self.players:
            def callback(x):
                logger.info('[new question] Player {} ready'.format(player.peer))
                self.db_rows[player.peer] = {
                    COL_QID: self.qid,
                    COL_UID: player.peer,
                    COL_START: 0}

            def errback(x):
                logger.warning('[new question] player {} timed out'\
                        .format(player.peer))
                self.unregister(player)

            condition = partial(self.check_player_response,
                    uid=player.peer, key='qid', value=self.qid)
            
            if condition():
                callback(None)
            else:
                deferred = Deferred()
                deferred.addTimeout(PLAYER_RESPONSE_TIME_OUT, reactor)
                deferred.addCallbacks(callback, errback)
                self.deferreds.append((deferred, condition))

        reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def stream_next(self):
        # send next word of the question to all players
        if self.position >= self.question_length:
            self._buzzing(end_of_question=True)
            return

        msg = {'type': MSG_TYPE_RESUME,  'qid': self.qid,
                'text': self.question_text[self.position],
                'position': self.position,
                'length': self.question_length,
                'evidence': self.evidence}
        self.position += 1
        self.broadcast(self.players, msg)
        if any(self.check_player_response(
                x.peer, 'type', MSG_TYPE_BUZZING_REQUEST)
                for x in self.players):
            self._buzzing()
        else:
            reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def stream_rest(self):
        # send rest of the question to all players
        msg = {'type': MSG_TYPE_RESUME,  'qid': self.qid,
                'length': self.question_length,
                'position': self.question_length - 1, 
                'text': ' '.join(self.question_text[self.position:])
                }
        self.position = self.question_length
        self.broadcast(self.players, msg)
        reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def _buzzing(self, end_of_question=False):
        buzzing_ids = []
        for i, player in enumerate(self.players):
            if self.player_buzzed[player.peer]:
                continue
            if end_of_question or self.check_player_response(
                    player.peer, 'type', MSG_TYPE_BUZZING_REQUEST):
                buzzing_ids.append(i)

        # if no one if buzzing
        if len(buzzing_ids) == 0:
            if end_of_question:
                self._end_of_question()
            return
        
        random.shuffle(buzzing_ids)
        buzzing_idx = buzzing_ids[0]
        logger.info('[buzzing] Player {} answering'.format(buzzing_idx))

        msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.qid, 
                'uid': buzzing_idx, 'length': ANSWER_TIME_OUT}
        red_players = self.players[:buzzing_idx] + self.players[buzzing_idx+1:]
        self.broadcast(red_players, msg)
        
        msg['type'] = MSG_TYPE_BUZZING_GREEN
        green_player = self.players[buzzing_idx]
        self.broadcast([green_player], msg)
        self.player_buzzed[green_player.peer] = True

        condition = partial(self.check_player_response, 
                green_player.peer, 'type', MSG_TYPE_BUZZING_ANSWER)

        def callback(x):
            self._buzzing_after(buzzing_idx, end_of_question, False)

        def errback(x):
            logger.warning('[buzzing] Player answer time out')
            self.player_responses[green_player.peer] = {
                    'type': MSG_TYPE_BUZZING_ANSWER,
                    'qid': self.qid, 'text': '_TIME_OUT_'}
            self._buzzing_after(buzzing_idx, end_of_question, True)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self.deferreds.append((deferred, condition))

    def _buzzing_after(self, buzzing_idx, end_of_question, timed_out):
        green_player = self.players[buzzing_idx]
        red_players = self.players[:buzzing_idx] + self.players[buzzing_idx+1:]
        answer = self.player_responses[green_player.peer]['text']
        position = self.player_responses[green_player.peer]['position']
        result = (answer == self.question['answer']) and not timed_out
        score = 10 if result else (0 if end_of_question else -5)
        self.db_rows[green_player.peer]['guess'] = {
                'position': self.position,
                'guess': answer,
                'result': result,
                'score': score}
        
        if not timed_out:
            logger.info('[buzzing] answer [{}] is {}'.format(answer, result))
        self.player_scores[green_player.peer] += score
        msg = {'type': MSG_TYPE_RESULT_MINE, 'qid': self.qid, 'result': result,
                'score': score,'uid': buzzing_idx, 'guess': answer}
        self.broadcast([green_player], msg)

        msg['type'] = MSG_TYPE_RESULT_OTHER
        self.broadcast(red_players, msg)

        if end_of_question or result:
            self._end_of_question()
        else:
            reactor.callLater(SECOND_PER_WORD * 2, self.stream_rest)

    def _end_of_question(self):
        msg = {'type': MSG_TYPE_END, 'qid': self.qid, 'text': '', 
                'evidence': {'answer': self.question['answer']}}
        self.broadcast(self.players, msg)
        try:
            for row in self.db_rows.values():
                self.db.add_row(row)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
        reactor.callLater(PLAYER_RESPONSE_TIME_OUT, self.new_question)
        

if __name__ == '__main__':
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
        random.shuffle(questions)

    db = QBDB()
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000", questions, db, loop=True)
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
