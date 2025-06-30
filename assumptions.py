team_composition = {
    'QB': 1,
    'RB': 2,
    'WR': 2,
    'TE': 1,
    'FLEX': 1,
    'SFLEX': 0,
    'K': 1,
    'DST' : 1
}
TEAMS = 8
# Last reasonable player to be rostered for each position
# Divide by 2 to get last reasonable player starting
def last_pos(pos,teams=TEAMS):
    last_player = -0.5
    if pos == 'RB' or pos == 'WR' or pos == 'TE':
        last_player = team_composition[pos]*teams + team_composition['FLEX']*teams*0.5 + team_composition['SFLEX']*teams*0.2
    if pos == 'QB':
        last_player = team_composition[pos]*teams + team_composition['SFLEX']*teams
    if pos == 'K':
        last_player = team_composition[pos]*teams
    # Account for bench spots
    last_player = last_player*2
    return last_player
