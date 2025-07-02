# Interesting but not very useful information
import pandas as pd

def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    
    return identity, weekly, yearly, overall

def main():
    identity, weekly, yearly, overall = load_data()
    print(overall.dtypes)
    print(identity.dtypes)
    print(overall.head(10))
    print(identity.head(10))
    #add identity info for display purposes
    overall = overall.merge(identity, on='player_id', how='left')
    overall = overall.sort_values(by=['ppg'],ascending=False)
    overall = overall.reset_index(drop=True)
    print(overall[['player_name','season','ppg','std_dev']].head(10))

    overall = overall.sort_values(by=['std_dev'],ascending=False)
    print(overall[['player_name','season','ppg','std_dev']].head(10))

    overall = overall[overall['ppg'] > 10.0]
    overall.reset_index(drop=True, inplace=True)
    print(overall[['player_name','season','ppg','std_dev']].head(25))



if __name__ == "__main__":
    main()