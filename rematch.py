import json
import pickle
from bs4 import BeautifulSoup
from nltk.corpus import stopwords as sw
import spacy
from tqdm import tqdm
from multiprocessing import Pool

nlp = spacy.load('en')
stopwords = set(sw.words('english'))


highlight_color = '#ecff6d'
highlight_prefix = '<span style="background-color: ' + highlight_color + '">'
highlight_suffix = '</span>'

with open('data/sample_questions.json', 'r') as f:
    questions = json.loads(f.read())
    questions = {x['qid']: x for x in questions}

with open('data/guesser_buzzer_cache.pkl', 'rb') as f:
    records = pickle.load(f)

def get_matched(words, matches):
    match_words = set()
    for i, match in enumerate(matches):
        match = match.replace(highlight_prefix, '__')
        match = match.replace(highlight_suffix, ' ')
        matches[i] = match.split()
        for x in match.split():
            if not x.startswith('__'):
                continue
            x = x[2:].lower()
            if x in stopwords:
                continue
            match_words.add(x)
    
    text_highlight = []
    matched_words = set()
    _words = [] # 
    for word in words:
        _words.append(word.text)
        if word.lower_ in match_words:
            text_highlight.append(True)
            matched_words.add(word.lower_)
        else:
            text_highlight.append(False)

    _matches = []
    matches_highlight = []
    for i, match in enumerate(matches):
        _matches.append([])
        matches_highlight.append([])
        for x in match:
            if not x.startswith('__'):
                _matches[i].append(x)
                matches_highlight[i].append(False)
                continue
            x = x[2:]
            _matches[i].append(x)
            matches_highlight[i].append(x.lower() in matched_words)

    return _words, text_highlight, _matches, matches_highlight

def main():
    _records = dict()
    pos_maps = dict()
    for qid, record in tqdm(records.items()):
        _records[qid] = dict()
        text = questions[qid]['text']
        words = nlp(text)
        text = [nlp(x) for x in text.split()]
        pos_map = dict() # map from text.split() to word

        curr = 0
        for i, seg in enumerate(text):
            curr += len(seg)
            pos_map[i] = curr - 1
        pos_map[len(text)] = len(words)
        pos_maps[qid] = pos_map

        for pos in record:
            guesses = record[pos]['evidence']['guesses']
            for i, (g, s) in enumerate(guesses):
                    guesses[i] = (g.replace('_', ' '), s)
            _records[qid][pos] = {
                    'answer': record[pos]['answer'],
                    'buzz_scores': record[pos]['buzz_scores'],
                    'guesses': guesses
                    }
            ws, ws_hi, ms, ms_hi = get_matched(
                    words[:pos_map[pos]], record[pos]['evidence']['matches'])
            _records[qid][pos]['text'] = ws
            _records[qid][pos]['text_highlight'] = ws_hi
            _records[qid][pos]['matches'] = ms
            _records[qid][pos]['matches_highlight'] = ms_hi
    with open('data/guesser_buzzer_cache_rematches.pkl', 'wb') as f:
        pickle.dump(_records, f)

    with open('data/pos_maps.pkl', 'wb') as f:
        pickle.dump(pos_maps, f)
        

if __name__ == '__main__':
    main()
