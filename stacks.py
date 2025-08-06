import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import time
import itertools
import numpy as np


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
def all_stacks(top_players, positions, season=2024,qb_limit=32):
    top_players = top_players[top_players['season']==season]
    top_players = top_players[top_players.position.isin(positions)]
    top_players = top_players[['recent_team','player_id','position','ppg']].drop_duplicates().sort_values(by='position',ascending=True).reset_index(drop=True)
    if 'QB1' in positions:
        mask = top_players['position'] != 'QB1'
        top_qbs = top_players[top_players['position']=='QB1'].nlargest(qb_limit,'ppg')
        top_players = pd.concat((top_players[mask],top_qbs)).sort_index()
    teams = top_players.groupby(['recent_team'])['player_id'].apply(lambda x: tuple(x)).tolist()
    return teams
    
# list of all players at a given position in a season
def all_position(top_players, position, season=2024):
    top_players = top_players[top_players['season']==season]
    top_players = top_players[top_players.position==position]
    return list(top_players['player_id'].drop_duplicates())

# Model wins as number of other teams beaten that week
def find_wins(teams):
    scores = teams.values
    wins_matrix = (scores[:, :, None] > scores[:, None, :]).sum(axis=2)
    wins = pd.DataFrame(wins_matrix,index=teams.index,columns=teams.columns)
    sum_wins = wins.sum(axis=0)
    return list(sum_wins)

def all_pairs(top_players, positions,yearly,season=2024):
    qbs = all_position(top_players,positions[0],season=season)
    wrs = all_position(top_players,positions[1],season=season)
    all_pairings = []
    yearly = yearly[yearly['season']==season].drop_duplicates().fillna(0.0).set_index('player_id')
    for pairing in itertools.product(qbs,wrs):
        A = yearly.loc[pairing[0]]['fantasy_points_ppr']
        B = yearly.loc[pairing[1]]['fantasy_points_ppr']
        points = A+B
        all_pairings.append([pairing[0],pairing[1],points])
    all_pairings = pd.DataFrame(data=all_pairings,columns=['QB','WR','points']).sort_values(by='points',ascending=False).reset_index(drop=True)
    return all_pairings

# compare stacks to other QB-WR pairings
# neighbors measures how many other pairings in each direction should be used for comparison
def compare_stacks(stacks,pairings,weekly,season=2024,neighbors=3,side="two"):
    stack_performance = []
    s_loc = []
    for s in stacks:
        # identify location of stack
        location = pairings.index[(pairings['QB'] == s[0]) & (pairings['WR'] == s[1])][0]
        s_loc.append(location)
    extreme = 0
    LEVEL = 10
    for i in range(len(stacks)):
        rank = pairings.shape[0]
        # Find neighboring non-stack neighbors
        s = stacks[i]
        idx = s_loc[i]
        after = min(2,rank-idx-1)
        before = min(neighbors,idx)
        # If we don't have enough on one side, compensate on the other
        remaining = neighbors*2 - (before + after)
        if remaining > 0:
            # Try to take more from after side
            extra_after = min(remaining, rank - idx - 1 - after)
            after += extra_after
            remaining -= extra_after
            # Whatever is left must come from before side
            extra_before = min(remaining, idx - before)
            before += extra_before
        nbors = []
        opponents = 0
        if side != "bot":
            for i in range(1,before+1):
                nbors.append((pairings.iloc[idx-i]['QB'],pairings.iloc[idx-i]['WR']))
                opponents +=1
        if side != "top":
            for i in range(1,after+1):
                nbors.append((pairings.iloc[idx+i]['QB'],pairings.iloc[idx+i]['WR']))
                opponents +=1
        # Calculate wins
        wins = 0
        for N in nbors:
            result = sim_season([N,s],weekly,season).values
            # calculate the occurrence of very good seasons
            if np.sum(result[:,1]>result[:,0]) > LEVEL:
                extreme += 1
            wins += np.mean(result[:,1]>result[:,0])/(opponents)
        # Add to the list
        stack_performance.append([s[0],s[1],wins])
    print(extreme)
    return stack_performance

def compare_top_n(stacks,pairings,weekly,n=5,season=2024):
    stack_performance = []
    s_loc = []
    for s in stacks:
        # identify location of stack
        location = pairings.index[(pairings['QB'] == s[0]) & (pairings['WR'] == s[1])][0]
        s_loc.append(location)
    # find the best n pairings
    top = []
    for i in range(n):
        top.append((pairings.iloc[i]['QB'],pairings.iloc[i]['WR']))
    for i in range(len(stacks)):
        # Find neighboring non-stack neighbors
        s = stacks[i]
        # Calculate wins
        wins = 0
        for N in top:
            result = sim_season([N,s],weekly,season).values
            wins += np.mean(result[:,1]>result[:,0])/(n)
        # Add to the list
        stack_performance.append([s[0],s[1],wins])
    return stack_performance

