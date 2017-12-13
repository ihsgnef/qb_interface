import os
import json
import uuid
import sqlite3
import logging

logger = logging.getLogger('db')

DB_FILENAME = 'db.sqlite'

class QBDB:

    def __init__(self):
        if not os.path.exists(DB_FILENAME):
            self.create()
        self.conn = sqlite3.connect(DB_FILENAME)
        self.c = self.conn.cursor()

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
                enabled_tools TEXT)')

        c.execute('CREATE TABLE players (\
                player_id PRIMARY KEY, \
                ip TEXT, \
                name TEXT)')

        c.execute('CREATE TABLE games (\
                game_id PRIMARY KEY, \
                question_id TEXT, \
                players TEXT, \
                question_text TEXT, \
                info_text TEXT)')
        conn.commit()
        conn.close() 

    def add_player(self, player):
        player_id = player.uid
        ip = player.client.peer
        name = player.name
        try:
            self.c.execute('INSERT INTO players VALUES (?,?,?)',
                    (player_id, ip, name))
        except sqlite3.IntegrityError:
            logger.info("player {} exists".format(player_id))
        self.conn.commit()

    def add_game(self, qid, players, question_text, info_text):
        game_id = 'game_' + str(uuid.uuid4()).replace('-', '')
        if isinstance(players, dict):
            players = players.values()
        player_ids = [x.uid for x in players]
        # include players that are not active
        self.c.execute('INSERT INTO games VALUES (?,?,?,?,?)',
                (game_id, qid,
                json.dumps(player_ids),
                question_text, info_text))
        self.conn.commit()
        return game_id

    def add_record(self, game_id, player_id, player_name, question_id,
            position_start=0, position_buzz=-1,
            guess='', result=None, score=0,
            enabled_tools=dict()):
        record_id = 'record_' + str(uuid.uuid4()).replace('-', '')
        self.c.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (record_id, game_id, player_id, player_name, question_id,
                position_start, position_buzz, guess, result, score,
                json.dumps(enabled_tools)))
        self.conn.commit()

class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

if __name__ == '__main__':
    from new_server import Player
    db = QBDB()
    client = Namespace(peer="dummy_peer")
    player_id = 'player_' + str(uuid.uuid4()).replace('-', '')
    name = "dummy_name"
    player = Player(client, player_id, name)
    db.add_player(player)
    qid = 20
    game_id = db.add_game(qid, [player], "question text awd", "info text awd")
    db.add_record(game_id, player.uid, qid,
            position_start=0, position_buzz=-1,
            guess='China', result=True, score=10,
            enabled_tools=dict())
