import re
import json
import pickle
import string
from tqdm import tqdm
from nltk import word_tokenize


MSG_TYPE_NEW = 0 # beginning of a new question
MSG_TYPE_RESUME = 1 # continue
MSG_TYPE_END = 2 # end of question
MSG_TYPE_BUZZING_REQUEST = 3 # user: I'd like to buzz
MSG_TYPE_BUZZING_ANSWER = 4 # user providing an answer
MSG_TYPE_BUZZING_GREEN = 5 # tell user you win the buzz and can answer now
MSG_TYPE_BUZZING_RED = 6 # tell user you cannot buzz now
MSG_TYPE_RESULT_MINE = 7 # result of my answer
MSG_TYPE_RESULT_OTHER = 8 # result of someone else's answer
MSG_TYPE_COMPLETE = 9 # answered all questions

BADGE_CORRECT = ' <span class="badge badge-success">Correct</span>'
BADGE_WRONG = ' <span class="badge badge-warning">Wrong</span>'
BADGE_BUZZ = '<span class="badge badge-danger">Buzz</span>' 
BELL = ' <span class="fa fa-bell" aria-hidden="true"></span> '
NEW_LINE = '</br>'

highlight_color = '#43c6fc'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'
highlight_template = highlight_prefix + '{}' + highlight_suffix
# highlight_template = '<mark data-entity=\"norp\">{}</mark>'

ftp_patterns = {
    '\n',
    ', for 10 points,',
    ', for ten points,',
    '--for 10 points--',
    'for 10 points, ',
    'for 10 points--',
    'for ten points, ',
    'for 10 points ',
    'for ten points ',
    ', ftp,'
    'ftp,',
    'ftp'
}

patterns = ftp_patterns | set(string.punctuation)
regex_pattern = '|'.join([re.escape(p) for p in patterns])
regex_pattern += r'|\[.*?\]|\(.*?\)'


def bodify(text):
    return '<b>{}</b>'.format(text) 


def clean_question(question: str):
    """
    Remove pronunciation guides and other formatting extras
    :param question:
    :return:
    """

    return re.sub(regex_pattern, '', question.strip().lower())


def tokenize_question(text):
    return word_tokenize(clean_question(text))


class QBQuestion:

    def __init__(self, question=None):
        # question should be a qanta.datasets.quiz_bowl.Question
        if question is not None:
            self.qid = question.qnum
            self.answer = question.page
            self.raw_text = question.flatten_text().split()
            self.length = len(self.raw_text)
            self.tokens = [tokenize_question(x) for x in self.raw_text]

    def set(self, qid, answer, text):
        self.qid = qid
        self.answer = answer
        self.raw_text = text.split()
        self.length = len(self.raw_text)
        self.tokens = [tokenize_question(x) for x in self.raw_text]

class NullQuestion:

    def __init__(self):
        self.qnum = 0
        self.page = ''
    
    def flatten_text(self):
        return ''

null_question = QBQuestion(NullQuestion())

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

def preprocess_pace():
    from qanta.datasets.quiz_bowl import QuestionDatabase
    questions = QuestionDatabase(location='data/naqt.db').all_questions()
    questions = list(questions.values())
    questions = [x for x in questions if 'PACE' in x.tournaments]
    print('preprocessing {} questions'.format(len(questions)))
    qs = []
    for question in tqdm(questions):
        qs.append(QBQuestion(question))
    with open('data/pace_questions.pkl', 'wb') as f:
        pickle.dump(qs, f)

def preprocess_expo():
    with open('data/expo_questions.txt') as f:
        questions = f.readlines()
    with open('data/expo_answers.txt') as f:
        answers = f.readlines()
    qs = []
    for i, (q, a) in enumerate(tqdm(zip(questions, answers))):
        qbq = QBQuestion()
        qbq.set(900000 + i, a.strip(), q.strip())
        qs.append(qbq)
    with open('data/expo_questions.pkl', 'wb') as f:
        pickle.dump(qs, f)

if __name__ == '__main__':
    preprocess_pace()
    preprocess_expo()

