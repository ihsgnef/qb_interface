import sys
import json
import time
import random
import pickle
import logging
import traceback
import datetime
from tqdm import tqdm
from threading import Thread
from functools import partial
from collections import defaultdict
from haikunator import Haikunator

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
from db import COL_QID, COL_UID, COL_START, COL_GUESS, COL_HELPS,\
        COL_TIME

ANSWER_TIME_OUT = 10
SECOND_PER_WORD = 0.5
PLAYER_RESPONSE_TIME_OUT = 3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')

haikunator = Haikunator()

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

        self.players = dict()
        self.player_names = dict()
        self.player_alive = dict()
        self.player_is_machine = dict()
        self.player_responses = dict()
        self.player_scores = dict()
        self.player_buzzed = defaultdict(lambda: False)

        self.deferreds = []

        self.started = False
        self.qid = 0
        self.position = 0
        self.disable_machine_buzz = False
        self.evidence = dict()
        self.db_rows = dict()
        with open('data/guesser_buzzer_cache.pkl', 'rb') as f:
            self.records = pickle.load(f)
        # when we unregister a player, wait until the end
        # of the round to remove it from the list of players
        # this list keeps track of the players that are actually active


    def get_time(self):
        ts = time.time()
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    def register(self, player):
        if player.peer not in self.players:
            self.players[player.peer] = player
            name = haikunator.haikunate(token_length=0, delimiter=' ').title()
            self.player_names[player.peer] = name
            msg = {'type': MSG_TYPE_NEW, 'qid': self.qid, 'player_name': name,
                    'player_list': self.get_player_list()}
            player.sendMessage(json.dumps(msg).encode('utf-8'))
            self.db_rows[player.peer] = {
                    COL_QID: self.qid,
                    COL_UID: player.peer,
                    COL_START: self.position,
                    COL_TIME: self.get_time()}
            self.player_alive[player.peer] = True
            self.player_is_machine[player.peer] = False
            self.player_scores[player.peer] = 0
            logger.info("Registered player {}".format(player.peer))

        if len(self.players) == 1 and not self.started:
            self.started = True
            self.new_question()
    
    def unregister(self, player_id):
        if player_id in self.players:
            logger.info("Unregistered player {}".format(player_id))
            self.player_alive[player_id] = False

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

    def receive(self, msg, player):
        try:
            msg = json.loads(msg.decode('utf-8'))
        except TypeError:
            logger.error("Message must be json string.")
            return
        if player.peer in self.players:
            self.player_responses[player.peer] = msg
            # if 'evidence' in  msg:
            #     self.evidence = msg['evidence']
            self.check_deferreds()
        else:
            logger.warning("Unknown source {}:\n{}".format(player.peer, msg))

    def broadcast(self, players_dict, msg):
        for pid, pclient in players_dict.items():
            if self.player_alive[pid]:
                pclient.sendMessage(json.dumps(msg).encode('utf-8'))
    
    def new_question(self):
        self.question_idx += 1
        if self.question_idx >= len(self.questions):
            if self.loop:
                random.shuffle(self.questions)
                self.question_idx = 0
            else:
                self._end_of_game()
                return
        
        self.player_responses.clear()
        self.disable_machine_buzz = False
        self.question = self.questions[self.question_idx]
        self.question['answer'] = self.question['answer'].replace('_', ' ')
        self.qid = self.question['qid']
        self.question_text = self.question['text'].split()
        self.question_length = len(self.question_text)
        self.player_buzzed = defaultdict(lambda: False)
        self.position = 0
        self.evidence = dict()
        ts = self.get_time()
        self.db_rows = {x: {
                    COL_QID: self.qid,
                    COL_UID: x,
                    COL_START: 0,
                    COL_TIME: ts} for x in self.players}

        # notify all players of new question, wait for confirmation
        msg = {'type': MSG_TYPE_NEW, 'qid': self.qid, 
                'length': self.question_length, 'position': 0,
                'player_list': self.get_player_list()}
        self.broadcast(self.players, msg)

        def make_callback(pid):
            def f(x):
                logger.info('[new question] Player {} ready'.format(pid))
            return f

        def make_errback(pid):
            def f(x):
                logger.info('[new] player {} timed out'.format(pid))
                self.unregister(pid)
            return f


        for pid in self.players:
            condition = partial(self.check_player_response,
                    uid=pid, key='qid', value=self.qid)
            callback = make_callback(pid)
            errback = make_errback(pid)
            
            if condition():
                callback(None)
            else:
                deferred = Deferred()
                deferred.addTimeout(PLAYER_RESPONSE_TIME_OUT, reactor)
                deferred.addCallbacks(callback, errback)
                self.deferreds.append((deferred, condition))

        def calllater():
            for pid in self.players:
                logger.info("Player {} score {}".format(
                    pid, self.player_scores[pid]))
                if self.check_player_response(pid, 
                        'disable_machine_buzz', True):
                    self.disable_machine_buzz = True
                if self.check_player_response(pid, 
                        'is_machine', True):
                    self.player_is_machine[pid] = True
                
            self.pbar = tqdm(total=self.question_length, leave=False)
            self.stream_next()

        reactor.callLater(SECOND_PER_WORD, calllater)

    def stream_next(self):
        # send next word of the question to all players
        end_of_question = self.position >= self.question_length

        buzzing_ids = []
        for pid in self.players:
            if not self.player_alive[pid]:
                continue
            if self.player_buzzed[pid]:
                continue
            if self.disable_machine_buzz and self.player_is_machine[pid]:
                continue
            if end_of_question or self.check_player_response(
                    pid, 'type', MSG_TYPE_BUZZING_REQUEST):
                buzzing_ids.append(pid)

        # if no one if buzzing
        if len(buzzing_ids) > 0:
            self._buzzing(buzzing_ids, end_of_question)
        else:
            if end_of_question:
                self._end_of_question()
            else:
                self.evidence = dict()
                if self.qid in self.records:
                    record = self.records[self.qid]
                    if self.position in record:
                        self.evidence = record[self.position]['evidence']
                        for i, (g, s) in enumerate(self.evidence['guesses']):
                            self.evidence['guesses'][i] = (g.replace('_', ' '), s)

                self.position += 1

                msg = {'type': MSG_TYPE_RESUME,  'qid': self.qid,
                        'text': ' '.join(self.question_text[:self.position]),
                        'position': self.position,
                        'length': self.question_length,
                        'evidence': self.evidence,
                        'player_list': self.get_player_list()}
                self.pbar.update(1)
                self.broadcast(self.players, msg)
                reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def stream_rest(self):
        # send rest of the question to all players
        self.position = self.question_length
        msg = {'type': MSG_TYPE_RESUME,  'qid': self.qid,
                'length': self.question_length,
                'position': self.position,
                'text': ' '.join(self.question_text[:self.position]),
                'player_list': self.get_player_list()
                }
        self.broadcast(self.players, msg)
        reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def get_player_list(self):
        plys = sorted(self.player_scores.items(), key=lambda x: x[1])[::-1]
        for i, (x, s) in enumerate(plys):
            if not self.player_alive(x):
                continue
            name = self.player_names[x]
            if self.player_is_machine[x]:
                name += ' (machine)'
            plys[i] = (self.player_names[x], s)
        return plys

    def _buzzing(self, buzzing_ids, end_of_question):
        random.shuffle(buzzing_ids)
        buzzing_id = buzzing_ids[0]
        logger.info('[buzzing] Player {} answering'.format(buzzing_id))

        msg = {'type': MSG_TYPE_BUZZING_RED, 'qid': self.qid, 
                'uid': buzzing_id, 'player_name': self.player_names[buzzing_id],
                'length': ANSWER_TIME_OUT,
                'player_list': self.get_player_list()}
        red_players = {k: v for k, v in self.players.items() if k != buzzing_id}
        self.broadcast(red_players, msg)
        
        msg['type'] = MSG_TYPE_BUZZING_GREEN
        green_player = self.players[buzzing_id]
        green_player.sendMessage(json.dumps(msg).encode('utf-8'))
        self.player_buzzed[buzzing_id] = True

        condition = partial(self.check_player_response, 
                buzzing_id, 'type', MSG_TYPE_BUZZING_ANSWER)

        def callback(x):
            self._buzzing_after(buzzing_id, end_of_question, False)

        def errback(x):
            logger.info('[buzzing] Player answer time out')
            helps = self.player_responses[buzzing_id].get('helps', dict())
            self.player_responses[buzzing_id] = {
                    'type': MSG_TYPE_BUZZING_ANSWER,
                    'qid': self.qid, 'position': self.position,
                    'text': '_TIME_OUT_',
                    'helps': helps}
            self._buzzing_after(buzzing_id, end_of_question, True)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self.deferreds.append((deferred, condition))

    def judge(self, guess):
        return guess.lower() == self.question['answer'].lower()

    def _buzzing_after(self, buzzing_id, end_of_question, timed_out):
        try:
            green_player = self.players[buzzing_id]
            red_players = {k: v for k, v in self.players.items() if k != buzzing_id}
            answer = self.player_responses[buzzing_id]['text']
            position = self.player_responses[buzzing_id]['position']
            result = self.judge(answer) and not timed_out
            score = 10 if result else (0 if end_of_question else -5)
            # if buzzing_id not in self.db_rows:
            #     self.db_rows[buzzing_id] = {
            #             COL_QID: self.qid,
            #             COL_UID: buzzing_id,
            #             COL_START: self.position,
            #             COL_TIME: self.get_time()}
            self.db_rows[buzzing_id][COL_GUESS] = {
                    'position': self.position,
                    'guess': answer,
                    'result': result,
                    'score': score}
            self.db_rows[buzzing_id][COL_HELPS] = \
                    self.player_responses[buzzing_id].get('helps', dict())
            
            if not timed_out:
                logger.info('[buzzing] answer [{}] is {}'.format(answer, result))
            self.player_scores[buzzing_id] += score
            msg = {'type': MSG_TYPE_RESULT_MINE, 'qid': self.qid, 'result': result,
                    'score': score,'uid': buzzing_id, 'guess': answer,
                    'player_list': self.get_player_list()}
            if self.player_alive[buzzing_id]:
                green_player.sendMessage(json.dumps(msg).encode('utf-8'))

            msg['type'] = MSG_TYPE_RESULT_OTHER
            self.broadcast(red_players, msg)
        except:
            traceback.print_exc(file=sys.stdout)

        if end_of_question or result:
            self._end_of_question()
        else:
            reactor.callLater(SECOND_PER_WORD * 2, self.stream_next)

    def _end_of_question(self):
        msg = {'type': MSG_TYPE_END, 'qid': self.qid, 'text': '', 
                'evidence': {'answer': self.question['answer']},
                'player_list': self.get_player_list()}
        self.broadcast(self.players, msg)

        # remove players that are marked of unlive
        dead_players = [x for x, y in self.player_alive.items() if not y]
        for pid in dead_players:
            self.players.pop(pid, None)
            self.player_names.pop(pid, None)
            self.player_alive.pop(pid, None)
            self.player_is_machine.pop(pid, None)
            self.player_responses.pop(pid, None)
            self.player_scores.pop(pid, None)
            self.player_buzzed.pop(pid, None)
            self.db_rows.pop(pid, None)
        logger.info('-' * 60)
        self.pbar.close()

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
