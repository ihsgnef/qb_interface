import pickle
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from db import QBDB
from util import *

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('API Project-21af541bdeea.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open("expo_alternative_answers").sheet1
# wks.update_acell('B2', "it's down there somewhere, let me take another look.")

db = QBDB()
with open('data/expo_questions.pkl', 'rb') as f:
    questions = pickle.load(f)

COLS = [x for x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']

wks.update_acell('A1', 'question')
wks.update_acell('B1', 'answer')
wks.update_acell('C1', 'alternative')
for i, q in enumerate(questions):
    n_row = str(i+2)
    idx = q.raw_text.index('10')
    question = ' '.join(x for x in q.raw_text[idx+2:])
    print(question)
    wks.update_acell('A' + n_row, question)
    rs = db.get_records(question_id=q.qid)
    answers = set(r['guess'].strip() for r in rs)
    answer = q.answer.replace('_', ' ')
    wks.update_acell('B' + n_row, answer)
    ignore = ["TIME_OUT", q.answer.lower(), q.answer, answer, '']
    answers = [x for x in list(answers) if x not in ignore]
    for j, a in enumerate(answers):
        n_col = COLS[j+2]
        wks.update_acell(n_col + n_row, a)
