#!/usr/bin/env python
# coding: utf-8
import os
import pickle
import pathlib
import itertools
import multiprocessing
import numpy as np
import pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed
from plotnine import ggplot, aes, geom_density, geom_line, \
    facet_grid, theme, theme_light, xlim, \
    element_text, element_blank, element_rect, element_line

from db import QBDB
from util import QBQuestion
from expected_wins import ExpectedWins

FIG_DIR = 'auto_fig'
pathlib.Path(FIG_DIR).mkdir(exist_ok=True)


class theme_fs(theme_light):
    """
    A theme similar to :class:`theme_linedraw` but with light grey
    lines and axes to direct more attention towards the data.

    Parameters
    ----------
    base_size : int, optional
        Base font size. All text sizes are a scaled versions of
        the base font size. Default is 11.
    base_family : str, optional
        Base font family.
    """

    def __init__(self, base_size=11, base_family='DejaVu Sans'):
        theme_light.__init__(self, base_size, base_family)
        self.add_theme(theme(
            axis_ticks=element_line(color='#DDDDDD', size=0.5),
            panel_border=element_rect(fill='None', color='#838383', size=1),
            strip_background=element_rect(fill='#DDDDDD', color='#838383', size=1),
            strip_text_x=element_text(color='black'),
            strip_text_y=element_text(color='black', angle=-90),
            legend_key=element_blank(),
        ), inplace=True)


def apply_parallel(f, groupby):
    # helper function that applies f to each group in the groupby object
    return Parallel(n_jobs=multiprocessing.cpu_count())(
        delayed(f)(group) for name, group in tqdm(groupby))


"""
1. load questions and records, create records df
"""
with open('data/pace_questions.pkl', 'rb') as f:
    questions = pickle.load(f)
    questions = {q.qid: q for q in questions}

db = QBDB('data/db.sqlite.20181116')
df = pd.DataFrame(db.get_records())
EW = ExpectedWins()
TOOLS = ['guesses', 'highlight', 'matches']


""""
2. filter df
drop rows with NaN
count the number of records for each player
remove players with fewer than min_player_records records
"""
min_player_records = 30
df = df.dropna()
player_record_count = df.player_id.value_counts()
player_record_count_df = pd.DataFrame({
    'player_id': player_record_count.index,
    'player_record_count': player_record_count.values
})
df = df.set_index('player_id').join(player_record_count_df.set_index('player_id')).reset_index()
df = df[df['player_record_count'] > min_player_records]


"""
3. compute EW score for each record
"""
def get_ew(row):
    text = questions[row.question_id].raw_text
    return row.result * EW.score(row.position_buzz, len(text))


df['ew'] = df.apply(get_ew, axis=1)


"""
4. plot accumulated EW against number of questions answered for each user
"""
fig_name = 'ew_player_growth.pdf'

def get_group_features(g):

    return (
        g.record_id.tolist(),
        g.reset_index().index.tolist(),
        # np.cumsum(g.result.tolist()).tolist(),
        np.cumsum(g.ew.tolist()).tolist(),
    )


feature_names = [
    'question_number',
    'accumulated_reward',
]
features = apply_parallel(get_group_features, df.groupby('player_id'))
features = zip(*features)
features = [itertools.chain(*x) for x in features]
index, features = list(features[0]), features[1:]
features = [{k: v for k, v in zip(index, fs)} for fs in features]
for fn, fs in zip(feature_names, features):
    df[fn] = df['record_id'].map(fs)

p = (
    ggplot(df)
    + geom_line(
        aes(
            x='question_number',
            y='accumulated_reward',
            color='player_id',
            fill='player_id'
        )
    )
    + theme_fs()
    + theme(
        legend_position="none"
    )

)
p.save(os.path.join(FIG_DIR, fig_name))


"""
5. density plot of EW w/wo each tool
"""
fig_name = 'ew_density_on_off.pdf'

plot_df = {
    'EW': [],
    'Tool': [],
    'Enabled': [],
}
for row in df.itertuples():
    for tool, enabled in row.enabled_tools.items():
        plot_df['EW'].append(row.ew)
        plot_df['Tool'].append(tool)
        plot_df['Enabled'].append('On' if enabled else 'Off')
plot_df = pd.DataFrame(plot_df)

p = (
    ggplot(plot_df)
    + geom_density(
        aes(
            x='EW',
            fill='Enabled',
        ),
        alpha=0.5,
    )
    + facet_grid('Tool ~ .')
    + theme_fs()
    + theme(
        aspect_ratio=0.5,
        axis_text_x=element_text(size=16),
        axis_text_y=element_text(size=16),
        axis_title_x=element_text(size=16),
        axis_title_y=element_blank(),
        legend_text=element_text(size=16),
        legend_title=element_blank(),
        strip_text=element_text(size=16),
    )
)
p.save(os.path.join(FIG_DIR, fig_name))


"""
6. density plot of buzzing position by result w/wo each tool
"""
fig_name = 'buzz_density_on_off.pdf'

def get_relative_position(row):
    text = questions[row.question_id].raw_text
    return row.position_buzz / len(text)


df['relative_position'] = df.apply(get_relative_position, axis=1)

plot_df = {
    'Tool': [],
    'Enabled': [],
    'Position': [],
    'Result': [],
}
for row in df.itertuples():
    for tool, enabled in row.enabled_tools.items():
        plot_df['Tool'].append(tool)
        plot_df['Enabled'].append('on' if enabled else 'off')
        plot_df['Position'].append(row.relative_position)
        plot_df['Result'].append('Correct' if row.result else 'Wrong')
plot_df = pd.DataFrame(plot_df)

p = (
    ggplot(plot_df)
    + geom_density(
        aes(
            x='Position',
            fill='Enabled'
        ),
        alpha=0.7
    )
    + facet_grid('Tool ~ Result')
    + xlim(0, 1)
    + theme_fs()
    + theme(
        aspect_ratio=0.6,
        axis_title_x=element_text(size=16),
        axis_title_y=element_text(size=16),
        legend_text=element_text(size=16),
        legend_title=element_blank(),
        strip_text=element_text(size=16),
    )
)
p.save(os.path.join(FIG_DIR, fig_name))
