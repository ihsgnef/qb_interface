import os
import json
import uuid
import sqlite3
import logging

logger = logging.getLogger('db')

DB_FILENAME = 'db.sqlite'
TABLE_NAME = "qb_records"
COL_ID = 'id' # unique record id
COL_QID = 'qid' # question id
COL_UID = 'uid' # user id
COL_START = 'start_pos' # starting position
COL_GUESS = 'guess' # dictionary with type, position, guess, result
COL_HELPS = 'helps' # interpretations used
COL_TIME = 'time' # starting time
COLUMNS = [COL_ID, COL_QID, COL_UID, COL_START, COL_GUESS, COL_HELPS]

class QBDB:

    def __init__(self):
        if not os.path.exists(DB_FILENAME):
            self.create()
        self.conn = sqlite3.connect(DB_FILENAME)
        self.c = self.conn.cursor()

    def create(self):
        conn = sqlite3.connect(DB_FILENAME)
        c = conn.cursor()
        c.execute("CREATE TABLE " + TABLE_NAME + " (" \
                + COL_ID + " PRIMARY KEY, " \
                + COL_QID + " INTEGER, " \
                + COL_UID + " TEXT, " \
                + COL_START + " INTEGER DEFAULT 0, " \
                + COL_GUESS + " TEXT, " \
                + COL_HELPS + " TEXT" \
                + ")")
        conn.commit()
        conn.close() 

    def add_row(self, row):
        rid = str(uuid.uuid4()).replace('-', '')
        qid = row.get(COL_QID, 0)
        uid = row.get(COL_UID, 0)
        start = row.get(COL_START, 0)
        guess = row.get(COL_GUESS, dict())
        helps = row.get(COL_HELPS, dict())

        cmd = "INSERT INTO " + TABLE_NAME + " (" \
                + ', '.join(COLUMNS) + ") " \
                + 'VALUES ("{}", {}, "{}", {}, "{}", "{}")'.format(
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
