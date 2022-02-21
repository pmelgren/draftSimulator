import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
import pandas as pd
import random


#######################
# Helper functions
#######################

# # convert a dataframe into a dict where each item is another dict corresponding
# # to a row of the html table
def make_table(df):

    # table header
    rows = [html.Tr([html.Th(col) for col in list(df.columns)])]
    
    # loop through each unique filename and create a list of the Html objects to make that row
    for r in range(len(df.index)):
        row = [html.Th(df.iloc[r,c]) for c in range(len(df.columns))]
        rows.append(html.Tr(row))
    return rows

def get_auto_picks(start_pick,end_pick,pl,n_teams,roster):
    
    randweights = [0]*25+[1]*9+[2]*5+[3]*3+[4]*2+[5]*2+[6]+[7]+[8]+[9]

    for pick_number in range(start_pick,end_pick):
    
        # determine team needs
        team = (teamnames[:n_teams+1]+teamnames[n_teams:0:-1])[pick_number % (2*n_teams)]
        pln = remove_unneeded_players(pl, roster, team)
        
        # use randomness to determine which player will be selected
        pick_no = randweights[random.randrange(0,49)] 
        pick_idx = pln.sort_values('Rank',ascending=True).index[pick_no] 
        pos= pl.loc[pick_idx,'Position(s)']
        
        # update players table
        pl.loc[pick_idx,'Available'] = False
        pl.loc[pick_idx,'Rd'] = (pick_number-1) // n_teams + 1
        pl.loc[pick_idx,'Pick'] = (pick_number-1) % n_teams + 1
        pl.loc[pick_idx,'Slot'] = determine_slot(pos,roster,pl.loc[pl.Team == team])
        pl.loc[pick_idx,'Team'] = team

    return pl    

def determine_slot(pos, ros, teampl):
    m = ros.merge(teampl,on='Slot',how='left')
    
    # add alternative positions
    altpos = (['MI'] if '2B' in pos or 'SS' in pos else []) + (
                ['CI'] if '1B' in pos or '3B' in pos else []) + ['UT','BE']
    for p in pos.split(', ') + altpos:
        for a in m.loc[m.Player.isna()].sort_values('Num')['Slot']:
            if p in a:
                return a
    else:
        return '-'
    
def remove_unneeded_players(pl,roster,team):
    
    # Remove the players from pl that team doesn't need based on roster
    teampl = pl.loc[pl.Team == team]
    teamros = roster.merge(teampl,on = 'Slot',how='left')
    needs = list(teamros.loc[teamros.Player.isna(),'Slot'].str.replace('\d+$','',regex=True))
    
    # handle MI and CI
    if 'MI' in needs:
        needs = needs + ['SS','2B']
    if 'CI' in needs:
        needs = needs + ['1B','3B']
    
    # filter players that don't match roster needs
    if ('BE' not in needs) and  ('UT' not in needs):
        return pl.loc[pl['Position(s)'].str.match('|'.join(needs)) & pl['Available']]
    else:
        return pl.loc[pl['Available']]


#######################
# Initial Data Prep
#######################

players = pd.read_csv('players.csv')
players['Team'], players['Slot'], players['Rd'], players['Pick'] = (pd.NA, pd.NA, pd.NA, pd.NA)

teamnames = 'AABCDEFGHIJKLMNOPQRSTUVWXYZ'

#######################
# Dash app layout
#######################
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# header for the app
header = [dbc.Row(html.H1('Draft Simulator')),
          dbc.Row(html.Div(' ',style = {'height': "35px"}))
]

