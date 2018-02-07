import sys
import json
import time
import uuid
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
from util import BADGE_CORRECT, BADGE_WRONG, BADGE_BUZZ, \
        NEW_LINE, BELL, bodify, highlight_template
from util import QBQuestion, QantaCacheEntry, null_question
from db import QBDB

ANSWER_TIME_OUT = 10
SECOND_PER_WORD = 0.4
PLAYER_RESPONSE_TIME_OUT = 3
HISTORY_LENGTH = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')

haikunator = Haikunator()

def get_time():
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

class Player:

    def __init__(self, client, uid=None, name=None, is_machine=False, score=0,
            active=True):
        self.client = client
        if uid is not None:
            self.uid = uid
        else:
            self.uid = 'player_' + str(uuid.uuid4()).replace('-', '')
        if name is not None:
            self.name = name
        else:
            self.name = haikunator.haikunate(token_length=0, 
                    delimiter=' ').title()
        self.is_machine = is_machine
        self.active = active
        self.score = score
        self.buzzed = False
        self.response = None
        self.position_start = 0
        self.position_buzz = -1
        self.buzz_info = dict()
        self.enabled_tools = {
                'guesses': True, 'highlight': True, 'matches': True}
        self.questions_seen = []
        self.questions_answered = []
        self.questions_correct = []

    def can_buzz(self):
        return self.active and not self.buzzed

    def sendMessage(self, msg):
        if self.active:
            msg['buzzed'] = self.buzzed
            self.client.sendMessage(json.dumps(msg).encode('utf-8'))


