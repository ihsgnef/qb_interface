import logging
import numpy as np
import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords as sw

from centaur.utils import tokenize_question

stopwords = set(sw.words('english'))

logging.basicConfig(level=logging.INFO)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)
logger = logging.getLogger('guesser_buzzer_client')


class StupidBuzzer:

    def __init__(self):
        self.step = 0

    def new_round(self):
        self.step = 0

    def buzz(self, guesses):
        self.step += 1
        if self.step > 40:
            return [1, 0]
        else:
            return [0, 1]


class GuesserBuzzer:

    def __init__(self, buzzer_model_dir='data/neo_0.npz'):
        self.buzzer = StupidBuzzer()

        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.matches = []

    def new_question(self, qid):
        self.buzzer.new_round()
        self.ok_to_buzz = True
        self.answer = ''
        self.guesses = []
        self.matches = []

    def buzz(self, tokens, position):
        text = ' '.join(tokens)

        guesses = requests.post(
            'http://0.0.0.0:6000/api/centaur_answer_question',
            data={'text': text},
        ).json()

        buzz_scores = [0, 1]  # [wait, buzz]
        if self.ok_to_buzz:
            buzz_scores = self.buzzer.buzz(guesses)
            if isinstance(buzz_scores, np.ndarray):
                buzz_scores = buzz_scores.tolist()

        guesses = sorted(guesses.items(), key=lambda x: x[1])[::-1]
        self.guesses = guesses
        if len(guesses) > 0:
            self.answer = guesses[0][0]

        self.matches = requests.post(
            'http://0.0.0.0:6000/api/get_highlights',
            data={'text': text},
        ).json()

        text_highlight, tokenized_matches, matches_highlight = self.get_matched(tokens, position, self.matches)
        self.text_highlight = text_highlight
        self.tokenized_matches = tokenized_matches
        self.matches_highlight = matches_highlight

        return buzz_scores

    def get_matched(self, tokens, position, matches):
        '''
        For a (partial) question and a list of matched documents (with highlights)
        Args:
            tokens List[str]
            position (int): so the partial question is `tokens[:position]`
            matches: list of matches
        '''
        matches = matches['wiki'][:4]
        # matches = matches['qb'][:2] + matches['wiki'][:2]

        # find words highligted in the matches
        highlighted_words = set()  # words highlighted in the matches
        for match in matches:
            soup = BeautifulSoup(match, features='html.parser')
            match = [
                x.text.lower() for x in soup.find_all('em')
                if x.text.lower() not in stopwords and len(x.text) > 2
            ]
            highlighted_words.update(match)

        # find the highlighted words in the question
        matched_words = set()  # words matched in the question
        text_highlight = []  # mark highlight or not in the displayed text
        for ts in tokens[:position]:
            matched = [t in highlighted_words for t in ts]
            text_highlight.append(any(matched))
            matched_words.update(t for t, m in zip(ts, matched) if m)

        # mark words in the matches
        tokenized_matches = []
        matches_highlight = []
        for m in matches:
            tokenized_matches.append([])
            matches_highlight.append([])
            m = m.replace('<em>', '__').replace('</em>', ' ')
            for word in m.split():
                if not word.startswith('__'):
                    tokenized_matches[-1].append(word)
                    matches_highlight[-1].append(False)
                else:
                    word = word[2:]  # remove __ prefix
                    ts = tokenize_question(word)
                    matched = [t in matched_words for t in ts]
                    matches_highlight[-1].append(any(matched))
                    tokenized_matches[-1].append(word)
        return text_highlight, tokenized_matches, matches_highlight


if __name__ == '__main__':
    # factory = WebSocketClientFactory(u"ws://play.qanta.org:9000")
    # factory.protocol = GuesserBuzzerProtocol
    # connectWS(factory)
    # reactor.run()
    pass
