import re
import json
import logging
import numpy as np
import chainer
from tqdm import tqdm
from bs4 import BeautifulSoup

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer
from qanta.experimental.get_highlights import get_highlights, color

from guesser_buzzer_client import GuesserBuzzer, get_color

def get_matched(text, matches):
    # text is the sentence to be highlighted
    # matches is a list of sentences with <em> tags
    # find all words in text that appear in <em> tags
    matched_words = set()
    for match in matches:
        # merge consecutive matches
        match = match.replace('</em> <em>', ' ')
        soup = BeautifulSoup(match)
        # add space at the beginning to avoid matching subword
        match = [' ' + x.text for x in soup.find_all('em')]
        matched_words.update(match)

    text = ' ' + text # avoid matching subword
    matched_segments = [] # pairs of (start, end)
    for matched in list(matched_words):
        starts = [m.start() for m in re.finditer(matched, text)]
        if len(starts) == 0:
            continue
        for start in starts:
            # first +1 to remove the matched space
            matched_segments.append((start + 1, start + len(matched)))

    matched_segments = sorted(matched_segments, key=lambda x: x[1])
    merged_segments = []
    curr = (0, 0)
    for start, end in matched_segments:
        if curr[1] <= start:
            if curr[0] < curr[1]:
                merged_segments.append((curr[0], curr[1]))
            curr = (start, end)
        else:
            if curr[1] < end:
                curr = (curr[0], end)
    if curr[0] < curr[1]:
        merged_segments.append((curr[0], curr[1]))

    c1 = get_color(0.2)
    mold = '<span style="background-color: ' + c1 + '">{}</span>';
    highlighted = ''
    idx = 0
    for start, end in merged_segments:
        if idx < start:
            highlighted += text[idx: start]
        highlighted += mold.format(text[start: end])
        idx = end
    highlighted += text[idx:]
    return highlighted[1:] # remove the added space at the beginning
    
def main():
    guesser_buzzer = GuesserBuzzer()
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
    
    records = dict()
    for question in tqdm(questions):
        qid = question['qid']
        buzzes = []
        answers = []
        evidences = []
        text = question['text'].split()
        guesser_buzzer.new_question()
        for i, word in enumerate(text):
            sentence = ' '.join(text[:i])
            scores = guesser_buzzer.buzz(sentence)
            buzzes.append(scores)
            answers.append(guesser_buzzer.answer)
            matches = get_highlights(sentence)
            color = get_color(np.random.uniform())
            evidences.append({'highlight': color, 'guesses': guesser_buzzer.guesses,
                'matches': matches})
        records[qid] = {'answer': answers, 'buzz': buzzes, 'evidence': evidences}
    
    with open('data/guesser_buzzer_cache.json', 'w') as f:
        f.write(json.dumps(records))

def test():
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())

    with open('data/guesser_buzzer_cache.json', 'r') as f:
        records = json.loads(f.read())

    questions = {x['qid']: x for x in questions}
    qid, record = list(records.items())[40]
    text = questions[int(qid)]['text']
    matches = record['evidence'][20]['matches']['qb']
    highlighted = get_matched(text, matches)
    with open('tmp.html', 'w') as f:
        f.write(text + '</br>')
        f.write(highlighted)
    print(highlighted)
    
if __name__ == '__main__':
    test()
