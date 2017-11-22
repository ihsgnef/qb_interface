import os
import json
import uuid
import sqlite3

DB_FILENAME = 'db.sqlite'
TABLE_NAME = "qb_records"
COL_ID = 'id' # unique record id
COL_QID = 'qid' # question id
COL_UID = 'uid' # user id
COL_START = 'start_pos' # starting position
COL_GUESS = 'guess' # dictionary with type, position, guess, result
COL_HELPS = 'helps' # interpretations used
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
                + COL_UID + " INTEGER DEFAULT 0, " \
                + COL_START + " INTEGER DEFAULT 0, " \
                + COL_GUESS + " TEXT, " \
                + COL_HELPS + " TEXT" \
                + ")")
        conn.commit()
        conn.close() 

    def add_row(self, qid, uid, start, guess=dict(), helps=dict()):
        rid = str(uuid.uuid4()).replace('-', '')
        cmd = "INSERT INTO " + TABLE_NAME + " (" \
                + ', '.join(COLUMNS) + ") " \
                + 'VALUES ("{}", {}, {}, {}, "{}", "{}")'.format(
                    rid, qid, uid, start,
                    json.dumps(guess).replace('"', "'"),
                    json.dumps(helps).replace('"', "'"))
        # print(cmd)
        try:
            self.c.execute(cmd)
        except sqlite3.IntegrityError:
                print('ERROR: ID already exists in PRIMARY KEY column')
        self.conn.commit()

if __name__ == '__main__':
    db = QBDB()
    db.add_row(qid=1, uid=2, start=0, 
            guess={'type': 'buzz', 'guess': 'sony', 'result': 'wrong', 'score': -5}, 
            helps={'guesses': True, 'highlight': True}
            )
