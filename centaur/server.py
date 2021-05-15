import sys
import json
import uuid
import random
import logging
import traceback
from tqdm import tqdm
from functools import partial
from datetime import datetime
from haikunator import Haikunator

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet.defer import Deferred
from autobahn.twisted.websocket import (
    WebSocketServerFactory,
    WebSocketServerProtocol,
    listenWS
)

from centaur.utils import (
    MSG_TYPE_NEW,
    MSG_TYPE_RESUME,
    MSG_TYPE_END,
    MSG_TYPE_BUZZING_REQUEST,
    MSG_TYPE_BUZZING_ANSWER,
    MSG_TYPE_BUZZING_GREEN,
    MSG_TYPE_BUZZING_RED,
    MSG_TYPE_RESULT_MINE,
    MSG_TYPE_RESULT_OTHER,
    MSG_TYPE_COMPLETE,
    MSG_TYPE_NEW_ROUND,
    BADGE_CORRECT,
    BADGE_WRONG,
    BADGE_BUZZ,
    NEW_LINE,
    BELL,
    ANSWER_TIME_OUT,
    SECOND_PER_WORD,
    PLAYER_RESPONSE_TIME_OUT,
    SECONDS_TILL_NEW_QUESTION,
    HISTORY_LENGTH,
    THRESHOLD,
    EXPLANATIONS,
    ALLOW_PLAYER_CHOICE,
    boldify,
    highlight_template,
)
from centaur.mediator import RandomDynamicMediator
from centaur.db.session import SessionLocal
from centaur.models import Question, Player, Record, QantaCache, PlayerRoundStat
from centaur.expected_wins import ExpectedWins


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')
haikunator = Haikunator()
EW = ExpectedWins()