def find_winner(teams):
        return teams.groupby('week').apply(lambda x: x.idxmax(axis=1)).rename('winner').reset_index(drop=True)

def graph_season(teams):
    fig = px.line(teams,x='week', y=teams.columns[1:], title='Fantasy Points per Week')
    fig.write_image('figures/per_week.png')

# return n random pairings as tuples with QB first and WR second
def random_pairings(pairings,n):
    pairing_indices = np.random.choice(np.arange(10,pairings.shape[0],1), size=n, replace=False)
    return pairings.iloc[pairing_indices][['QB','WR']].apply(lambda x: tuple(x),axis=1).tolist()

def exp_stacks():
    identity, weekly, yearly, overall = load_data()
    identity, weekly, yearly, overall = load_data()
    top_players = groups(yearly,weekly,identity,overall)
    # Iterate through every QB1 WR1 pairings and find wins
    wins = []
    for szn in range(2002,2025):
        stacks = all_stacks(top_players, ('QB1','WR1'),season=szn,qb_limit=32)
        # get rid of all the tuples with just a WR in them. This line in unnecessary if qb_limit is 32
        stacks = [s for s in stacks if len(s)>1]
        all_pairings = all_pairs(top_players,('QB1','WR1'), yearly, season=szn)
        # Compare QB WR1 stacks with adjacent pairings
        outcome = compare_stacks(stacks,all_pairings,weekly,season=szn,side="top")
        outcome = pd.DataFrame(data=outcome,columns=['QB','WR','wins']).sort_values(by='wins',ascending=False).reset_index(drop=True)
        wins.append(outcome['wins'].agg('mean'))
    print(np.mean(np.array(wins)))

def exp_random():
    identity, weekly, yearly, overall = load_data()
    identity, weekly, yearly, overall = load_data()
    top_players = groups(yearly,weekly,identity,overall)
    # Iterate through every QB1 WR1 pairings and find wins
    wins = []
    for szn in range(2002,2025):
        all_pairings = all_pairs(top_players,('QB1','WR1'), yearly, season=szn)

        #code for randomly selecting WR pairings
        stacks = random_pairings(all_pairings,32)
        # Compare QB WR1 stacks with adjacent pairings
        outcome = compare_stacks(stacks,all_pairings,weekly,season=szn,side="top")
        outcome = pd.DataFrame(data=outcome,columns=['QB','WR','wins']).sort_values(by='wins',ascending=False).reset_index(drop=True)
        wins.append(outcome['wins'].agg('mean'))
    print(np.mean(np.array(wins)))

def exp_top():
    identity, weekly, yearly, overall = load_data()
    identity, weekly, yearly, overall = load_data()
    top_players = groups(yearly,weekly,identity,overall)
    # Iterate through every QB1 WR1 pairings and find wins
    wins = []
    for szn in range(2002,2025):
        stacks = all_stacks(top_players, ('QB1','WR1'),season=szn,qb_limit=32)
        # get rid of all the tuples with just a WR in them. This line in unnecessary if qb_limit is 32
        stacks = [s for s in stacks if len(s)>1]
        all_pairings = all_pairs(top_players,('QB1','WR1'), yearly, season=szn)

        # Compare QB WR1 stacks with best pairings
        outcome = compare_top_n(stacks,all_pairings,weekly,n=10,season=szn)
        outcome = pd.DataFrame(data=outcome,columns=['QB','WR','wins']).sort_values(by='wins',ascending=False).reset_index(drop=True)
        wins.append(outcome['wins'].agg('mean'))
    print(np.mean(np.array(wins)))
    wins = []
    for szn in range(2002,2025):
        all_pairings = all_pairs(top_players,('QB1','WR1'), yearly, season=szn)
        #code for randomly selecting QB-WR pairings
        stacks = random_pairings(all_pairings,50)
        # Compare random pairings with best pairings
        outcome = compare_top_n(stacks,all_pairings,weekly,n=10,season=szn)
        outcome = pd.DataFrame(data=outcome,columns=['QB','WR','wins']).sort_values(by='wins',ascending=False).reset_index(drop=True)
        wins.append(outcome['wins'].agg('mean'))
    print(np.mean(np.array(wins)))


if __name__ == "__main__":
    exp_stacks()
    exp_random()
    exp_top()