class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(payload, self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url, loop=False):
        WebSocketServerFactory.__init__(self, url)

        with open('data/pace_questions.pkl', 'rb') as f:
            self.questions = pickle.load(f)
            random.shuffle(self.questions)
        logger.info('Loaded {} questions'.format(len(self.questions)))

        self.db = QBDB()
        self.loop = loop
        self.question_idx = -1

        self.socket_to_player = dict() # client.peer -> Player
        self.players = dict() # uid -> Player
        self.deferreds = []

        self.question = null_question
        self.started = False
        self.position = 0
        self.info_text = ''
        self.history_entries = []
        self.player_list = []

        # to get new user started in the middle of a round
        self.latest_resume_msg = None 
        self.latest_buzzing_msg = None


    def register(self, client):
        if client.peer not in self.socket_to_player:
            new_player = Player(client)
            self.socket_to_player[client.peer] = new_player
            msg = {'type': MSG_TYPE_NEW,
                    'qid': self.question.qid,
                    'player_uid': new_player.uid,
                    'player_name': new_player.name}
            new_player.sendMessage(msg)

            def callback(x):
                try:
                    uid = new_player.response['player_uid']
                    name = new_player.response['player_name']
                    if uid in self.players:
                        # same uid exists
                        old_peer = self.players[uid].client.peer
                        self.socket_to_player[client.peer] = self.players[uid]
                        self.players[uid].client = client
                        self.players[uid].name = name
                        self.socket_to_player.pop(old_peer, None)
                        self.players[uid].active = True
                        logger.info("[register] old player {} ({} -> {})".format(
                            name, old_peer, client.peer))
                    else:
                        new_player.uid = uid
                        new_player.name = name
                        new_player.position_start = self.position
                        self.players[uid] = new_player

                        dbp = self.db.get_player(uid)
                        if dbp is not None:
                            new_player.score = dbp['score']
                            new_player.questions_seen = dbp['questions_seen']
                            new_player.questions_answered = dbp['questions_answered']
                            new_player.questions_correct = dbp['questions_correct']
                        else:
                            logger.info('add player {} to db'.format(new_player.uid))
                            self.db.add_player(new_player)
                        logger.info("[register] new player {} ({})".format(
                            name, client.peer))

                    msg = {'type': MSG_TYPE_NEW, 'qid': self.question.qid,
                            'player_list': self.player_list,
                            'info_text': self.info_text,
                            'history_entries': self.history_entries,
                            'position': self.position,
                            'speech_text': ' '.join(self.question.raw_text[self.position:])}
                    self.players[uid].sendMessage(msg)

                    # keep player up to date
                    if self.latest_resume_msg is not None:
                        self.players[uid].sendMessage(self.latest_resume_msg)
                    if self.latest_buzzing_msg is not None:
                        self.players[uid].sendMessage(self.latest_buzzing_msg)

                    if len(self.players) == 1 and not self.started:
                        self.started = True
                        self.new_question()
                except:
                    traceback.print_exc(file=sys.stdout)

            def errback(x):
                logger.info('[register] client {} timed out'.format(client.peer))

            condition = partial(self.check_player_response,
                                player=new_player, key='qid',
                                value=self.question.qid)
            if condition():
                callback(None)
            else:
                deferred = Deferred()
                deferred.addTimeout(PLAYER_RESPONSE_TIME_OUT, reactor)
                deferred.addCallbacks(callback, errback)
                self.deferreds.append((deferred, condition))
    
    def unregister(self, client=None, player=None):
        if player is None:
            player = self.socket_to_player.pop(client.peer, None)
        if player is not None:
            player.active = False
            logger.info("[unregister] player {} inactive".format(player.name))

    def check_player_response(self, player, key, value):
        return player.active and \
                player.response is not None and \
                key in player.response and \
                player.response.get(key, None) == value

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
        if client.peer in self.socket_to_player:
            player = self.socket_to_player[client.peer]
            player.response = msg
            if 'enabled_tools' in msg:
                player.enabled_tools = msg
            self.check_deferreds()
        else:
            logger.warning("Unknown source {}:\n{}".format(client.peer, msg))

    def new_question(self):
        try:
            self.question_idx += 1
            if self.question_idx >= len(self.questions):
                if self.loop:
                    random.shuffle(self.questions)
                    self.question_idx = 0
                else:
                    self._end_of_game()
                    return
            
            self.question = self.questions[self.question_idx]
            self.question.answer = self.question.answer.replace('_', ' ')

            self.display_question = ''
            self.info_text = ''
            # self.record = self.records[int(self.question.qid)]
            self.record = self.db.get_cache(self.question.qid)
            # print(self.record[10].matches)
            self.bell_positions = []
            self.position = 0
            self.latest_resume_msg = None
            self.latest_buzzing_msg = None

            def make_callback(player):
                def f(x):
                    logger.info('[new question] player {} ready'.format(
                        player.name))
                return f

            def make_errback(player):
                def f(x):
                    logger.info('[new question] player {} timed out'.format(
                        player.name))
                    self.unregister(player=player)
                return f

            self.player_list = self.get_player_list()
            msg = {'type': MSG_TYPE_NEW, 'qid': self.question.qid, 
                    'length': self.question.length, 'position': 0,
                    'player_list': self.player_list,
                    'speech_text': ' '.join(self.question.raw_text)}

            for player in self.players.values():
                player.sendMessage(msg)
                condition = partial(self.check_player_response,
                        player=player, key='qid', value=self.question.qid)
                callback = make_callback(player)
                errback = make_errback(player)
                
                if condition():
                    callback(None)
                else:
                    deferred = Deferred()
                    deferred.addTimeout(PLAYER_RESPONSE_TIME_OUT, reactor)
                    deferred.addCallbacks(callback, errback)
                    self.deferreds.append((deferred, condition))
        except:
            traceback.print_exc(file=sys.stdout)

        def calllater():
            for player in self.players.values():
                logger.info("player {} score {}".format(
                    player.name, player.score))
                player.questions_seen.append(self.question.qid)
            self.pbar = tqdm(total=self.question.length, leave=False)
            self.stream_next()

        reactor.callLater(SECOND_PER_WORD, calllater)

    def get_display_question(self):
        '''
        Get the current question text for display, both plain and highlighted,
        with visual elements like buzzing bells.
        '''
        text_plain = ''
        text_highlighted = ''

        words = self.question.raw_text[:self.position]
        highlight = self.record[self.position].text_highlight

        for i, (x, y) in enumerate(zip(words, highlight)):
            text_plain += x + ' '
            x = highlight_template.format(x) if y else x
            text_highlighted += x + ' '
            if i + 1 in self.bell_positions:
                text_plain += BELL
                text_highlighted += BELL
        return text_plain, text_highlighted
        
    def get_display_matches(self):
        '''
        Get the current matches for display, both plain and highlighted.
        '''
        matches = self.record[self.position].matches
        highlights = self.record[self.position].matches_highlight
        matches_plain = []
        matches_highlighted = []
        for i, (match, high) in enumerate(zip(matches, highlights)):
            matches_plain.append('')
            matches_highlighted.append('')
            for x, y in zip(match, high):
                matches_plain[i] += x + ' '
                x = highlight_template.format(x) if y else x
                matches_highlighted[i] += x + ' '
        return matches_plain, matches_highlighted

    def stream_next(self):
        end_of_question = self.position >= self.question.length

        self.latest_buzzing_msg = None
        buzzing_ids = []
        for uid, player in self.players.items():
            if not player.can_buzz():
                continue
            if end_of_question or self.check_player_response(
                    player, 'type', MSG_TYPE_BUZZING_REQUEST):
                buzzing_ids.append(uid)

        if len(buzzing_ids) > 0:
            self._buzzing(buzzing_ids, end_of_question)
        else:
            if end_of_question:
                self._end_of_question()
            else:
                self.position += 1
                text_plain, text_highlighted = self.get_display_question()
                matches_plain, matches_highlighted = self.get_display_matches()
                self.display_question = text_highlighted

                msg = {'type': MSG_TYPE_RESUME,  'qid': self.question.qid,
                        'text': text_plain,
                        'text_highlighted': text_highlighted,
                        'position': self.position,
                        'length': self.question.length,
                        'guesses': self.record[self.position].guesses,
                        'matches': matches_plain,
                        'matches_highlighted': matches_highlighted
                        }
                self.latest_resume_msg = msg
                self.pbar.update(1)
                for player in self.players.values():
                    player.sendMessage(msg)
                reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def get_player_list(self):
        db_players = self.db.get_player()
        players = sorted(self.players.values(), key=lambda x: x.score)[::-1]
        player_list = []
        for x in db_players:
            uid = x['player_id']
            active = (uid in self.players) and (self.players[uid].active)
            player_list.append({'uid': x['player_id'], 'name': x['name'],
                'score': x['score'],
                'questions_seen': x['questions_seen'],
                'questions_answered': x['questions_answered'],
                'questions_correct': x['questions_correct'],
                'active': active})
        player_list = sorted(player_list, key=lambda x: x['score'])[::-1]
        return player_list 

    def _buzzing(self, buzzing_ids, end_of_question):
        random.shuffle(buzzing_ids)
        buzzing_id = buzzing_ids[0]
        green_player = self.players[buzzing_id]
        logger.info('[buzzing] player {} answering'.format(green_player.name))

        self.info_text += NEW_LINE + BADGE_BUZZ
        self.info_text += ' {}: '.format(bodify(green_player.name))
        self.bell_positions.append(self.position)

        msg = {'qid': self.question.qid, 
                'length': ANSWER_TIME_OUT,
                'info_text': self.info_text}

        msg['type'] = MSG_TYPE_BUZZING_GREEN
        green_player.sendMessage(msg)
        green_player.buzzed = True
        green_player.position_buzz = self.position
        green_player.questions_answered.append(self.question.qid)

        msg['type'] = MSG_TYPE_BUZZING_RED
        for player in self.players.values():
            if player.uid != buzzing_id:
                player.sendMessage(msg)

        self.latest_buzzing_msg = msg

        condition = partial(self.check_player_response, 
                green_player, 'type', MSG_TYPE_BUZZING_ANSWER)

        def callback(x):
            self._buzzing_after(buzzing_id, end_of_question, timed_out=False)

        def errback(x):
            logger.info('[buzzing] player {} answer time out'.format(
                green_player.name))
            self._buzzing_after(buzzing_id, end_of_question, timed_out=True)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self.deferreds.append((deferred, condition))

    def judge(self, guess):
        return guess.lower() == self.question.answer.lower()

    def _buzzing_after(self, buzzing_id, end_of_question, timed_out):
        try:
            green_player = self.players[buzzing_id]
            answer = 'TIME_OUT' if timed_out else green_player.response['text']
            result = self.judge(answer) and not timed_out
            score = 10 if result else (0 if end_of_question else -5)
            green_player.buzz_info = {
                    'position': self.position,
                    'guess': answer,
                    'result': result,
                    'score': score}
            
            green_player.score += score
            if result:
                green_player.questions_correct.append(self.question.qid)
            if not timed_out:
                logger.info('[buzzing] answer [{}] is {}'.format(answer, result))

            self.info_text += answer
            self.info_text += BADGE_CORRECT if result else BADGE_WRONG
            self.info_text += ' ({})'.format(green_player.score)
            self.info_text += NEW_LINE

            msg = {'qid': self.question.qid, 'result': result,
                    'score': score,'uid': buzzing_id, 'guess': answer,
                    'info_text': self.info_text}

            msg['type'] = MSG_TYPE_RESULT_MINE
            green_player.sendMessage(msg)

            msg['type'] = MSG_TYPE_RESULT_OTHER
            for player in self.players.values():
                if player.uid != green_player.uid:
                    player.sendMessage(msg)
        except:
            traceback.print_exc(file=sys.stdout)

        if end_of_question or result:
            self._end_of_question()
        else:
            reactor.callLater(SECOND_PER_WORD * 2, self.stream_next)

    def _end_of_question(self):
        # notify players of end of game and send correct answer
        self.info_text += NEW_LINE + bodify('Answer') \
                + ': ' + self.question.answer

        history = {'header': self.question.answer,
                   'question_text': self.display_question,
                   'info_text': self.info_text,
                   'guesses': self.latest_resume_msg['guesses'],
                   'matches': self.latest_resume_msg['matches_highlighted']
                   }
        self.history_entries.append(history)
        self.history_entries = self.history_entries[-HISTORY_LENGTH:]
        
        msg = {'type': MSG_TYPE_END, 
                'qid': self.question.qid, 'text': '', 
                'answer': self.question.answer,
                'info_text': self.info_text,
                'history_entries': self.history_entries
                }

        for player in self.players.values():
            player.sendMessage(msg)

        try:
            game_id = self.db.add_game(self.question.qid, self.players,
                    self.display_question,
                    self.info_text)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

        try:
            # remove inactive player
            # clear player response
            # set buzzed to false
            to_remove = []
            for uid, player in self.players.items():
                self.db.update_player(player)
                if not player.active:
                    to_remove.append(uid)
                    self.socket_to_player.pop(player.client.peer, None)
                self.db.add_record(game_id, uid, player.name, self.question.qid,
                        player.position_start, player.position_buzz,
                        player.buzz_info.get('guess', ''),
                        player.buzz_info.get('result', None),
                        player.buzz_info.get('score', 0),
                        player.enabled_tools)
                player.response = None
                player.buzzed = False
                player.position_start = 0
                player.position_buzz = -1
                player.buzz_info = dict()
            for uid in to_remove:
                self.players.pop(uid, None)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

        logger.info('-' * 60)
        self.pbar.close()


        if len(self.players) > 0:
            reactor.callLater(PLAYER_RESPONSE_TIME_OUT, self.new_question)
        else:
            self.started = False


if __name__ == '__main__':
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000", loop=True)
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
