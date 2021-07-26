name = 'nfl_data_py'

import pandas
import numpy
import datetime


def import_pbp_data(years, columns=None):

    if columns is None:
        columns = []
    plays = pandas.DataFrame()

    url1 = r'https://github.com/nflverse/nflfastR-data/raw/master/data/play_by_play_'
    url2 = r'.parquet'

    for year in years:
        if len(columns) != 0:
            data = pandas.read_parquet(url1 + str(year) + url2, columns=columns, engine='fastparquet')
        else:
            data = pandas.read_parquet(url1 + str(year) + url2, engine='fastparquet')
        raw = pandas.DataFrame(data)
        raw['season'] = year
        if len(plays) == 0:
            plays = raw
        else:
            plays = plays.append(raw)
        print(str(year) + ' done.')

    return plays


def import_weekly_data(years, columns=None):

    if columns is None:
        columns = []
    data = pandas.read_parquet(r'https://github.com/nflverse/nflfastR-data/raw/master/data/player_stats.parquet', engine='fastparquet')
    data = data[data['season'].isin(years)]

    if len(columns) > 0:

        data = data[columns]

    return data


def import_seasonal_data(years):

    data = pandas.read_parquet(r'https://github.com/nflverse/nflfastR-data/raw/master/data/player_stats.parquet', engine='fastparquet')

    pgstats = data[['recent_team', 'season', 'week', 'attempts', 'completions', 'passing_yards', 'passing_tds',
                      'passing_air_yards', 'passing_yards_after_catch', 'passing_first_downs',
                      'fantasy_points_ppr']].groupby(
        ['recent_team', 'season', 'week']).sum().reset_index()
    pgstats.columns = ['recent_team', 'season', 'week', 'atts', 'comps', 'p_yds', 'p_tds', 'p_ayds', 'p_yac', 'p_fds',
                       'ppr_pts']
    all_stats = data[
        ['player_id', 'player_name', 'recent_team', 'season', 'week', 'carries', 'rushing_yards', 'rushing_tds',
         'rushing_first_downs', 'rushing_2pt_conversions', 'receptions', 'targets', 'receiving_yards', 'receiving_tds',
         'receiving_air_yards', 'receiving_yards_after_catch', 'receiving_first_downs', 'receiving_epa',
         'fantasy_points_ppr']].merge(pgstats, how='left', on=['recent_team', 'season', 'week']).fillna(0)
    season_stats = all_stats.drop(['recent_team', 'week'], axis=1).groupby(
        ['player_id', 'player_name', 'season']).sum().reset_index()

    season_stats['tgt_sh'] = season_stats['targets'] / season_stats['atts']
    season_stats['ay_sh'] = season_stats['receiving_air_yards'] / season_stats['p_ayds']
    season_stats['yac_sh'] = season_stats['receiving_yards_after_catch'] / season_stats['p_yac']
    season_stats['wopr'] = season_stats['tgt_sh'] * 1.5 + season_stats['ay_sh'] * 0.8
    season_stats['ry_sh'] = season_stats['receiving_yards'] / season_stats['p_yds']
    season_stats['rtd_sh'] = season_stats['receiving_tds'] / season_stats['p_tds']
    season_stats['rfd_sh'] = season_stats['receiving_first_downs'] / season_stats['p_fds']
    season_stats['rtdfd_sh'] = (season_stats['receiving_tds'] + season_stats['receiving_first_downs']) / (
                season_stats['p_tds'] + season_stats['p_fds'])
    season_stats['dom'] = (season_stats['ry_sh'] + season_stats['rtd_sh']) / 2
    season_stats['w8dom'] = season_stats['ry_sh'] * 0.8 + season_stats['rtd_sh'] * 0.2
    season_stats['yptmpa'] = season_stats['receiving_yards'] / season_stats['atts']
    season_stats['ppr_sh'] = season_stats['fantasy_points_ppr'] / season_stats['ppr_pts']

    data = data[(data['season'].isin(years)) & (data['season_type'] == 'REG')].drop(['recent_team', 'week'], axis=1)
    szn = data.groupby(['player_id', 'player_name', 'season', 'season_type']).sum().reset_index().merge(
        data[['player_id', 'season', 'season_type']].groupby(['player_id', 'season']).count().reset_index().rename(
            columns={'season_type': 'games'}), how='left', on=['player_id', 'season'])

    szn = szn.merge(season_stats[['player_id', 'season', 'tgt_sh', 'ay_sh', 'yac_sh', 'wopr', 'ry_sh', 'rtd_sh',
                                  'rfd_sh', 'rtdfd_sh', 'dom', 'w8dom', 'yptmpa', 'ppr_sh']], how='left',
                    on=['player_id', 'season'])

    return szn


def see_pbp_cols():

    data = pandas.read_parquet(r'https://github.com/nflverse/nflfastR-data/raw/master/data/play_by_play_2020.parquet', engine='fastparquet')
    cols = data.columns

    return cols


def see_weekly_cols():

    data = pandas.read_parquet(r'https://github.com/nflverse/nflfastR-data/raw/master/data/player_stats.parquet', engine='fastparquet')
    cols = data.columns

    return cols


