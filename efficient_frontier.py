import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import numpy as np
import random
import time
import itertools
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

def add_noise(data, season= 2024, noise=4):
    data = data[data['season']==season].reset_index(drop=True)
    rng = np.random.default_rng()
    data['par_noise'] = data['par'] + rng.normal(0, noise, size=len(data))
    return data

# Simulate a draft based on the points above replacement
# par_data must be sorted by season and par
def sim_snake_draft(teams,par_data,season=2024):
    team_counter = {'QB':0, 'RB':0, 'WR':0,'TE':0}
    counters = []
    rosters = []
    par_data = par_data[par_data['season'] == season].reset_index(drop=True)
    for _ in range(teams):
        counters.append(team_counter.copy())
        rosters.append([])
    rounds = team_composition['QB'] + team_composition['RB'] + team_composition['WR'] + team_composition['TE']
    
    for r in range(rounds):
        for team in range(teams):
            # Reverse order for odd rounds
            if r % 2 == 1:
                team = teams - 1 - team
            # Find next best player
            no_pick = True
            pointer = 0
            while no_pick:
                next_pick = par_data.iloc[pointer]
                if counters[team][next_pick['position']] < team_composition[next_pick['position']]:
                    no_pick = False
                    counters[team][next_pick['position']] += 1
                    rosters[team].append(next_pick['player_id'])
                    #print(f"Team {team} picks {next_pick['player_name']}")
                    par_data = par_data.drop(index=pointer)
                    par_data = par_data.reset_index(drop=True)
                else:
                    pointer += 1
    return rosters

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

def var_test():
    rng = np.random.default_rng()
    alpha = 3
    u2 = 0.0
    u1 = u2 + alpha
    e = 200
    s1 = 2
    s2 = e*s1*s1
    primary = rng.normal(u1,s1*s1,10000)
    secondary = rng.normal(u2,s2,10000)
    wins = secondary>primary
    print(np.sum(wins))

def main():
    identity, weekly, yearly, overall = load_data()
    overall = overall.merge(identity, on='player_id', how='left')
    # Calculate replacement stats
    replacement = replacement_stats(overall)
    
    # Calculate points above replacement
    par_results = par(overall, replacement)
    # real players only
    par_results = par_results[par_results['position'].isin(['QB','RB','WR','TE'])]
    SZN = [2019,2020,2021,2022,2023,2024]
    v,p,w = [],[],[]
    for i in range(100):
        season = random.sample(SZN,1)
        season = season[0]
        season_results = add_noise(par_results,season).sort_values(by='par_noise', ascending=False).reset_index(drop=True)
        rosters = sim_snake_draft(TEAMS,season_results,season)
        v.extend(team_variance(rosters,weekly,season))
        p.extend(total_points(rosters,weekly,season))
        w.extend(find_wins(sim_season(rosters,weekly,season)))
    outcomes = pd.DataFrame({"points":p,"variance":v,"wins":w})
    fig = px.scatter(outcomes,x='variance',y='wins')
    fig.write_image('figures/E-V.png')
    
if __name__ == "__main__":
    var_test() 