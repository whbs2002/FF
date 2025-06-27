import nfl_data_py as nfl

print(nfl.see_weekly_cols())

test = nfl.import_weekly_data(
    years=[2023],
    columns=['player_name','position','week','passing_yards','rushing_yards'])

print(test.head(10))