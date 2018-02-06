import json
import pickle
from tqdm import tqdm
from qanta.util.constants import GUESSER_DEV_FOLD
from qanta.datasets.quiz_bowl import QuestionDatabase, Question
from qanta.preprocess import tokenize_question

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

class QBQuestion:

    def __init__(self, question: Question):
        self._question = question
        self.qid = question.qnum
        self.answer = question.page
        self.raw_text = question.flatten_text().split()
        self.length = len(self.raw_text)
        self.tokens = [tokenize_question(x) for x in self.raw_text]

class QantaCacheEntry:
    '''cache entry for one question'''

    def __init__(self, qid, position, answer, guesses, buzz_scores,
            matches, text_highlight, matches_highlight):
        '''
        Args:
            qid (int): question id
            position (int): question text is `question.raw_text[:position]`
            answer (string): the top guess
            guesses: list of (guess, score) tuples
            buzz_scores: [score of buzzing, score of not buzzing]
            matches: list of lists of words, tokenized matches
            text_highlight: list of booleans indicating highlight or not
            matches_highlight: list of lists of booleans
        '''
        self.qid = qid
        self.position = position
        self.answer = answer
        self.guesses = guesses
        self.buzz_scores = buzz_scores
        self.matches = matches
        self.text_highlight = text_highlight
        self.matches_highlight = matches_highlight

def preprocess():
    questions = QuestionDatabase(location='data/naqt.db').all_questions()
    questions = list(questions.values())
    questions = [x for x in questions if 'PACE' in x.tournaments]
    print('preprocessing {} questions'.format(len(questions)))
    qs = []
    for question in tqdm(questions):
        qs.append(QBQuestion(question))
    with open('data/questions.pkl', 'wb') as f:
        pickle.dump(qs, f)

if __name__ == '__main__':
    preprocess()

