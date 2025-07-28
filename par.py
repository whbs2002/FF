import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import plotly.figure_factory as ff
import time
import itertools
COLORS = ['#1F659E','#F59C22','#17A86A','#F55E22']
def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    
    return identity, weekly, yearly, overall

# will return the ith largest value in a group, or 0 if there are not enough values
def ith_largest_or_zero(group, i):
    top_i = group.nlargest(i)
    if len(top_i) < i:
        return 0
    return top_i.iloc[-1]

# find stats for replacement player
def replacement_stats(data):
    replacement = {}
    for pos in ['QB', 'RB', 'WR', 'TE', 'K']:
        replacement[pos] = int(last_pos(pos))
    return (data
        .groupby(['season','position'])['ppg']
        .apply(lambda x: ith_largest_or_zero(x, replacement[x.name[1]]))
        .reset_index())

# calculate points above replacement for each player
def par(data, replacement):
    data = data.merge(replacement, on=['season', 'position'], how='left', suffixes=('', '_replacement'))
    data['par'] = data['ppg'] - data['ppg_replacement']
    data = data.drop(columns=['ppg_replacement']) 
    return data[['player_id', 'player_name','season', 'position', 'ppg', 'par']].sort_values(by=['season', 'par'], ascending=[False, False]).reset_index(drop=True)

# Creates density plots for groups of positions
def density_plots(groups, val_col, file_name):
    labels = []
    data = []
    for name,group in groups:
        labels.append(name)
        data.append(group[val_col].to_numpy())
    fig = ff.create_distplot(data,labels,colors=COLORS,show_hist=False, bin_size=10)
    fig.update_layout(
        font=dict(size=20)
    )
    fig.update_xaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey'
    )
    fig.write_html(file_name)
    fig.write_image(file_name.replace('.html', '.png'))

# All players over a certain points limit
def limits_hist(yearly,player_identity, type,years=(2019,2025), limit = 0.0):
    positions = ['QB','WR','RB','TE']
    if type == 'ppr': 
        points = 'fantasy_points_ppr'
        file_name = 'figures/points_limit_ppr.html' 
    elif type == 'par':
        points = 'par'
        file_name = 'figures/points_limit_par.html'
    else: 
        points = 'fantasy_points'
        file_name = 'figures/points_limit_standard.html'
    year_list = [i for i in range(years[0],years[1])]
    yearly = yearly[yearly['season'].isin(year_list)]
    yearly = yearly[yearly[points]>limit]
    yearly = yearly.merge(player_identity, on='player_id',suffixes=('','_x'))
    yearly = yearly[yearly['position'].isin(positions)]
    grouped = yearly.groupby('position')
    density_plots(grouped, points, file_name)

# The top n players in a position for a given year
def top_n_hist(yearly,player_identity,type,years=(2019,2025),n=30):
    positions = ['QB','WR','RB','TE']
    if type == 'ppr': 
        points = 'fantasy_points_ppr'
        file_name = 'figures/points_n_ppr.html' 
    elif type == 'par':
        points = 'par'
        file_name = 'figures/points_n_par.html'
    else: 
        points = 'fantasy_points'
        file_name = 'figures/points_n_standard.html'
    year_list = [i for i in range(years[0],years[1])]
    yearly = yearly[yearly['season'].isin(year_list)]
    yearly = yearly.merge(player_identity, on='player_id',suffixes=('','_x'))
    yearly = yearly[yearly['position'].isin(positions)]
    grouped = yearly.groupby(['position','season'])
    top = grouped.apply(lambda x: x.nlargest(n,points)).reset_index(drop=True)
    grouped = top.groupby('position')
    density_plots(grouped, points, file_name)

def top_rounds_pos(stats,rounds=2,years=(2019,2025)):
    n = rounds* TEAMS
    positions = ['QB','WR','RB','TE']
    stats = stats[stats['season'].isin([i for i in range(years[0],years[1])])]
    top = stats[stats['position'].isin(positions)]
    top = top.groupby(['season']).apply(lambda x: x.nlargest(n,'par')).reset_index(drop=True)
    top = top.groupby(['season'])['position'].value_counts()
    top = top.reset_index(name='count')
    fig = px.area(top,x='season',y='count',color='position', color_discrete_map={'QB':COLORS[0], 'RB':COLORS[1], 'TE':COLORS[2],'WR':COLORS[3]}, line_group='position')
    fig.update_layout(
        font=dict(size=20)
    )
    fig.write_image('figures/top_rounds_pos.png',width=1400,height=1000)
    fig.write_html('figures/top_rounds_pos.html')

def main():
    identity, weekly, yearly, overall = load_data()
    overall = overall.merge(identity, on='player_id', how='left')
    # Calculate replacement stats
    replacement = replacement_stats(overall)
    
    # Calculate points above replacement
    par_results = par(overall, replacement)
    # Print results
    file = open('data/points_above_replacement.csv', 'w')
    file.write(par_results.to_csv(index=False))
    file.close()

    limits_hist(yearly,identity,type='ppr',limit=17.0)
    top_n_hist(yearly,identity,type='ppr')

    par_results['par'] = par_results['par']*17.0
    limits_hist(par_results,identity,type='par',limit=-200)
    top_n_hist(par_results,identity,type='par')

    top_rounds_pos(par_results,rounds=2,years=(1999,2025))



if __name__ == "__main__":
    main() 