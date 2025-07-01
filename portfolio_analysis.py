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

# Simulate a draft based on the points above replacement
def sim_draft(teams,par_data,season=2024,turns=True):
    team_counter = {'QB':0, 'RB':0, 'WR':0,'TE':0}
    counters = []
    rosters = []
    par_data = par_data[par_data['season'] == season].reset_index(drop=True)
    for _ in range(teams):
        counters.append(team_counter.copy())
        rosters.append([])
    rounds = team_composition['QB'] + team_composition['RB'] + team_composition['WR'] + team_composition['TE']
    if turns:
        # Team 0 is the greedy team; always gets to pick first and has perfect knowledge
        for _ in range(rounds):
            for team in range(teams):
                # Find next best player
                no_pick = True
                pointer = 0
                while no_pick:
                    next_pick = par_data.iloc[pointer]
                    if counters[team][next_pick['position']] < team_composition[next_pick['position']]:
                        no_pick = False
                        counters[team][next_pick['position']] += 1
                        rosters[team].append(next_pick['player_id'])
                        print(f"Team {team} picks {next_pick['player_name']}")
                        par_data = par_data.drop(index=pointer)
                        par_data = par_data.reset_index(drop=True)
                    else:
                        pointer += 1
    else:
        # Team 0 is the maximal team; has the best possible team composition for the year
        for team in range(teams):
            for _ in range(rounds):
                # Find next best player
                no_pick = True
                pointer = 0
                while no_pick:
                    next_pick = par_data.iloc[pointer]
                    if counters[team][next_pick['position']] < team_composition[next_pick['position']]:
                        no_pick = False
                        counters[team][next_pick['position']] += 1
                        rosters[team].append(next_pick['player_id'])
                        print(f"Team {team} picks {next_pick['player_name']}")
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
    return teams.sort_values(by='week').reset_index(drop=True)

def find_winner(teams):
        return teams.groupby('week').apply(lambda x: x.idxmax(axis=1)).rename('winner').reset_index(drop=True)

def graph_season(teams):
    fig = px.line(teams,x='week', y=teams.columns[1:], title='Fantasy Points per Week')
    fig.write_image('figures/per_week.png')

def find_non_maximal_team(maximal, par_data, weekly, season=2024):
    BENCHMARK = 5
    MULT = 2
    par_data = par_data[par_data['season'] == season].reset_index(drop=True)
    # Remove the players on the maximal team
    par_data = par_data[~par_data['player_id'].isin(maximal[0])].reset_index(drop=True)
    # Separate out the positions
    qb_data = par_data[par_data['position'] == 'QB'].nlargest(team_composition['QB']*MULT, 'par')
    rb_data = par_data[par_data['position'] == 'RB'].nlargest(team_composition['RB']*MULT, 'par')
    wr_data = par_data[par_data['position'] == 'WR'].nlargest(team_composition['WR']*MULT, 'par')
    te_data = par_data[par_data['position'] == 'TE'].nlargest(team_composition['TE']*MULT, 'par')
    # Generate all combinations at each position
    qb_combinations = [c for c in itertools.combinations(qb_data['player_id'], team_composition['QB'])]
    rb_combinations = [c for c in itertools.combinations(rb_data['player_id'], team_composition['RB'])]
    wr_combinations = [c for c in itertools.combinations(wr_data['player_id'], team_composition['WR'])]
    te_combinations = [c for c in itertools.combinations(te_data['player_id'], team_composition['TE'])]
    # Form all possible teams
    all_teams = itertools.product(qb_combinations, rb_combinations, wr_combinations, te_combinations)
    # Sim season and find winners for each team
    for team in all_teams:
        team = list(team)
        team = [item for sublist in team for item in sublist]
        competing_teams = [maximal[0],list(team)]
        outcomes = sim_season(competing_teams, weekly, season)
        winners = find_winner(outcomes)
        # Check if the non-maximal team wins at least BENCHMARK weeks
        wins = winners.value_counts().get(1, 0)
        if wins > BENCHMARK:
            print(wins)
            print(par_data[par_data['player_id'].isin(list(team))]['player_name'].tolist())
    return None

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
    SZN = 2024
    maximal = sim_draft(1, par_results, season=SZN, turns=True)
    find_non_maximal_team(maximal, par_results, weekly, season=SZN)

if __name__ == "__main__":
    main() 