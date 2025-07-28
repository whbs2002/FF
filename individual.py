import pandas as pd
from assumptions import last_pos, TEAMS, team_composition
import plotly.express as px
import plotly.figure_factory as ff
import numpy as np

def load_data():
    # Load the data from CSV files
    identity = pd.read_csv('data/player_identity.csv')
    weekly = pd.read_csv('data/weekly_stats.csv')
    yearly = pd.read_csv('data/yearly_stats.csv')
    overall = pd.read_csv('data/overall_stats.csv')
    
    return identity, weekly, yearly, overall

def scenario_one():
    return 0

def scenario_two():
    return 0

def scenario_three():
    return 0

# Compare always starting the least variable player to trying to guess the best
def scenario_four():
    N = 1000000
    v = 1.25
    lbda = 0.4
    rng = np.random.default_rng()
    A = rng.normal(0,1,(N,2))
    B = np.concatenate((rng.normal(0,1,(N,1)), rng.normal(0,v,(N,1))), axis=1)
    C = rng.normal(0,v,(N,2))
    # determines how many times the correct player is predicted. Correct = 0 (no change), incorrect = 1 (change)
    correct = (rng.random(N)>lbda).astype(int)
    # Records the predictions 
    better_A = (A[:,0] < A[:,1]).astype(int)
    better_A = (better_A + correct)%2
    better_B = (B[:,0] < B[:,1]).astype(int)
    better_B = (better_B + correct)%2
    better_C = (C[:,0] < C[:,1]).astype(int)
    better_C = (better_C + correct)%2
    choice_A = A[np.arange(0,N,1),better_A]
    choice_B = B[np.arange(0,N,1),better_B]
    choice_C = C[np.arange(0,N,1),better_C]
    outcome_A = np.sum(choice_A)
    outcome_B = np.sum(choice_B)
    outcome_C = np.sum(choice_C)
    print(outcome_A)
    print(outcome_B)
    print(outcome_C)
    return 0

def main():
    identity, weekly, yearly, overall = load_data()
    overall = overall.merge(identity, on='player_id', how='left')



if __name__ == "__main__":
    scenario_four() 