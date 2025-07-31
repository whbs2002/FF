import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import plotly.figure_factory as ff
import numpy as np
import nfl_data_py as nfl
import statsmodels.api as sm
from formulaic import model_matrix

def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    schedules = nfl.import_schedules(range(1999,2025))

    return identity, weekly, yearly, overall,schedules

def calculate_days(schedules):
    schedules = schedules[schedules['game_type']=='REG']
    schedules = schedules[['season','week','gameday','away_team','home_team','away_score','home_score']]
    # switch to just team and score
    away = schedules[['gameday', 'season', 'week', 'away_team', 'away_score']].rename(
        columns={'away_team': 'team', 'away_score': 'score'}
    )
    home = schedules[['gameday', 'season', 'week', 'home_team', 'home_score']].rename(
        columns={'home_team': 'team', 'home_score': 'score'}
    )
    team_scores = pd.concat([away, home], ignore_index=True)
    team_scores['gameday'] = pd.to_datetime(team_scores['gameday'])
    team_scores = team_scores.sort_values(by=['team','gameday']).reset_index(drop=True)
    team_scores['days'] = team_scores.groupby('team')['gameday'].diff().dt.days
    team_scores = team_scores.dropna(subset=['days']).reset_index(drop=True)
    team_scores.fillna(0,inplace=True)
    team_scores = team_scores[team_scores['days']<25].reset_index(drop=True)
    return team_scores

#
def team_performance(schedules):
    team_scores = calculate_days(schedules)
    model_1 = sm.OLS(team_scores['score'],sm.add_constant(team_scores['days']))
    res = model_1.fit()
    print(res.summary())

    # demean the data
    team_scores['score_demeaned'] = team_scores['score']- team_scores.groupby(['team','season'])['score'].transform('mean')
    model_2 = sm.OLS(team_scores['score_demeaned'],sm.add_constant(team_scores['days']))
    res_2 = model_2.fit()
    print(res_2.summary())
    team_scores['days_sq'] = team_scores['days'] ** 2
    model_3 = sm.OLS(team_scores['score_demeaned'],sm.add_constant(team_scores[['days', 'days_sq']]))
    res_3 = model_3.fit()
    print(res_3.summary()) 
    fig = px.scatter(team_scores,x='days',y='score_demeaned',color='team')
    fig.write_html('figures/team_scores.html')
    return 0

def player_performance(schedules, weekly,identity):
    team_scores = calculate_days(schedules)
    weekly.rename(columns={'recent_team':'team'}, inplace=True)
    weekly = weekly.merge(team_scores, on=['season','week','team'], how='left')
    weekly = weekly.dropna(subset=['days']).reset_index(drop=True)
    weekly = weekly.merge(identity,on='player_id',how='left')
    weekly = weekly[['player_id','days','fantasy_points_ppr','position','season','week']]
    weekly = weekly[weekly['position'].isin(['QB', 'RB', 'WR', 'TE'])].reset_index(drop=True)
    weekly['points_demeaned'] = weekly['fantasy_points_ppr'] - weekly.groupby(['player_id','season'])['fantasy_points_ppr'].transform('mean')
    #All players
    y,X = model_matrix('points_demeaned ~ days + position',weekly)
    model = sm.OLS(y,X)
    res = model.fit()
    print(res.summary())
    # Just regular players (>1 ppg)
    regular_players = weekly.groupby(['player_id','season'])['fantasy_points_ppr'].mean().reset_index()
    regular_players = regular_players[regular_players['fantasy_points_ppr'] > 1]
    regular = weekly[weekly['player_id'].isin(regular_players['player_id'])].reset_index(drop=True)
    y,X = model_matrix('points_demeaned ~ days + position',regular)
    model = sm.OLS(y,X)
    res = model.fit()
    print(res.summary())

    # Just good players (> 6 ppg)
    good_players = weekly.groupby(['player_id','season'])['fantasy_points_ppr'].mean().reset_index()
    good_players = good_players[good_players['fantasy_points_ppr'] > 10]
    good = weekly[weekly['player_id'].isin(good_players['player_id'])].reset_index(drop=True)
    y,X = model_matrix('points_demeaned ~ days + position',good)
    model = sm.OLS(y,X)
    res = model.fit()
    print(res.summary())
    fig = px.scatter(weekly[weekly['position']=='QB'],x='days',y='points_demeaned')
    fig.write_html('figures/player_scores.html')
    fig = px.scatter(regular[regular['position']=='QB'],x='days',y='points_demeaned')
    fig.write_html('figures/reg_player_scores.html')
    fig = px.scatter(good[good['position']=='QB'],x='days',y='points_demeaned')
    fig.write_html('figures/good_player_scores.html')
    return 0




def main():
    identity, weekly, yearly, overall,schedules = load_data()
    # 
    team_performance(schedules)
    player_performance(schedules, weekly,identity)
    overall = overall.merge(identity, on='player_id', how='left')



if __name__ == "__main__":
    main() 