startsection = [
    dbc.Row([
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-p-dropdown',options=list(range(5,16)),value=9), 
                html.Div(children='# of Pitchers')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-of-dropdown',options=list(range(3,8)),value=3), 
                html.Div(children='# of Outfielders')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-c-dropdown',options=list(range(1,4)),value=1), 
                html.Div(children='# of Catchers')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-ci-dropdown',options=list(range(0,6)),value=1), 
                html.Div(children='# of Corner IF')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-mi-dropdown',options=list(range(0,6)),value=1), 
                html.Div(children='# of Middle IF')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-ut-dropdown',options=list(range(0,21)),value=2), 
                html.Div(children='# of Utility Players')  
            ],style = {'width':'90%'}), md=1),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-be-dropdown',options=list(range(0,21)),value=2), 
                html.Div(children='# of Bench Players')  
            ],style = {'width':'15%'}), md=6)
    ],id = 'start-row-1'),
    dbc.Row(html.Div(' ',style = {'height': "25px"})),
    dbc.Row([
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-teams-dropdown',options=list(range(2,25)),value=10), 
                html.Div(children='Select number of teams')  
            ],style = {'width':'75%'}), md=2),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='position-dropdown'), 
                html.Div(children='Select your draft position')
            ],style = {'width':'75%'}), md=2),
        dbc.Col(html.Button('Begin!',id='begin-button',style={'width': '25%'}),md=8)   
    ],id = 'start-row-2')
]


# put the table of the sorted data in the left half of the screen
draftpanel = [
    html.Div([
        html.Div([
            html.H3('Select Player'),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(options = players.Rank.astype(str)+'. '+players.Name+' ('+players['Position(s)']+')'
                             ,id = 'pick-dropdown'),
                    html.Button('Draft Player', id='draft-button', n_clicks=0)],md=5),
                dbc.Col([
                    html.Table(make_table(pd.DataFrame({})),id='bat-proj-table',className='table'),
                    html.Table(make_table(pd.DataFrame({})),id='pit-proj-table',className='table')],md=7)
            ]),
            html.Div(' ',style={'height':'20px'})
        ],id = 'draft-div'),
        html.H3('Team Roster'),
        dcc.Dropdown(id='team-roster-dropdown',options=['My-Team'], value = 'My-Team'), 
        html.Table(make_table(pd.DataFrame({})),id='roster-table',className='table')
    ],id='draft-panel',style={"width": "90%"})
]

pickspanel = [
    html.Div([
        html.H3('Last Picks'),
        html.Table(make_table(pd.DataFrame({})),id='last-picks-table',className='table'),
        html.Div(players.to_json(),id='players',style={'display': 'none'}),
        html.Div(0,id='n-teams',style={'display': 'none'}),
        html.Div(0,id='position',style={'display': 'none'}),
        html.Div(0,id='pick-number',style={'display': 'none'}),
        html.Div(0,id='roster',style={'display': 'none'})
    ],style = {"width": "90%"})
]

projpanel = [
        html.Div([
            html.H3('Projected Standings'),
            dcc.RadioItems(['Stats','Ranks'],'Stats',id='proj-type-radioitems',style = {'width':'200%'}),
            html.Table(make_table(pd.DataFrame({})),id='proj-standings-table',className='table')
        ])
]

# lay out the app based on the above panel definitions
app.layout = dbc.Container([
        html.Div(header),
        html.Div(startsection,id ='start-section'),
        html.Div(dbc.Row([dbc.Col(draftpanel, md=5),
                 dbc.Col(projpanel, md=5),
                 dbc.Col(pickspanel, md=2)])
                ,id = 'main-section',style = {'display':'none'})
],fluid=True)


# #######################
# # Reactive callbacks
# #######################
@app.callback(
    Output('roster','children'),
    [Input('n-of-dropdown','value'),
     Input('n-p-dropdown','value'),
     Input('n-c-dropdown','value'),
     Input('n-mi-dropdown','value'),     
     Input('n-ci-dropdown','value'),
     Input('n-ut-dropdown','value'),
     Input('n-be-dropdown','value'),
     Input('begin-button','n_clicks')]
)
def update_roster(n_of,n_p,n_c,n_mi,n_ci,n_ut,n_be,n_clicks):
    slots = (['C'+str(i+1) for i in range(n_c)] +
             ['1B','2B','3B','SS'] + 
             ['OF'+str(i+1) for i in range(n_of)] + 
             ['MI'+str(i+1) for i in range(n_mi)] + 
             ['CI'+str(i+1) for i in range(n_ci)] + 
             ['P'+str(i+1) for i in range(n_p)] + 
             ['UT'+str(i+1) for i in range(n_ut)] + 
             ['BE'+str(i+1) for i in range(n_be)])
    
    roster = pd.DataFrame({'Slot': slots,'Num': list(range(len(slots)))})
    return roster.to_json()

