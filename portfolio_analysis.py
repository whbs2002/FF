import pandas as pd
from assumptions import last_pos
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

if __name__ == "__main__":
    main() 