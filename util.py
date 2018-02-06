import json
from qanta.util.constants import GUESSER_DEV_FOLD
from qanta.datasets.quiz_bowl import QuizBowlDataset

MSG_TYPE_NEW = 0 # beginning of a new question
MSG_TYPE_RESUME = 1 # continue
MSG_TYPE_END = 2 # end of question
MSG_TYPE_BUZZING_REQUEST = 3 # user: I'd like to buzz
MSG_TYPE_BUZZING_ANSWER = 4 # user providing an answer
MSG_TYPE_BUZZING_GREEN = 5 # tell user you win the buzz and can answer now
MSG_TYPE_BUZZING_RED = 6 # tell user you cannot buzz now
MSG_TYPE_RESULT_MINE = 7 # result of my answer
MSG_TYPE_RESULT_OTHER = 8 # result of someone else's answer

BADGE_CORRECT = ' <span class="badge badge-success">Correct</span>'
BADGE_WRONG = ' <span class="badge badge-warning">Wrong</span>'
BADGE_BUZZ = '<span class="badge badge-danger">Buzz</span>' 
BELL = ' <span class="fa fa-bell" aria-hidden="true"></span> '
NEW_LINE = '</br>'

highlight_color = '#ecff6d'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'
highlight_template = highlight_prefix + '{}' + highlight_suffix

def bodify(text):
    return '<b>{}</b>'.format(text) 

def preprocess():
    dataset = QuizBowlDataset(guesser_train=True, qb_question_db='data/naqt.db')
    questions = dataset.questions_by_fold([GUESSER_DEV_FOLD])[GUESSER_DEV_FOLD]
    
    def convert(q):
        return {'qid': q.qnum, 'text': ' '.join(q.text.values()), 'answer': q.page}
    
    questions = [convert(q) for q in questions]
    with open('data/sample_questions.json', 'w') as f:
        f.write(json.dumps(questions))
