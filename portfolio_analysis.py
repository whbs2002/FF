import pandas as pd
from assumptions import last_pos
def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    
    return identity, weekly, yearly, overall

# find stats for replacement player
def replacement_stats(data):
    replacement = {}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        last_player = int(last_pos(pos))
        position_data = data[data['position'] == pos].sort_values(by='ppg', ascending=False)
        replacement[pos] = position_data.iloc[last_player-1].loc['ppg']
    return replacement

# calculate points above replacement for each player
def par(data, replacement):   
    return 0


def main():
    identity, weekly, yearly, overall = load_data()
    
    # Calculate replacement stats
    replacement = replacement_stats()
    
    # Calculate points above replacement
    par_results = par(overall, replacement)
    
    # Print results
    print(par_results)

if __name__ == "__main__":
    main() 