def import_rosters(years, columns=None):

    if columns is None:
        columns = []
    rosters = []

    for y in years:
        temp = pandas.read_csv(r'https://github.com/mrcaseb/nflfastR-roster/blob/master/data/seasons/roster_' + str(y)
                               + '.csv?raw=True', low_memory=False)

        if len(columns) > 0:

            temp = temp[columns]

        rosters.append(temp)

    rosters = pandas.DataFrame(pandas.concat(rosters)).rename(
        columns={'full_name': 'player_name', 'gsis_id': 'player_id'})
    rosters.drop_duplicates(subset=['season', 'player_name', 'position', 'player_id'], keep='first', inplace=True)

    def calc_age(x):
        ca = pandas.to_datetime(x[0])
        bd = pandas.to_datetime(x[1])
        return ca.year - bd.year + numpy.where(ca.month > bd.month, 0, -1)

    rosters['current_age'] = rosters['season'].apply(lambda x: datetime.datetime(int(x), 9, 1))
    rosters['age'] = rosters[['current_age', 'birth_date']].apply(calc_age, axis=1)
    rosters.drop(['current_age'], axis=1, inplace=True)
    rosters.dropna(subset=['player_id'], inplace=True)

    return rosters


def import_team_desc():
    
    df = pandas.read_csv(r'https://github.com/nflverse/nflfastR-data/raw/master/teams_colors_logos.csv')
    
    return df


def clean_nfl_data(df):

    name_repl = {
        'Gary Jennings Jr': 'Gary Jennings',
        'DJ Chark': 'D.J. Chark',
        'Cedrick Wilson Jr.': 'Cedrick Wilson',
        'Deangelo Yancey': 'DeAngelo Yancey',
        'Ardarius Stewart': 'ArDarius Stewart',
        'Calvin Johnson  HOF': 'Calvin Johnson',
        'Mike Sims-Walker': 'Mike Walker',
        'Kenneth Moore': 'Kenny Moore',
        'Devante Parker': 'DeVante Parker',
        'Brandon Lafell': 'Brandon LaFell',
        'Desean Jackson': 'DeSean Jackson',
        'Deandre Hopkins': 'DeAndre Hopkins',
        'Deandre Smelter': 'DeAndre Smelter',
        'William Fuller': 'Will Fuller',
        'Lavon Brazill': 'LaVon Brazill',
        'Devier Posey': 'DeVier Posey',
        'Demarco Sampson': 'DeMarco Sampson',
        'Deandrew Rubin': 'DeAndrew Rubin',
        'Latarence Dunbar': 'LaTarence Dunbar',
        'Jajuan Dawson': 'JaJuan Dawson',
        "Andre' Davis": 'Andre Davis',
        'Johnathan Holland': 'Jonathan Holland',
        'Johnnie Lee Higgins Jr.': 'Johnnie Lee Higgins',
        'Marquis Walker': 'Marquise Walker',
        'William Franklin': 'Will Franklin',
        'Ted Ginn Jr.': 'Ted Ginn',
        'Jonathan Baldwin': 'Jon Baldwin',
        'T.J. Graham': 'Trevor Graham',
        'Odell Beckham Jr.': 'Odell Beckham',
        'Michael Pittman Jr.': 'Michael Pittman',
        'DK Metcalf': 'D.K. Metcalf',
        'JJ Arcega-Whiteside': 'J.J. Arcega-Whiteside',
        'Lynn Bowden Jr.': 'Lynn Bowden',
        'Laviska Shenault Jr.': 'Laviska Shenault',
        'Henry Ruggs III': 'Henry Ruggs',
        'KJ Hamler': 'K.J. Hamler',
        'KJ Osborn': 'K.J. Osborn',
        'Devonta Smith': 'DeVonta Smith',
        'Terrace Marshall Jr.': 'Terrace Marshall',
        "Ja'Marr Chase": 'JaMarr Chase'
    }

    col_tm_repl = {
        'Ole Miss': 'Mississippi',
        'Texas Christian': 'TCU',
        'Central Florida': 'UCF',
        'Bowling Green State': 'Bowling Green',
        'West. Michigan': 'Western Michigan',
        'Pitt': 'Pittsburgh',
        'Brigham Young': 'BYU',
        'Texas-El Paso': 'UTEP',
        'East. Michigan': 'Eastern Michigan',
        'Middle Tenn. State': 'Middle Tennessee State',
        'Southern Miss': 'Southern Mississippi',
        'Louisiana State': 'LSU'
    }

    pro_tm_repl = {
        'GNB': 'GB',
        'KAN': 'KC',
        'LA': 'LAR',
        'LVR': 'LV',
        'NWE': 'NE',
        'NOR': 'NO',
        'SDG': 'SD',
        'SFO': 'SF',
        'TAM': 'TB'
    }

    if 'name' in df.columns:
        df.replace({'name': name_repl}, inplace=True)

    if 'col_team' in df.columns:
        df.replace({'col_team': col_tm_repl}, inplace=True)

        if 'name' in df.columns:
            for z in player_col_tm_repl:
                df[df['name'] == z[0]] = df[df['name'] == z[0]].replace({z[1]: z[2]})

    return df