@app.callback(
    Output('position-dropdown', 'options'),
    [Input('n-teams-dropdown', 'value')]
)
def update_position_dropdown(num_teams):
    return list(range(1,num_teams+1))

@app.callback(
    [Output('pick-dropdown','options')],
    [Input('players','children'),
     Input('roster','children')]
)
def update_pick_options(players_json,roster_json):
    pl = pd.read_json(players_json)
    roster = pd.read_json(roster_json)
    pln = remove_unneeded_players(pl, roster, 'My-Team')
    return [list(pln.Rank.astype(str)+'. '+pln.Player+' ('+pln['Position(s)']+')')]

@app.callback(
    Output('last-picks-table', 'children'),
    [Input('players','children')],
    [State('n-teams','children')]
)
def update_last_picks_table(players_json,n_teams):
    pl = pd.read_json(players_json)
    last_picks = pl.loc[~pl.Team.isna()]
    last_picks['Pick'] = (last_picks['Rd']-1)*n_teams + last_picks['Pick']
    last_picks.loc[last_picks.Team == 'My-Team','Team'] = 'Me'
    
    return make_table(last_picks.sort_values('Pick',ascending = False)
                      [['Pick','Team','Player']].iloc[0:3*n_teams])
    
@app.callback(
    Output('roster-table', 'children'),
    [Input('players','children'),
     Input('team-roster-dropdown','value')],
    [State('roster','children')]
)
def update_roster_table(players_json,teamchoice,roster_json):
    ros = pd.read_json(roster_json)
    pl = pd.read_json(players_json)
    pl['AVG'] = (pl['H']/pl['AB']).round(3)
    pl['ERA'] = (9*pl['ER']/pl['IP']).round(2)
    pl['WHIP'] = ((pl['BB']+pl['H.P'])/pl['IP']).round(2)
    teampl = pl.loc[pl.Team == teamchoice]
    
    retcols = ['Slot','Player','Rd','AB','R','HR','RBI','SB','AVG',
               'IP', 'ERA', 'W', 'SO', 'SV', 'WHIP']
    ret = ros.merge(teampl,on='Slot',how='left').sort_values('Num')
    return make_table(ret[retcols])

@app.callback(
    Output('bat-proj-table', 'children'),
    [Input('pick-dropdown','value')],
    [State('players','children')]
)
def update_bat_proj_table(pick,players_json):
    pl = pd.read_json(players_json)
    pickrank = int(pick.split('.')[0])
    pick_idx = pl.loc[pl.Rank == pickrank].index[0]
    pl['AVG'] = (pl['H']/pl['AB']).round(3)

    if pl.loc[pick_idx,['AB']].count() > 0:
        return make_table(pl.loc[[pick_idx],['AB', 'R', 'HR', 'RBI', 'SB','AVG']])
    else:         
        return make_table(pd.DataFrame({}))
    
@app.callback(
    Output('pit-proj-table', 'children'),
    [Input('pick-dropdown','value')],
    [State('players','children')]
)
def update_pit_proj_table(pick,players_json):
    pl = pd.read_json(players_json)
    pickrank = int(pick.split('.')[0])
    pick_idx = pl.loc[pl.Rank == pickrank].index[0]
    pl['WHIP'] = ((pl['BB']+pl['H.P'])/pl['IP']).round(2)
    pl['ERA'] = (9*pl['ER']/pl['IP']).round(2)

    if pl.loc[pick_idx,['IP']].count() > 0:
        return make_table(pl.loc[[pick_idx],['IP', 'ERA', 'W', 'SO', 'SV', 'WHIP']])
    else:         
        return make_table(pd.DataFrame({}))
    