class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        self.factory.receive(payload, self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class PlayerClient:

    def __init__(
        self,
        client: BroadcastServerProtocol,
        player_id: str = None,
        player_name: str = None,
        player_email: str = None,
    ):
        self.client = client

        if player_id is None:
            player_id = 'player_' + str(uuid.uuid4()).replace('-', '')

        if player_name is None:
            player_name = haikunator.haikunate(token_length=0, delimiter=' ').title()

        if player_email is None:
            player_email = f'{player_name}@qanta.org'

        self.player_id = player_id
        self.player_name = player_name
        self.player_email = player_email

        self.active = True
        self.buzzed = False
        self.response = None
        self.score = 0
        self.position_start = 0
        self.position_buzz = -1
        self.buzz_info = dict()
        self.explanation_config = {x: False for x in EXPLANATIONS + ['allow_player_choice']}
        self.questions_seen = []
        self.questions_answered = []
        self.questions_correct = []
        self.task_completed = False  # answered all questions
        self.before_half_correct = 0

        self.mediator = RandomDynamicMediator()

    def can_buzz(self, qid: str):
        if not self.active:
            return False
        if self.buzzed:
            return False
        return True

    def sendMessage(self, msg: dict):
        if self.active:
            if 'qid' in msg:
                msg['can_buzz'] = self.can_buzz(msg['qid'])
                msg['explanation_config'] = self.explanation_config
            self.client.sendMessage(json.dumps(msg).encode('utf-8'))


class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url: str):
        WebSocketServerFactory.__init__(self, url)
        self.db = SessionLocal()

        self.round_number_list = [3, 4, 6, 8, 9, 10]
        # self.round_number_list = [1]
        self.round_number_index = None
        self.question_index = None
        self.question = None

        self.socket_to_player = dict()  # client.peer -> Player
        self.players = dict()  # player_id -> Player
        self.deferreds = []
        self.position = 0
        self.info_text = ''
        self.history_entries = []
        self.player_list = []
        self.bell_positions = []

        # to get new user started in the middle of a round
        self.latest_resume_msg = None
        self.latest_buzzing_msg = None

        self.all_paused = True  # everyone is stopped

        self.room_id_base = 'room_1'
        self.room_id_and_round = None

    def register(self, client):
        if client.peer not in self.socket_to_player:
            new_player = PlayerClient(client)
            self.socket_to_player[client.peer] = new_player
            qid = 'PAUSED' if self.question is None else self.question.id
            msg = {
                'type': MSG_TYPE_NEW,
                'qid': qid,
                'player_id': new_player.player_id,
                'player_name': new_player.player_name,
                'player_email': new_player.player_email,
            }
            new_player.sendMessage(msg)

            def callback(x):
                try:
                    player_id = new_player.response['player_id']
                    player_name = new_player.response['player_name']
                    player_email = new_player.response['player_email']
                    if player_id in self.players:
                        # same player_id exists
                        old_peer = self.players[player_id].client.peer
                        self.socket_to_player[client.peer] = self.players[player_id]
                        self.players[player_id].client = client
                        self.players[player_id].player_name = player_name
                        self.players[player_id].player_email = player_email
                        self.socket_to_player.pop(old_peer, None)
                        self.players[player_id].active = True
                        logger.info(f"{self.room_id_base} [register] old player {player_name} {player_email} ({old_peer} -> {client.peer})")
                    else:
                        new_player.player_id = player_id
                        new_player.player_name = player_name
                        new_player.player_email = player_email
                        new_player.position_start = self.position
                        self.players[player_id] = new_player

                        player_in_db = self.db.query(Player).get(player_id)
                        if player_in_db is not None:
                            new_player.score = player_in_db.score
                            new_player.questions_seen = player_in_db.questions_seen
                            new_player.questions_answered = player_in_db.questions_answered
                            new_player.questions_correct = player_in_db.questions_correct
                            new_player.task_completed = len(set(player_in_db.questions_answered)) >= THRESHOLD
                        else:
                            logger.info(f'{self.room_id_base} add player {new_player.player_id} to db')
                            player_in_db = Player(
                                id=new_player.player_id,
                                ip_addr=new_player.client.peer,
                                name=new_player.player_name,
                                email=new_player.player_email,
                                mediator_name=new_player.mediator.__class__.__name__,
                                score=0,
                                questions_seen=[],
                                questions_answered=[],
                                questions_correct=[],
                            )
                            self.db.add(player_in_db)
                            self.db.commit()
                        logger.info(f"{self.room_id_base} [register] new player {player_name} {player_email} ({client.peer})")

                    if new_player.response.get('start_new_round', False):
                        self.all_paused = False

                    self.player_list = self.get_player_list()
                    qid = 'PAUSED' if self.question is None else self.question.id
                    length = 0 if self.question is None else self.question.length

                    msg = {
                        'type': MSG_TYPE_NEW,
                        'qid': qid,
                        'player_list': self.player_list,
                        'info_text': self.info_text,
                        'history_entries': self.history_entries,
                        'length': length,
                        'position': self.position,
                        'task_completed': self.all_paused,
                        'room_id': self.room_id_base,
                    }
                    if self.question is not None:
                        tournament_str = f'Round {self.round_number_index + 1}'
                        msg.update({
                            'tournament': tournament_str,
                            'question_index': self.question_index + 1,
                            'n_questions': len(self.questions),
                        })

                    self.players[player_id].sendMessage(msg)

                    # keep player up to date
                    if self.latest_resume_msg is not None:
                        self.players[player_id].sendMessage(self.latest_resume_msg)
                    if self.latest_buzzing_msg is not None:
                        self.players[player_id].sendMessage(self.latest_buzzing_msg)

                    if new_player.response.get('start_new_round', False):
                        chosen_round = int(new_player.response.get('chosen_round', 0))
                        # next round index = chosen_round - 1
                        # if chosen_round is 0, go to default next round
                        if chosen_round != 0:
                            self.new_round(chosen_round - 1)
                        else:
                            self.new_round()

                except Exception:
                    traceback.print_exc(file=sys.stdout)
                # end of callback

            def errback(x):
                logger.info(f'{self.room_id_base} [register] client {client.peer} timed out')

            # check if the qid returned by the player client matches the current one
            qid = 'PAUSED' if self.question is None else self.question.id
            condition = partial(
                self.check_player_response,
                player=new_player,
                key='qid',
                value=qid,
            )
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
            logger.info(f"{self.room_id_base} [unregister] player {player.player_name} inactive")

    def check_player_response(self, player, key, value):
        return (
            player.active
            and player.response is not None
            and key in player.response
            and player.response.get(key, None) == value
        )

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
            self.check_deferreds()
        else:
            logger.warning("Unknown source {}:\n{}".format(client.peer, msg))

    def get_next_question(self):
        # # choose next question based on what currently active players have not seen
        # counter = Counter()
        # counter.update({qid: 0 for qid in self.questions})
        # questions_answered = []
        # for p in self.players.values():
        #     if p.active:
        #         questions_answered.append(set(p.questions_answered))
        # if len(questions_answered) == 0:
        #     questions_answered = []
        # else:
        #     questions_answered = sorted(questions_answered, key=lambda x: -len(x))
        #     questions_answered = questions_answered[0]
        # qids = [x for x in self.questions.keys() if x not in questions_answered]
        # random.shuffle(qids)
        if self.question_index is None:
            self.question_index = 0
        else:
            self.question_index += 1
        if self.question_index < len(self.questions):
            return self.questions[self.question_index]
        else:
            return None

    def update_explanation_config(self):
        for player_id, player in self.players.items():
            if not player.active:
                continue
            # TODO also pass the question
            explanation_config = player.mediator.get_explanation_config(player)
            explanation_config['allow_player_choice'] = ALLOW_PLAYER_CHOICE
            player.explanation_config = explanation_config

    def new_round(self, chosen_round=None):
        if chosen_round is not None:
            self.round_number_index = chosen_round
            assert self.round_number_index >= 0
        else:
            if self.round_number_index is None:
                self.round_number_index = 0
            else:
                self.round_number_index += 1
        if self.round_number_index >= len(self.round_number_list):
            return

        round_number = self.round_number_list[self.round_number_index]
        round_str = f'0{round_number}' if round_number < 10 else str(round_number)
        tournament_str = f'spring_novice_round_{round_str}'
        self.questions = self.db.query(Question).filter(Question.tournament.startswith(tournament_str)).all()[:2]
        logger.info('*********** new round *************')
        logger.info(f'{self.room_id_base} Loaded {len(self.questions)} questions for {tournament_str} (round {self.round_number_index + 1})')

        self.room_id_and_round = f'{self.room_id_base}_{tournament_str}'

        for player_id, player in self.players.items():
            player.sendMessage({'type': MSG_TYPE_NEW_ROUND})

        self.question_index = None
        self.all_paused = False
        self.new_question()

    def end_of_round(self):
        self.all_paused = True

        player_qb_scores = {}
        player_ew_scores = {}
        for player in self.db.query(Player):
            round_stat = self.db.query(PlayerRoundStat).get((player.id, self.room_id_and_round))
            if round_stat is not None:
                player_qb_scores[player.id] = round_stat.qb_score
                player_ew_scores[player.id] = round_stat.ew_score

        print('===================', self.room_id_and_round, '/', self.round_number_index + 1)
        for i, (player_id, qb_score) in enumerate(sorted(player_qb_scores.items(), key=lambda x: -x[1])):
            player = self.db.query(Player).get(player_id)
            print('{:<3}  {:<20}  {:<50}  {:<3}  {:<5}'.format(i, player.name, player.email, qb_score, player_ew_scores[player_id]))
        print('===================')
        print()
        pause_msg = f'{self.room_id_base} Round {self.round_number_index+1} complete. Please visit </br><a href="https://cutt.ly/human_ai_spring_novice">https://cutt.ly/human_ai_spring_novice</a></br>for next round room assignment'
        print(pause_msg)

        for player_id, player in self.players.items():
            player.sendMessage({
                'type': MSG_TYPE_COMPLETE,
                'message': pause_msg,
            })

        try:
            admin_player = [x for x in self.players.values() if x.player_name == 'ihsgnef'][0]
        except IndexError:
            return

        condition = partial(
            self.check_player_response,
            admin_player,
            'type',
            MSG_TYPE_NEW_ROUND,
        )

        def callback(x):
            chosen_round = int(admin_player.response.get('chosen_round', 0))
            # next round index = chosen_round - 1
            # if chosen_round is 0, go to default next round
            if chosen_round != 0:
                self.new_round(chosen_round - 1)
            else:
                self.new_round()

        def errback(x):
            logger.info('{self.room_id_base} failed to start new round')

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            # deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self.deferreds.append((deferred, condition))

    def new_question(self):
        try:
            self.question = self.get_next_question()
            if self.question is None:
                self.end_of_round()
                return

            self.info_text = ''
            self.bell_positions = []
            self.position = 0
            self.latest_resume_msg = None
            self.latest_buzzing_msg = None

            logger.info(f'{self.room_id_base} [new question] {self.question.id} {self.question.answer}')

            def make_callback(player):
                def f(x):
                    logger.info(f'{self.room_id_base} [new question] player {player.player_name} ready')
                return f

            def make_errback(player):
                def f(x):
                    logger.info(f'{self.room_id_base} [new question] player {player.player_name} timed out')
                    self.unregister(player=player)
                return f

            self.player_list = self.get_player_list()

            tournament_str = f'Round {self.round_number_index + 1}'
            msg = {
                'type': MSG_TYPE_NEW,
                'qid': self.question.id,
                'info_text': '',
                'length': self.question.length,
                'position': 0,
                'player_list': self.player_list,
                'room_id': self.room_id_base,
                'tournament': tournament_str,
                'question_index': self.question_index + 1,
                'n_questions': len(self.questions),
            }

            self.update_explanation_config()

            for player in self.players.values():
                msg['explanation_config'] = player.explanation_config
                player.sendMessage(msg)
                condition = partial(
                    self.check_player_response,
                    player=player,
                    key='qid',
                    value=self.question.id,
                )
                callback = make_callback(player)
                errback = make_errback(player)

                if condition():
                    callback(None)
                else:
                    deferred = Deferred()
                    deferred.addTimeout(PLAYER_RESPONSE_TIME_OUT, reactor)
                    deferred.addCallbacks(callback, errback)
                    self.deferreds.append((deferred, condition))
        except Exception:
            traceback.print_exc(file=sys.stdout)

        def calllater():
            for player in self.players.values():
                logger.info(f"{self.room_id_base} player {player.player_name} score {player.score}")
                player.questions_seen.append(self.question.id)
            self.pbar = tqdm(total=self.question.length, leave=False)

            # start streaming question
            self.stream_next()

        reactor.callLater(SECOND_PER_WORD, calllater)

    def get_display_question(self):
        '''
        Get the current question text for display, both plain and highlighted,
        with visual elements like buzzing bells.
        '''
        text_plain = ''
        text_highlighted = ''

        words = self.question.tokens[:self.position]
        highlight = self.cache_entry.text_highlight

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
        matches = self.cache_entry.matches
        highlights = self.cache_entry.matches_highlight
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

    def last_chance(self, countdown):
        buzzing_ids = []
        for player_id, player in self.players.items():
            if not player.can_buzz(self.question.id):
                continue
            if self.check_player_response(
                    player, 'type', MSG_TYPE_BUZZING_REQUEST):
                buzzing_ids.append(player_id)
        if len(buzzing_ids) > 0:
            self._buzzing(buzzing_ids, end_of_question=True)
        else:
            if countdown == 0:
                self._end_of_question()
            else:
                msg = {
                    'type': MSG_TYPE_RESUME,
                    'qid': self.question.id,
                    'position': self.position,
                    'length': self.question.length,
                }
                for player in self.players.values():
                    player.sendMessage(msg)
                reactor.callLater(SECOND_PER_WORD, self.last_chance, countdown - 1)

    def stream_next(self):
        end_of_question = self.position == self.question.length

        self.latest_buzzing_msg = None
        buzzing_ids = []
        for player_id, player in self.players.items():
            if not player.can_buzz(self.question.id):
                continue
            if self.check_player_response(
                    player, 'type', MSG_TYPE_BUZZING_REQUEST):
                buzzing_ids.append(player_id)

        if len(buzzing_ids) > 0:
            self._buzzing(buzzing_ids, end_of_question)
        else:
            if end_of_question:
                self.last_chance(6)
            else:
                self.position += 1
                self.cache_entry = self.db.query(QantaCache).get((self.question.id, self.position))

                text_plain, text_highlighted = self.get_display_question()
                matches_plain, matches_highlighted = self.get_display_matches()
                score_for_buzz, score_for_wait = self.cache_entry.buzz_scores
                autopilot_prediction = score_for_buzz > score_for_wait

                autopilot_prediction = False
                guesses = self.cache_entry.guesses
                if len(guesses) >= 5:
                    guesses = guesses[:5]
                    score_sum = sum([s for x, s in guesses])
                    if score_sum > 0:
                        guesses = [(x, s / score_sum) for x, s in guesses]
                    if guesses[0][1] - guesses[1][1] > 0.05:
                        autopilot_prediction = True

                msg = {
                    'type': MSG_TYPE_RESUME,
                    'qid': self.question.id,
                    'text': text_plain,
                    'text_highlighted': text_highlighted,
                    'position': self.position,
                    'length': self.question.length,
                    'guesses': guesses,
                    'matches': matches_plain,
                    'matches_highlighted': matches_highlighted,
                    'autopilot_prediction': autopilot_prediction,
                }
                self.latest_resume_msg = msg
                self.pbar.update(1)
                for player in self.players.values():
                    player.sendMessage(msg)
                reactor.callLater(SECOND_PER_WORD, self.stream_next)

    def get_player_list(self):
        player_list = []
        for p in self.db.query(Player):
            active = (p.id in self.players) and (self.players[p.id].active)
            if not active:
                continue

            if self.room_id_and_round is not None:
                round_stat = self.db.query(PlayerRoundStat).get((p.id, self.room_id_and_round))
                if round_stat is None:
                    round_stat = PlayerRoundStat(
                        player_id=p.id,
                        room_id=self.room_id_and_round,
                        qb_score=0,
                        ew_score=0,
                        questions_answered=[],
                        questions_correct=[],
                    )
                    self.db.add(round_stat)
                    self.db.commit()
                qb_score = round_stat.qb_score
                ew_score = round_stat.ew_score
                questions_answered = len(set(round_stat.questions_answered))
                questions_correct = len(set(round_stat.questions_correct))
            else:
                qb_score = 0
                ew_score = 0
                questions_answered = 0
                questions_correct = 0

            player_list.append({
                'player_id': p.id,
                'player_name': p.name,
                'score': qb_score,
                'ew_score': round(ew_score, 2),
                'questions_answered': questions_answered,
                'questions_correct': questions_correct,
                'active': active,
            })
        player_list = sorted(player_list, key=lambda x: (x['active'], x['score']), reverse=True)
        return player_list

    def _buzzing(self, buzzing_ids, end_of_question):
        random.shuffle(buzzing_ids)
        buzzing_id = buzzing_ids[0]
        green_player = self.players[buzzing_id]
        logger.info(f'{self.room_id_base} [buzzing] player {green_player.player_name} answering')

        self.info_text += NEW_LINE + BADGE_BUZZ
        self.info_text += ' {}: '.format(boldify(green_player.player_name))
        self.bell_positions.append(self.position)

        msg = {
            'qid': self.question.id,
            'length': ANSWER_TIME_OUT,
            'info_text': self.info_text
        }

        msg['type'] = MSG_TYPE_BUZZING_GREEN
        green_player.sendMessage(msg)
        green_player.buzzed = True
        green_player.position_buzz = self.position
        green_player.questions_answered.append(self.question.id)

        msg['type'] = MSG_TYPE_BUZZING_RED
        for player in self.players.values():
            if player.player_id != buzzing_id:
                player.sendMessage(msg)

        self.latest_buzzing_msg = msg

        condition = partial(
            self.check_player_response,
            green_player,
            'type',
            MSG_TYPE_BUZZING_ANSWER,
        )

        def callback(x):
            self._buzzing_after(buzzing_id, end_of_question, timed_out=False)

        def errback(x):
            logger.info(f'{self.room_id_base} [buzzing] player {green_player.player_name} answer time out')
            self._buzzing_after(buzzing_id, end_of_question, timed_out=True)

        if condition():
            callback(None)
        else:
            deferred = Deferred()
            deferred.addTimeout(ANSWER_TIME_OUT, reactor)
            deferred.addCallbacks(callback, errback)
            self.deferreds.append((deferred, condition))

    def judge(self, guess):
        answer = self.question.answer.strip().lower()
        if guess.strip().lower() == answer:
            return True

        alternatives = [x.strip().lower() for x in self.question.meta.get('alternative_answers', [])]
        if guess.strip().lower() in alternatives:
            return True

        return False

    def _buzzing_after(self, buzzing_id, end_of_question, timed_out):
        try:
            green_player = self.players[buzzing_id]
            answer = 'TIME_OUT' if timed_out else green_player.response['text']
            result = self.judge(answer) and not timed_out
            qb_score = 0
            ew_score = 0
            if result:
                qb_score = 10
                ew_score = EW.score(self.position, self.question.length)
            else:
                if not end_of_question:
                    qb_score = -5
            green_player.buzz_info = {
                'position': self.position,
                'guess': answer,
                'result': int(result),
                'qb_score': qb_score,
                'ew_score': ew_score,
            }

            if False:
                green_player.mediator.update(green_player, result)

            green_player.score += qb_score
            if result:
                green_player.questions_correct.append(self.question.id)
            if not timed_out:
                logger.info(f'{self.room_id_base} [buzzing] answer [{answer}] is {result}')

            if result and self.position <= self.question.length / 2 + 1:
                green_player.before_half_correct += 1

            self.info_text += answer
            self.info_text += NEW_LINE if result else ''
            self.info_text += BADGE_CORRECT if result else BADGE_WRONG
            self.info_text += ' (+ %.2f)' % ew_score if result else ''
            self.info_text += NEW_LINE

            msg = {
                'qid': self.question.id,
                'result': result,
                'score': qb_score,
                'player_id': buzzing_id,
                'guess': answer,
                'info_text': self.info_text
            }

            msg['type'] = MSG_TYPE_RESULT_MINE
            green_player.sendMessage(msg)

            msg['type'] = MSG_TYPE_RESULT_OTHER
            can_buzz_players = 0
            for player in self.players.values():
                if player.player_id != green_player.player_id:
                    player.sendMessage(msg)
                    if player.can_buzz(self.question.id):
                        can_buzz_players += 1

            if can_buzz_players == 0:
                end_of_question = True
        except Exception:
            traceback.print_exc(file=sys.stdout)

        if end_of_question or result:
            self._end_of_question()
        else:
            reactor.callLater(SECOND_PER_WORD * 2, self.stream_next)

    def _end_of_question(self):
        # notify players of end of game and send correct answer
        self.info_text += (NEW_LINE + 'Answer: ' + boldify(self.question.answer))

        # show the whole question
        # but show guesses & matches where the question ended
        self.position = self.question.length
        text_plain, text_highlighted = self.get_display_question()
        matches_plain, matches_highlighted = self.get_display_matches()

        history = {
            'header': self.question.answer,
            'question_text': text_highlighted,
            'info_text': self.info_text,
            'guesses': self.latest_resume_msg['guesses'],
            'matches': self.latest_resume_msg['matches_highlighted']
        }
        self.history_entries.append(history)
        self.history_entries = self.history_entries[-HISTORY_LENGTH:]

        msg = {
            'type': MSG_TYPE_END,
            'qid': self.question.id,
            'text': text_plain,
            'text_highlighted': text_highlighted,
            'position': self.position,
            'length': self.question.length,
            'answer': self.question.answer,
            'info_text': self.info_text,
            'history_entries': self.history_entries
        }

        for player in self.players.values():
            player.sendMessage(msg)

        self.player_list = self.get_player_list()

        try:
            to_remove = []  # list of inactive users to be removed
            for player_id, player in self.players.items():
                player_in_db = self.db.query(Player).get(player_id)
                player_in_db.score = player.score
                player_in_db.questions_seen = player.questions_seen
                player_in_db.questions_answered = player.questions_answered
                player_in_db.questions_correct = player.questions_correct
                self.db.commit()

                if not player.active:
                    to_remove.append(player_id)
                    self.socket_to_player.pop(player.client.peer, None)

                date = datetime.now()
                record_id = json.dumps({
                    'question_id': self.question.id,
                    'player_id': player_in_db.id,
                    'date': str(date),
                })

                record = Record(
                    id=record_id,
                    player_id=player.player_id,
                    question_id=self.question.id,
                    position_start=player.position_start,
                    position_buzz=player.position_buzz,
                    guess=player.buzz_info.get('guess', None),
                    result=player.buzz_info.get('result', None),
                    qb_score=player.buzz_info.get('qb_score', None),
                    ew_score=player.buzz_info.get('ew_score', None),
                    explanation_config=json.dumps(player.explanation_config),
                    mediator_name=player.mediator.__class__.__name__,
                    room_id=self.room_id_and_round,
                    player_list=self.player_list,
                    date=date,
                )
                self.db.add(record)
                self.db.commit()

                round_stat = self.db.query(PlayerRoundStat).get((player.player_id, self.room_id_and_round))
                if round_stat is None:
                    round_stat = PlayerRoundStat(
                        player_id=player.player_id,
                        room_id=self.room_id_and_round,
                        qb_score=0,
                        ew_score=0,
                        questions_answered=[],
                        questions_correct=[],
                    )
                    self.db.add(round_stat)
                    self.db.commit()

                round_stat.qb_score += player.buzz_info.get('qb_score', 0)
                round_stat.ew_score += player.buzz_info.get('ew_score', 0)
                if 'result' in player.buzz_info:
                    round_stat.questions_answered = round_stat.questions_answered + [self.question.id]
                    if player.buzz_info['result']:
                        round_stat.questions_correct = round_stat.questions_correct + [self.question.id]

                self.db.commit()

                # clear player response
                player.response = None
                player.buzzed = False
                player.position_start = 0
                player.position_buzz = -1
                player.buzz_info = dict()

                # n_answered = len(set(player.questions_answered))
                # if (
                #     not player.task_completed
                #     and THRESHOLD > 0
                #     and n_answered >= THRESHOLD
                #     and player.score > 0
                # ):
                #     # first time the player answers THRESHOLD questions
                #     if player.before_half_correct >= 10:
                #         logger.info("player {} complete".format(player.player_name))
                #         player.task_completed = True
                #         player.sendMessage({'type': MSG_TYPE_COMPLETE})

            # remove inactive users
            for player_id in to_remove:
                self.players.pop(player_id, None)

        except Exception:
            traceback.print_exc(file=sys.stdout)

        logger.info(self.room_id_base + '-' * 60)
        self.pbar.close()

        reactor.callLater(SECONDS_TILL_NEW_QUESTION, self.new_question)

        # if len(self.players) > 0:
        #     reactor.callLater(PLAYER_RESPONSE_TIME_OUT, self.new_question)
        # else:
        #     # self.started = False
        #     pass


if __name__ == '__main__':
    factory = BroadcastServerFactory(u"ws://127.0.0.1:9000")
    factory.protocol = BroadcastServerProtocol
    listenWS(factory)

    webdir = File("web/index.html")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
