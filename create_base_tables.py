import nfl_data_py as nfl
import pandas as pd

raw = nfl.import_weekly_data(
    years = [x for x in range(1999,2025)],
    columns = ['player_id', 'player_name', 'position',
       'position_group', 'recent_team', 'season', 'week',
       'season_type', 'opponent_team',
       'passing_yards', 'passing_tds', 'interceptions',
       'sack_fumbles', 'sack_fumbles_lost',
       'passing_2pt_conversions', 'rushing_yards',
       'rushing_tds', 'rushing_fumbles', 'rushing_fumbles_lost',
       'rushing_2pt_conversions',
       'receptions', 'receiving_yards', 'receiving_tds',
       'receiving_fumbles', 'receiving_fumbles_lost',
       'receiving_2pt_conversions', 'special_teams_tds', 'fantasy_points', 'fantasy_points_ppr']
)

# First drop irrelevant rows
# Remove all playoff data
raw = raw[raw['season_type'] == 'REG']
# Remove defensive players and offensive linemen
raw = raw[raw['position'].isin(['RB', 'QB', 'WR', 'TE', 'FB', 'K', 'HB'])]

# Create table for player identity
identity = raw[['player_id','player_name','position']].drop_duplicates().dropna(subset=['player_id','position']).reset_index(drop=True)
identity[identity['position'] == 'FB'] = 'RB'
identity[identity['position'] == 'HB'] = 'RB'

# Create table for weekly stats
weekly = raw[['player_id', 'recent_team', 'season', 'week', 'opponent_team',
       'passing_yards', 'passing_tds', 'interceptions', 'sack_fumbles_lost',
       'passing_2pt_conversions', 'rushing_yards', 'rushing_tds', 'rushing_fumbles_lost',
       'rushing_2pt_conversions', 'receptions', 'receiving_yards', 'receiving_tds', 'receiving_fumbles_lost',
       'receiving_2pt_conversions', 'fantasy_points_ppr']]

weekly['fumbles'] = weekly['sack_fumbles_lost'] + weekly['rushing_fumbles_lost'] + weekly['receiving_fumbles_lost']
weekly = weekly.drop(columns=['sack_fumbles_lost', 'rushing_fumbles_lost','receiving_fumbles_lost'])
weekly['2pt'] = weekly['passing_2pt_conversions'] + weekly['rushing_2pt_conversions'] + weekly['receiving_2pt_conversions']
weekly = weekly.drop(columns=['passing_2pt_conversions', 'rushing_2pt_conversions', 'receiving_2pt_conversions'])

# Create table for yearly stats
yearly = weekly.drop(columns=['opponent_team'])
yearly = yearly.groupby(['player_id','season']).agg({
    'recent_team':'first',
    'week':'count',
    'passing_yards':'sum',
    'passing_tds':'sum',
    'interceptions':'sum',
    'rushing_yards':'sum',
    'rushing_tds':'sum',
    'receptions':'sum',
    'receiving_yards':'sum',
    'receiving_tds':'sum',
    'fantasy_points_ppr':'sum',
    'fumbles':'sum',
    '2pt':'sum'
}).reset_index()

# Captures weeks per season
season = yearly.groupby('season').agg({
    'week':'max'
})

# add total weeks to yearly stats
yearly = yearly.join(season, on='season', rsuffix='_total')

# Find standard deviation of fantasy points per player per season
small_table = weekly[['player_id','season','fantasy_points_ppr']]
small_table= small_table.groupby(['player_id','season']).agg(std_dev=pd.NamedAgg(column="fantasy_points_ppr", aggfunc="std")).reset_index()
yearly = yearly.join(small_table.set_index(['player_id','season']), on=['player_id','season'])

# Create overall stats table with only the most important data
overall = yearly[['player_id','season','week_total','fantasy_points_ppr','std_dev']]
overall['ppg'] = overall['fantasy_points_ppr'] / overall['week_total']
overall = overall.drop(columns=['fantasy_points_ppr','week_total'])
# fill missing standard deviations with -1 (right now no filling is done)
# overall = overall.fillna({'std_dev': -1})
# Save the tables to CSV files
identity.to_csv('data/player_identity.csv', index=False)
weekly.to_csv('data/weekly_stats.csv', index=False)
yearly.to_csv('data/yearly_stats.csv', index=False)
overall.to_csv('data/overall_stats.csv', index=False)