@app.callback(
    Output('proj-standings-table','children'),
    [Input('players','children'),
     Input('proj-type-radioitems','value')]    
)
def update_proj_standings(players_json,proj_type):
    df = pd.read_json(players_json)
    dfg=df.groupby('Team')[['AB', 'H', 'R', 'HR', 'RBI', 'SB', 'IP', 'ER', 'W',
                            'SO', 'SV', 'H.P','BB']].sum().reset_index().sort_values('Team')
    dfg['AVG'] = (dfg['H']/dfg['AB']).round(3)
    dfg['ERA'] = (9*dfg['ER']/dfg['IP']).round(2)
    dfg['WHIP'] = ((dfg['BB']+dfg['H.P'])/dfg['IP']).round(2)
    
    ranks = {'Team':dfg.Team}
    for m in ['R', 'HR', 'RBI', 'SB','AVG', 'W','SO', 'SV']:
        ranks.update({m: dfg[m].rank(ascending=False)})
    for m in ['ERA','WHIP']:
        ranks.update({m: dfg[m].rank()})
    
    rdf = pd.DataFrame(ranks,index=dfg.index)
    rdf['Score'] = rdf.sum(axis=1)
    
    if proj_type == 'Ranks':
        return make_table(rdf.sort_values('Score'))
    else:
        dfg['Score'] = rdf.Score
        return make_table(dfg[rdf.columns].sort_values('Score'))
    
@app.callback(
    [Output('n-teams','children'),
     Output('position','children'),
     Output('pick-number','children'),
     Output('players','children'),
     Output('begin-button','n_clicks'),
     Output('draft-button','n_clicks'),
     Output('team-roster-dropdown','options'),
     Output('main-section','style'),
     Output('start-section','style')],
    [Input('begin-button', 'n_clicks'),
     Input('n-teams-dropdown','value'),
     Input('position-dropdown','value'),
     Input('draft-button','n_clicks'),
     Input('pick-dropdown','value')],
    [State('n-teams','children'),
     State('position','children'),
     State('pick-number','children'),
     State('team-roster-dropdown','options'),
     State('main-section','style'),
     State('start-section','style'),
     State('players','children'),
     State('roster','children')]
)
def update_data(begin_clicks,n_teams,position,draft_clicks,pick,
                prev_n_teams,prev_position,pick_number,prev_opts,
                prev_style1,prev_style2,players_json,roster_json):
    if begin_clicks is not None:
    
        # prepare data frames
        pl = pd.read_json(players_json)
        ros = pd.read_json(roster_json)
    
        # initial autopicks    
        pl = get_auto_picks(1, position, pl, n_teams, ros)   
        
        # list of team names
        opts = ['My-Team'] + [teamnames[i] for i in range(1,n_teams+1) if i != position]
        return (n_teams, position, position, pl.to_json(),
                None, None, opts, {'display':'block'}, {'display':'none'})

    elif draft_clicks is not None:
        
        pl = pd.read_json(players_json)
        pickrank = int(pick.split('.')[0])
        pick_idx = pl.loc[pl.Rank == pickrank].index[0]
        pos = pl.loc[pick_idx,'Position(s)']
        
        ros = pd.read_json(roster_json)
        
        pl.loc[pick_idx,'Available'] = False
        pl.loc[pick_idx,'Rd'] = (pick_number-1) // n_teams + 1
        pl.loc[pick_idx,'Pick'] = (pick_number-1) % n_teams + 1
        pl.loc[pick_idx,'Slot'] = determine_slot(pos,ros,pl.loc[pl.Team == 'My-Team'])
        pl.loc[pick_idx,'Team'] = 'My-Team'

        # auto draft to next human pick or end of draft
        human_picks = [position%(2*n_teams), (2*n_teams+1-position)%(2*n_teams)] 
        end_pick = pick_number+1
        while (end_pick % (n_teams*2) not in human_picks) & (end_pick <= len(ros.Num)*n_teams): 
            end_pick += 1
        
        pl = get_auto_picks(pick_number+1,end_pick,pl,n_teams,ros)
        
        return (n_teams, position, end_pick, pl.to_json(), 
                None, None, prev_opts, prev_style1, prev_style2)
    else:
        return (prev_n_teams, prev_position, pick_number, players_json, 
                None, None, prev_opts, prev_style1, prev_style2)
    
@app.callback(
    Output('draft-div','style'),
    [Input('pick-number','children')],
    [State('n-teams','children'),
     State('roster','children'),
     State('draft-div','style')]
)
def end_draft(pick_num,n_teams,roster_json,prev_style):
    ros = pd.read_json(roster_json)
    if pick_num > n_teams*len(ros.index):
        return {'display':'none'}
    else:
        return prev_style

# necessary code at the bottom of all Dash apps to run the app
if __name__ == "__main__":
    app.run_server(port = 8080)