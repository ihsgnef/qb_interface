import os
import json
import uuid
import sqlite3
import logging

logger = logging.getLogger('db')

DB_FILENAME = 'db.sqlite'
PLAYER_TABLE_NAME = 'player'
RECORD_TABLE_NAME = 'record'
COL_ID = 'id' # unique record id
COL_QID = 'qid' # question id
COL_UID = 'uid' # user id
COL_START = 'start_pos' # starting position
COL_GUESS = 'guess' # dictionary with type, position, guess, result
COL_HELPS = 'helps' # interpretations used
COL_TIME = 'time' # starting time
RECORD_COLUMNS = [COL_ID, COL_QID, COL_UID, COL_START, COL_GUESS, COL_HELPS]

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
                question_id INTEGER, \
                player_id TEXT, \
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
        cmd = 'INSERT INTO players ' \
                + 'VALUES ("{}", "{}", "{}")'.format(
                        player_id, ip, name)
        try:
            self.c.execute(cmd)
        except sqlite3.IntegrityError:
            logger.error('ERROR: ID already exists in PRIMARY KEY column')
        self.conn.commit()

    def add_game(self, qid, players, question_text, info_text):
        game_id = 'game_' + str(uuid.uuid4()).replace('-', '')
        if isinstance(players, dict):
            players = player.values()
        player_ids = [x.player.uid for x in players if x.active]
        cmd = 'INSERT INTO games ' \
                + 'VALUES ("{}", "{}", "{}", "{}", "{}")'.format(
                        game_id, qid,
                        json.dumps(player_ids),
                        question_text, info_text)
        try:
            self.c.execute(cmd)
        except sqlite3.IntegrityError:
            logger.error('ERROR: ID already exists in PRIMARY KEY column')
        self.conn.commit()
    '''
                record_id PRIMARY KEY, \
                game_id TEXT, \
                question_id INTEGER, \
                player_id TEXT, \
                position_start INTEGER DEFAULT 0, \
                position_buzz INTEGER DEFAULT -1, \
                guess TEXT, \
                result INTEGER, \
                score INTEGER, \
                enabled_tools TEXT)')
    '''

    def add_record(self, game_id, player_id, question_id,
            position_start=0, position_buzz=-1,
            guess='', result=False, score=0,
            enabled_tools=dict()):
        record_id = 'record_' + str(uuid.uuid4()).replace('-', '')
        cmd = 'INSERT INTO records' \
                + 'VALUES ("{}", "{}", {}, "{}", {}, "{}", "{}")'.format(
                    rid, qid, uid, start,
                    json.dumps(guess).replace('"', "'"),
                    json.dumps(helps).replace('"', "'"))
        logger.debug(cmd)
        try:
            self.c.execute(cmd)
        except sqlite3.IntegrityError:
            logger.error('ERROR: ID already exists in PRIMARY KEY column')
        self.conn.commit()

if __name__ == '__main__':
    db = QBDB()
    row = {COL_QID: 1, COL_UID: 2, COL_START: 2,
            COL_GUESS: {'type': 'buzz', 'guess': 'sony', 'result': False, 'score': -5},
            COL_HELPS: {'guesses': True, 'highlight': True}}
    db.add_row(row)
