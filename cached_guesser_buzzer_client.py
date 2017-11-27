import json
import logging
import numpy as np
import chainer
from tqdm import tqdm

from qanta.config import conf
from qanta.guesser.abstract import AbstractGuesser
from qanta.guesser.experimental.elasticsearch_instance_of import ElasticSearchWikidataGuesser
from qanta.new_expo.agent import RNNBuzzer
from qanta.experimental.get_highlights import get_highlights, color

from guesser_buzzer_client import GuesserBuzzer, get_color

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
            scores = guesser_buzzer.buzz(sentence)
            buzzes.append(scores)
            answers.append(guesser_buzzer.answer)
            color = get_color(np.random.uniform())
            matches = get_highlights(sentence)
            evidences.append({'highlight': color, 'guesses': guesser_buzzer.guesses,
                'matches': matches})
        records[qid] = {'answer': answers, 'buzz': buzzes, 'evidence': evidences}
    
    with open('data/guesser_buzzer_cache.json', 'w') as f:
        f.write(json.dumps(records))

def test():
    with open('data/guesser_buzzer_cache.json', 'r') as f:
        records = json.loads(f.read())

    for record in records.values():
        highlights = record['evidence'][-1]['matches']
        for x in highlights['wiki']:
            print('WIKI|' + x.replace('<em>', color.RED).replace('</em>', color.END))
        for x in highlights['qb']:
            print('QUIZ|' + x.replace('<em>', color.RED).replace('</em>', color.END))

if __name__ == '__main__':
    test()
