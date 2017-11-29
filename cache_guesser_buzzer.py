import re
import json
import pickle
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
    for question in tqdm(questions):
        qid = question['qid']
        text = question['text'].split()
        guesser_buzzer.new_question(qid)
        records[qid] = dict()
        for i, word in enumerate(text):
            sentence = ' '.join(text[:i])
            buzz_scores = guesser_buzzer.buzz(sentence, i)
            records[qid][i] = {
                'buzz_scores': buzz_scores,
                'answer': guesser_buzzer.answer,
                'evidence': guesser_buzzer.evidence}
    
    with open('data/guesser_buzzer_cache.pkl', 'wb') as f:
        pickle.dump(records, f)

def main2():
    with open('data/guesser_buzzer_cache.pkl', 'rb') as f:
        records = pickle.load(f)

    with open('data/sample_questions.json', 'r') as f:
        questions = json.loads(f.read())
    questions = {x['qid']: x for x in questions}

    new_records = dict()
    for qid, record in tqdm(records.items()):
        text = questions[qid]['text']
        new_records[qid] = dict()
        for i, row in record.items():
            matches = row['evidence']['matches']
            top_matches = matches['qb'][:1] + matches['wiki'][:1]
            highlighted = get_matched(text, top_matches)
            row['evidence']['highlight'] = highlighted
            new_records[qid][i] = row
    
    with open('data/guesser_buzzer_cache1.pkl', 'wb') as f:
        pickle.dump(new_records, f)


def test():
    with open('data/guesser_buzzer_cache.pkl', 'rb') as f:
        records = pickle.load(f)

    record = list(records.values())[0]
    evidence = record['evidence']
    with open('tmp.html', 'w') as f:
        for entry in evidence:
            f.write(entry['highlight'] + '</br>')
    
if __name__ == '__main__':
    main()
