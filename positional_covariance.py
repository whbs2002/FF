import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import random
import time
import itertools

pairs = ['QB-WR1','QB-RB1','QB-WR2','QB-RB2','RB1-RB2','WR1-WR2','QB-TE1']

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

# narrow down to WR1, WR2, TE1, RB1, RB2, QB1 and rename positions to match
def trim_players(data):
    data = (data
            .groupby(['season','position','recent_team'])['ppg']
            .nlargest(2))
    return data

# Group positions together
def groups(yearly,weekly,identity,overall):
    weekly = weekly[['player_id','week','fantasy_points_ppr']]
    yearly = yearly[['player_id','season','recent_team']]
    overall = overall[['player_id','ppg']]
    #identify relevant players
    data = yearly.merge(identity,on='player_id',how='left')
    data = data.merge(overall,on='player_id',how='left')
    print(data)
    data = trim_players(data)
    print(data)


# returns the index of the team that won each week
def sim_season(rosters, weekly,season=2024):
    weekly = weekly[weekly['season'] == season].reset_index(drop=True)
    weekly = weekly[['player_id', 'week', 'fantasy_points_ppr']]
    team_num = 0
    teams = weekly[['week']].drop_duplicates().reset_index(drop=True)
    for team in rosters:
        team_weekly = weekly[weekly['player_id'].isin(team)]
        team_weekly = team_weekly.groupby('week')['fantasy_points_ppr'].sum().reset_index()
        team_weekly.rename(columns={'fantasy_points_ppr': f'{team_num}'}, inplace=True)
        teams = teams.merge(team_weekly, on='week', how='left')
        team_num += 1
    return teams.sort_values(by='week').set_index('week')

# each team is a list of player ids
def team_variance(teams,weekly,season=2024):
    weekly = weekly[weekly['season'] == season].reset_index(drop=True)
    weekly = weekly[['player_id', 'week', 'fantasy_points_ppr']]
    variances = []
    for team in teams:
        team_weekly = weekly[weekly['player_id'].isin(team)]
        team_weekly = team_weekly.pivot(index='week',columns='player_id', values='fantasy_points_ppr').fillna(0)
        n = len(team)
        cov_matrix = team_weekly.cov()
        var = np.ones(n).T @ cov_matrix @ np.ones(n)
        variances.append(var)
    return variances

# Model wins as above or below mean points for the week
def find_wins(teams):
    scores = teams.values
    wins_matrix = (scores[:, :, None] > scores[:, None, :]).sum(axis=2)
    wins = pd.DataFrame(wins_matrix,index=teams.index,columns=teams.columns)
    sum_wins = wins.sum(axis=0)
    return list(sum_wins)

def total_points(rosters,weekly,season=2024):
    weekly = weekly[weekly['season']==season].reset_index(drop=True)
    points = []
    for team in rosters:
        team_weekly = weekly[weekly['player_id'].isin(team)]
        points.append(team_weekly['fantasy_points_ppr'].sum())
    return points

def graph_season(teams):
    fig = px.line(teams,x='week', y=teams.columns[1:], title='Fantasy Points per Week')
    fig.write_image('figures/per_week.png')

def main():
    identity, weekly, yearly, overall = load_data()
    groups(yearly,weekly,identity,overall)
    
if __name__ == "__main__":
    main()