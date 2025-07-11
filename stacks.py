import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import time
import itertools


def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    
    return identity, weekly, yearly, overall


# narrow down to WR1, WR2, TE1, RB1, RB2, QB1 and rename positions to match
def trim_players(data):
    data['rank'] = (data
            .groupby(['season','position','recent_team'])['ppg']
            .rank(method='first',ascending=False)
            .astype('Int64'))
    
    data['position']= data['position'] + data['rank'].astype(str)
    data.drop(columns='rank')
    data = data[data.position.isin(['QB1','TE1','RB1','RB2','WR1','WR2'])]
    return data

# Group positions together
def groups(yearly,weekly,identity,overall):
    weekly = weekly[['player_id','week','fantasy_points_ppr','season']]
    yearly = yearly[['player_id','season','recent_team']]
    overall = overall[['player_id','ppg','season']]
    #identify relevant players
    data = yearly.merge(identity,on='player_id',how='left')
    data = pd.merge(left=data,right=overall,how='left',right_on=['player_id','season'],left_on=['player_id','season'])
    data = trim_players(data)
    data = pd.merge(left=data,right=weekly,how='left',right_on=['player_id','season'],left_on=['player_id','season'])
    return data

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

# Finds the all the stacks across a season
def all_stacks(top_players, positions, season=2024):
    top_players = top_players[top_players['season']==2024]
    top_players = top_players[top_players.position.isin(positions)]
    top_players = top_players[['recent_team','player_id','position']].drop_duplicates().reset_index(drop=True)
    teams = top_players.groupby(['recent_team'])['player_id'].apply(lambda x: tuple(x)).tolist()
    return teams
    
# list of all players at a given position in a season
def all_position(top_players, position, season=2024):
    top_players = top_players[top_players['season']==2024]
    top_players = top_players[top_players.position==position]
    return list(top_players['player_id'].drop_duplicates())

# Model wins as number of other teams beaten that week
def find_wins(teams):
    scores = teams.values
    wins_matrix = (scores[:, :, None] > scores[:, None, :]).sum(axis=2)
    wins = pd.DataFrame(wins_matrix,index=teams.index,columns=teams.columns)
    print(wins)
    sum_wins = wins.sum(axis=0)
    return list(sum_wins)

def all_pairs(top_players, positions,yearly,season=2024):
    qbs = all_position(top_players,positions[0],season=season)
    wrs = all_position(top_players,positions[1],season=season)
    all_pairings = []
    yearly = yearly[yearly['season']==season].drop_duplicates().fillna(0.0).set_index('player_id')
    for pairing in itertools.product(qbs,wrs):
        A = yearly.loc[pairing[0]]['fantasy_points_ppr']
        B= yearly.loc[pairing[1]]['fantasy_points_ppr']
        points = A+B
        all_pairings.append([pairing[0],pairing[1],points])
    all_pairings = pd.DataFrame(data=all_pairings,columns=['QB','WR','points'])
    return all_pairings

def find_winner(teams):
        return teams.groupby('week').apply(lambda x: x.idxmax(axis=1)).rename('winner').reset_index(drop=True)

def graph_season(teams):
    fig = px.line(teams,x='week', y=teams.columns[1:], title='Fantasy Points per Week')
    fig.write_image('figures/per_week.png')

def main():
    identity, weekly, yearly, overall = load_data()
    identity, weekly, yearly, overall = load_data()
    top_players = groups(yearly,weekly,identity,overall)
    # Iterate through every QB1 WR1 pairings and find total points
    SZN = 2023
    stacks = all_stacks(top_players, ('QB1','WR1'),season=SZN)
    all_pairings = all_pairs(top_players,('QB1','WR1'), yearly, season=SZN)
    print(all_pairings)
    # Compare QB WR1 stacks with adjacent non-stack pairings
    
if __name__ == "__main__":
    main()