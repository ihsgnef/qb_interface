import os
import json
import uuid
import sqlite3
import logging
from util import QantaCacheEntry

logger = logging.getLogger('db')
DB_FILENAME = 'db.sqlite'

class QBDB:

    def __init__(self):
        if not os.path.exists(DB_FILENAME):
            self.create()
        self.conn = sqlite3.connect(DB_FILENAME)

    def create(self):
        conn = sqlite3.connect(DB_FILENAME)
        c = conn.cursor()
        c.execute('CREATE TABLE records (\
                record_id PRIMARY KEY, \
                game_id TEXT, \
                player_id TEXT, \
                player_name TEXT, \
                question_id INTEGER, \
                position_start INTEGER DEFAULT 0, \
                position_buzz INTEGER DEFAULT -1, \
                guess TEXT, \
                result INTEGER, \
                score INTEGER, \
                enabled_tools TEXT, \
                free_mode INTEGER)')

        c.execute('CREATE TABLE players (\
                player_id PRIMARY KEY, \
                ip TEXT, \
                name TEXT, \
                score INT, \
                questions_seen TEXT, \
                questions_answered TEXT, \
                questions_correct TEXT)')

        c.execute('CREATE TABLE games (\
                game_id PRIMARY KEY, \
                question_id TEXT, \
                players TEXT, \
                question_text TEXT, \
                info_text TEXT)')

        c.execute('CREATE TABLE qanta_cache (\
                question_id PRIMARY KEY, \
                json_str TEXT)')

        conn.commit()
        conn.close()

    def add_player(self, player):
        c = self.conn.cursor()
        questions_seen = json.dumps(player.questions_seen)
        questions_answered = json.dumps(player.questions_answered)
        questions_correct = json.dumps(player.questions_correct)
        try:
            c.execute('INSERT INTO players VALUES (?,?,?,?,?,?,?)',
                      (player.uid, player.client.peer, player.name, player.score,
                       questions_seen, questions_answered, questions_correct))
        except sqlite3.IntegrityError:
            logger.info("player {} exists".format(player.uid))
        self.conn.commit()

    def add_game(self, qid, players, question_text, info_text):
        game_id = 'game_' + str(uuid.uuid4()).replace('-', '')
        if isinstance(players, dict):
            players = players.values()
        player_ids = [x.uid for x in players]
        # include players that are not active
        c = self.conn.cursor()
        c.execute('INSERT INTO games VALUES (?,?,?,?,?)',
                  (game_id, qid, json.dumps(player_ids), question_text, info_text))
        self.conn.commit()
        return game_id

    def add_record(self, game_id, player_id, player_name, question_id,
                   position_start=0, position_buzz=-1,
                   guess='', result=None, score=0,
                   enabled_tools=dict(), free_mode=False):
        record_id = 'record_' + str(uuid.uuid4()).replace('-', '')
        c = self.conn.cursor()
        c.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                  (record_id, game_id, player_id, player_name, question_id,
                   position_start, position_buzz, guess, result, score,
                   json.dumps(enabled_tools), int(free_mode)))
        self.conn.commit()

    def add_cache(self, question_id, records):
        # records is a list of QantaCacheEntry
        records = {
            i: {'qid': e.qid,
                'position': e.position,
                'answer': e.answer,
                'guesses': e.guesses,
                'buzz_scores': e.buzz_scores,
                'matches': e.matches,
                'text_highlight': e.text_highlight,
                'matches_highlight': e.matches_highlight
                } for i, e in records.items()
        }
        c = self.conn.cursor()
        try:
            c.execute('INSERT INTO qanta_cache VALUES (?,?)',
                      (question_id, json.dumps(records)))

        except sqlite3.IntegrityError:
            logger.info("question {} cache exists".format(question_id))
        self.conn.commit()

    def get_cache(self, question_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM qanta_cache WHERE question_id=?", (question_id,))
        records = c.fetchall()
        if len(records) == 0:
            logger.info("cache {} does not exist".format(question_id))
            return None
        records = json.loads(records[0][1])  # key, value
        records = {
            int(i): QantaCacheEntry(
                e['qid'], e['position'], e['answer'], e['guesses'],
                e['buzz_scores'], e['matches'],
                e['text_highlight'], e['matches_highlight']
            ) for i, e in records.items()
        }
        return records

    def get_player(self, player_id=None, player_name=None):
        def row_to_dict(r):
            return {
                'player_id': r[0],
                'ip': r[1],
                'name': r[2],
                'score': r[3],
                'questions_seen': json.loads(r[4]),
                'questions_answered': json.loads(r[5]),
                'questions_correct': json.loads(r[6])
            }
        c = self.conn.cursor()
        if player_id is None and player_name is None:
            c.execute("SELECT * FROM players")
            return [row_to_dict(r) for r in c.fetchall()]
        elif player_id is not None:
            c.execute("SELECT * FROM players WHERE player_id=?", (player_id,))
            r = c.fetchall()
            if len(r) == 0:
                return None
            else:
                return row_to_dict(r[0])
        else:
            assert player_name is not None
            c.execute("SELECT * FROM players WHERE name=?", (player_name,))
            rs = c.fetchall()
            if len(rs) == 0:
                return None
            else:
                return [row_to_dict(r) for r in rs]

    def update_player(self, player):
        c = self.conn.cursor()
        c.execute("UPDATE players SET score=?,\
                questions_seen=?,questions_answered=?,questions_correct=? \
                WHERE player_id=?", (
            player.score,
            json.dumps(player.questions_seen),
            json.dumps(player.questions_answered),
            json.dumps(player.questions_correct),
            player.uid))
        self.conn.commit()

    def get_records(self, player_id=None, question_id=None):
        def row_to_dict(row):
            rs = {
                'record_id': row[0],
                'game_id': row[1],
                'player_id': row[2],
                'player_name': row[3],
                'question_id': row[4],
                'position_start': row[5],
                'position_buzz': row[6],
                'guess': row[7],
                'result': row[8],
                'score': row[9],
                'enabled_tools': json.loads(row[10])
            }
            if len(row) == 10:
                rs['free_mode'] = bool(row[11])
            return rs
        c = self.conn.cursor()
        if player_id is not None:
            c.execute("SELECT * FROM records WHERE player_id=?", (player_id,))
        elif question_id is not None:
            c.execute("SELECT * FROM records WHERE question_id=?", (question_id,))
        else:
            c.execute("SELECT * FROM records")
        rs = c.fetchall()
        rs = [row_to_dict(r) for r in rs]
        return rs


class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


if __name__ == '__main__':
    from server import Player
    db = QBDB()
    client = Namespace(peer="dummy_peer")
    player_id = 'player_' + str(uuid.uuid4()).replace('-', '')
    name = "dummy_name"
    player = Player(client, player_id, name)
    db.add_player(player)
    qid = 20
    game_id = db.add_game(qid, [player], "question text awd", "info text awd")
    db.add_record(
        game_id, player.uid, name, qid,
        position_start=0, position_buzz=-1,
        guess='China', result=True, score=10,
        enabled_tools=dict(),
        free_mode=False
    )
