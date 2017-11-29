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

from guesser_buzzer_client import GuesserBuzzer, get_matched


    
def main():
    guesser_buzzer = GuesserBuzzer()
    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
    
    records = dict()
    for question in tqdm(questions[:10]):
        qid = question['qid']
        buzzes = []
        answers = []
        evidences = []
        text = question['text'].split()
        guesser_buzzer.new_question()
        for i, word in enumerate(text):
            sentence = ' '.join(text[:i])
            scores = guesser_buzzer.buzz(sentence, i)
            buzzes.append(scores)
            answers.append(guesser_buzzer.answer)
            matches = get_highlights(sentence)
            top_matches = matches['qb'][:2] + matches['wiki'][:2]
            highlighted = get_matched(' '.join(text[:i]), top_matches)
            evidences.append({'highlight': highlighted, 
                              'guesses': guesser_buzzer.guesses,
                              'matches': matches})
        records[qid] = {'answer': answers, 
                        'buzz': buzzes, 
                        'evidence': evidences}
    
    with open('data/guesser_buzzer_cache.json', 'w') as f:
        f.write(json.dumps(records))

def test():
    with open('data/guesser_buzzer_cache.json', 'r') as f:
        records = json.loads(f.read())

    record = list(records.values())[0]
    evidence = record['evidence']
    with open('tmp.html', 'w') as f:
        for entry in evidence:
            f.write(entry['highlight'] + '</br>')
    
if __name__ == '__main__':
    test()
