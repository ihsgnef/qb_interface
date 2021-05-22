import os
import json
import altair as alt
import pandas as pd
from centaur.db.session import SessionLocal
from centaur.models import Record, Player
from centaur.utils import EXPLANATIONS, ID_TO_CONFIG

alt.data_transformers.disable_max_rows()
alt.renderers.enable('mimetype')

spring_novice_email_list = [
    'Brandonisqiu@gmail.com',
    'alexakridge2@gmail.com',
    'alexbenjaminjacob@outlook.com',
    'avi.a.mehta@gmail.com',
    'chuang.grace@gmail.com',
    'clement.aldebert.21@gmail.com',
    'dn285@cornell.edu',
    'donalishere@gmail.com',
    'eb.wolf@verizon.net',
    'eyhung@gmail.com',
    'jeanrw@live.com',
    'jordan.davidsen@yale.edu',
    'mrbolesclassroom@gmail.com',
    'ned.tagtmeier@gmail.com',
    'tonychen2001@gmail.com',
]


def save_chart_and_pdf(chart, path):
    chart.save(f'{path}.json')
    os.system(f'vl2vg {path}.json | vg2pdf > {path}.pdf')


def fig_cumulative_ew_by_visualization(path: str):
    '''
    Cumulative EW score broken down by visualization.
    '''
    session = SessionLocal()
    email_to_records = {}
    for email in spring_novice_email_list:
        doppelgangers = session.query(Player).filter(Player.email == email)
        doppelgangers = [x for x in doppelgangers if len(x.records) > 0]
        doppelgangers = sorted(doppelgangers, key=lambda x: x.records[-1].date)
        email_to_records[email] = []
        for x in doppelgangers:
            email_to_records[email] += x.records

    max_n_records = max(len(x) for x in email_to_records.values())

    source = {}
    for i in range(max_n_records):
        source[i] = {'index': 1}
        for exp in EXPLANATIONS:
            source[i][exp] = 0

    for email, records in email_to_records.items():
        for i, r in enumerate(records):
            if r.ew_score is None:
                continue
            config = json.loads(r.explanation_config)
            for exp, enabled in config.items():
                if enabled and exp in source[i]:
                    source[i][exp] += r.ew_score

    rows = []
    for i, row in source.items():
        rows.append(row)

    source = pd.DataFrame(rows)
    source = source.cumsum()
    source = source.melt('index', var_name='visualization', value_name='ew_cumsum')

    chart = alt.Chart(source).mark_line().encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('ew_cumsum:Q', title='Cummulative EW'),
        color=alt.Color(
            'visualization:N',
            title='Visualization',
            legend=alt.Legend(labelFont='courier'),
        ),
    )
    save_chart_and_pdf(chart, f'{path}/spring_novice_visualization_cumulative_ew')


def fig_visualization_cumulative_count(path: str):
    '''
    Cumulative count of each individual visualization.
    '''
    session = SessionLocal()
    email_to_records = {}
    for email in spring_novice_email_list:
        doppelgangers = session.query(Player).filter(Player.email == email)
        doppelgangers = [x for x in doppelgangers if len(x.records) > 0]
        doppelgangers = sorted(doppelgangers, key=lambda x: x.records[-1].date)
        email_to_records[email] = []
        for x in doppelgangers:
            email_to_records[email] += x.records

    max_n_records = max(len(x) for x in email_to_records.values())

    source = {}
    for i in range(max_n_records):
        source[i] = {'index': 1}
        for exp in EXPLANATIONS:
            source[i][exp] = 0

    for email, records in email_to_records.items():
        for i, r in enumerate(records):
            config = json.loads(r.explanation_config)
            for exp, on_or_off in config.items():
                if exp in source[i]:
                    source[i][exp] += on_or_off

    rows = []
    for i, row in source.items():
        rows.append(row)

    source = pd.DataFrame(rows)
    source = source.cumsum()
    source = source.melt('index', var_name='visualization', value_name='count_cumsum')

    chart = alt.Chart(source).mark_line().encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('count_cumsum:Q', title='Cummulative Count'),
        color=alt.Color(
            'visualization:N',
            title='Visualization',
            legend=alt.Legend(labelFont='courier'),
        ),
    )
    save_chart_and_pdf(chart, f'{path}/spring_novice_visualization_cumulative_count')


if __name__ == '__main__':
    path = '/Users/shifeng/workspace/centaur/figures'
    fig_visualization_cumulative_count(path)
    fig_cumulative_ew_by_visualization(path)
