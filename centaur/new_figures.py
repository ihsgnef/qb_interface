import os
import json
import altair as alt
import pandas as pd
from centaur.db.session import SessionLocal
from centaur.models import Record, Player
from centaur.utils import EXPLANATIONS, ID_TO_CONFIG

alt.data_transformers.disable_max_rows()
alt.renderers.enable('mimetype')


def save_chart_and_pdf(chart, path):
    chart.save(f'{path}.json')
    os.system(f'vl2vg {path}.json | vg2pdf > {path}.pdf')


def filter_player_spring_novice(player: Player):
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
    return player.email in spring_novice_email_list


def fig_cumulative_reward(path: str):
    '''
    Cumulative reward by number of examples, break down by condition.
    '''
    session = SessionLocal()
    players = [x for x in session.query(Player) if filter_player_spring_novice(x)]
    all_records = []
    for player in players:
        records = session.query(Record).filter(Record.player_id == player.id).order_by(Record.date)
        records = [x.__dict__ for x in records]
        for i, r in enumerate(records):
            r.pop('_sa_instance_state')
            r['index'] = i
            r['player_email'] = player.email
        all_records += records
    source = pd.DataFrame(all_records)

    condition_names = {
        'NoneFixedMediator': 'None-fixed',
        'EverythingFixedMediator': 'Everything-fixed',
        'RandomFixedMediator': 'Random-fixed',
        'RandomDynamicMediator': 'Random-dynamic',
        'SemiAutopilotMediator': 'Semi-autopilot',
        'BanditMediator': 'Mediated-dynamic',
    }
    source['condition'] = source['mediator_name'].apply(lambda x: condition_names[x])
    source['ew_cumsum'] = source.groupby(['player_email'])['ew_score'].cumsum()

    selection = alt.selection_multi(fields=['condition'], bind='legend')
    line = alt.Chart().mark_line().encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('mean(ew_cumsum):Q', title='Cummulative Reward (EW)'),
        color=alt.Color(
            'condition',
            title='Condition',
            legend=alt.Legend(labelFont='courier'),
        ),
        opacity=alt.condition(selection, alt.value(0.8), alt.value(0.2))
    )
    band = alt.Chart().mark_errorband(extent='ci').encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('ew_cumsum:Q', title='Cummulative Reward (EW)'),
        color=alt.Color(
            'condition',
            title='Condition',
            legend=alt.Legend(labelFont='courier'),
        ),
        opacity=alt.condition(selection, alt.value(0.4), alt.value(0.1))
    )

    chart = alt.layer(line, band, data=source).add_selection(selection)
    save_chart_and_pdf(chart, f'{path}/cumulative_ew')


def fig_config_cumulative_count(path: str):
    '''
    Cumulative count of each config selected by the mediator.
    '''
    source = []
    for i in range(60):
        source.append({'index': 1})
        for config in ID_TO_CONFIG:
            source[i][json.dumps(config)] = 0

    session = SessionLocal()
    players = [x for x in session.query(Player) if x.id.startswith('dummy')]
    for player in players:
        records = session.query(Record).filter(Record.player_id == player.id).order_by(Record.date)
        if records[0].mediator_name != 'BanditMediator':
            continue
        for i, r in enumerate(records):
            source[i][r.explanation_config] += 1

    source = pd.DataFrame(source)
    source = source.cumsum()
    source = source.melt('index', var_name='explanation_config', value_name='count_cumsum')
    chart = alt.Chart(source).mark_line().encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('count_cumsum:Q', title='Cummulative Count'),
        color=alt.Color(
            'explanation_config',
            title='explanation_config',
            legend=alt.Legend(labelFont='courier'),
        ),
    )
    save_chart_and_pdf(chart, f'{path}/mediated_config_cumulative_count')


def fig_explanation_cumulative_count(path: str):
    '''
    Cumulative count of each individual explanation, break down by condition.
    '''
    condition_names = {
        'NoneFixedMediator': 'None-fixed',
        'EverythingFixedMediator': 'Everything-fixed',
        'RandomFixedMediator': 'Random-fixed',
        'RandomDynamicMediator': 'Random-dynamic',
        'SemiAutopilotMediator': 'Semi-autopilot',
        'BanditMediator': 'Mediated-dynamic',
    }

    source = {}
    for i in range(60):
        for condition in condition_names.values():
            source[(i, condition)] = {'index': 1}
            for config in EXPLANATIONS:
                source[(i, condition)][config] = 0

    session = SessionLocal()
    players = [x for x in session.query(Player) if filter_player_spring_novice(x)]
    for player in players:
        records = session.query(Record).filter(Record.player_id == player.id).order_by(Record.date)
        condition = condition_names[records[0].mediator_name]
        for i, r in enumerate(records):
            config = json.loads(r.explanation_config)
            for exp, on_or_off in config.items():
                source[(i, condition)][exp] += on_or_off

    rows = []
    for i_condition, others in source.items():
        i, condition = i_condition
        others['index'] = i
        others['condition'] = condition
        rows.append(others)

    source = pd.DataFrame(rows)
    source = source.melt(['index', 'condition'], var_name='explanation', value_name='count')
    source['count_cumsum'] = source.groupby(['condition', 'explanation'])['count'].cumsum()

    chart = alt.Chart(source).mark_line().encode(
        alt.X('index:Q', title='Questions'),
        alt.Y('count_cumsum:Q', title='Cummulative Count'),
        color=alt.Color(
            'explanation',
            title='Explanation',
            legend=alt.Legend(labelFont='courier'),
        ),
    ).facet(
        facet=alt.Facet(
            'condition:N',
            title=None,
            header=alt.Header(labelFont='courier'),
        ),
        columns=3,
    )
    save_chart_and_pdf(chart, f'{path}/explanation_cumulative_count')


if __name__ == '__main__':
    path = '/Users/shifeng/workspace/centaur/figures'
    # fig_cumulative_reward(path)
    # fig_config_cumulative_count(path)
    fig_explanation_cumulative_count(path)
