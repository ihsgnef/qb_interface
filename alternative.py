from collections import defaultdict
alternative_answers = defaultdict(list)
alternative_answers.update({
'pankhurst': ['emmeline pankhurst'],
'huguenots': ['huguenot'],
'frederick the great': ['frederick ii', 'friedrich der größe'],
'victor emmanuel': ['victor emmanuel ii of italy'],
'les fleurs du mal': ['flower of evil', 'the flowers of evil'],
'cyrano de bergerac': ['cyrano de bergerac (play)'],
'newton (surname)': ['isaac newton', 'newton'],
'amedeo avogadro': ['avogadro constant'],
'aztec mythology': ['aztec', 'aztec mythology'],
'dualism': ['mind–body dualism', 'dualism (philosophy of mind)'],
'prelude (music)': ['prelude'],
'drum': ['drum kit'],
'adler': ['alfred adler', 'adler (surname)'],
'civil disobedience (thoreau)': ['civil disobedience'],
'option (finance)': ['option'],
'embargo act of 1807': ['embangro act of 1807', 'embargo act'],
'bimetallism': ['bi-metallism'],
'battle of midway': ['midway'],
'george iii of the united kingdom': ['george iii'],
'england': ['united kingdom'],
'battle of alesia': ['alesia'],
'battle of borodino': ['borodino'],
'otto von bismarck': ['otto eduard leopold', 'bismark'],
'inca empire': ['inca'],
'simón bolívar': ['simon bolivar'],
'mali empire': ['mali'],
'shang dynasty': ['shang'],
'abolitionism': ['abolition'],
'shield': ['shields'],
'mark twain': ['samuel clemens'],
'who\'s afraid of virginia woolf?': ["who's afraid of virginia woolf"],
'w. h. auden': ['wh auden', 'w h auden', 'auden'],
'saki': ['h. h. munro', 'hector hugh munro'],
'falstaff': ['sir john falstaff', 'john falstaff'],
'harold pinter': ['pinter'],
'mother courage and her children': ['mutter courage und ihre kinder'],
'the idiot': ['idiot', 'идио́т'],
'china': ['zhongguo', '中国'],
'confessions of a mask': ['仮面の告白', 'kamen no kokuhaku'],
'athol fugard': ['fugard'],
'orchidaceae': ['orchid', 'orchids'],
'calcium': ['ca'],
'iron': ['fe'],
'augustin-louis cauchy': ['cauchy'],
'sql': ['structured query language'],
'moons of jupiter': ['jovian moons'],
'invention of radio': ['radio'],
'muhammad\'s wives': ['mothers of the believers', 'أم المؤمنين', 'ummahat al-muminin'],
'falun gong': ['falwen tafa', '法轮功'],
'manichaeism': ['آیین مانی'],
'troy': ['ilium'],
'apology (plato)': ['apology'],
'the consolation of philosophy': ['de consolatione philosophiae'],
'edmund burke': ['burke'],
'friedrich nietzsche': ['nietzsche'],
'antonio vivaldi': ['vivaldi'],
'symphony no. 6 (beethoven)': ['beethoven symphny no.6'],
'poland': ['polska'],
'frank capra': ['capra'],
'athens': ['αθήνα', 'athina'],
'bird in space': ['pasărea în văzduh'],
'the magic flute': ['der zauberflöte'],
'is–lm model': ['investment-savings, liquidity-money'],
'bobo doll experiment': ['bobo doll'],
'rock (geology)': ['shale'],
'new york city': ['new york city', 'nyc'],
'borneo': ['kalimantan', 'pulau borneo'],
'nepal': ['नेपाल'],
'navajo': ['dine'],
'leicester city f.c.': ['leicester city'],
'civilization (series)': ['civilization', 'civilization v'],
'peter dinklage': ['peter dinklage'],
'sweden': ['sverige'],
'the twilight zone (1959 tv series)': ['the twilight zone', 'twilight zone'],
'1920s': ['twenties'],
'bicycle': ['bike'],
'dada': ['dadism'],
'tulip': ['tulipa gesneriana'],
'horse racing': ['horse race'],
'c. s. lewis': ['c.s lews', 'clive staples lewis'],
})

def create_alternatives:
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
    
def read_alternatives:
