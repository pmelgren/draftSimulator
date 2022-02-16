import dash
from dash import dcc
import dash_bootstrap_components as dbc
import dash_daq as daq
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

def get_auto_picks(start_pick,end_pick,px,pl,n_teams,roster):
    
    pick_number=start_pick
    for pick_number in range(start_pick,end_pick):
    
        # auto-pick     
        randweights = [0]*25+[1]*9+[2]*5+[3]*3+[4]*2+[5]*2+[6]+[7]+[8]+[9]
        pick_no = randweights[random.randrange(0,49)]
        pick_idx = pl.loc[pl.Available].sort_values('Rank',ascending=True).index[pick_no]
        team = (teamnames[:n_teams+1]+teamnames[n_teams:0:-1])[pick_number % (2*n_teams)]
        pos= pl.loc[pick_idx,'Position(s)']
        
        # add the autopick to the picks data
        px = px.append({'Team':team
                        ,'Position': pos
                        ,'Player':pl.loc[pick_idx,'Player']
                        ,'Round':(pick_number-1) // n_teams + 1
                        ,'Pick':(pick_number-1) % n_teams + 1
                        ,'Slot':determine_slot(pos,roster,px.loc[px.Team == team])}
                      ,ignore_index = True)
        
        pl.loc[pick_idx,'Available'] = False
        pl.loc[pick_idx,'Team'] = team

    return px, pl    

def determine_slot(pos, ros, px):
    m = ros.merge(px,on='Slot',how='left')
    for p in pos.split(', ') +['UT','BE']:
        for a in m.loc[m.Player.isna()].sort_values('Num')['Slot']:
            if p in a:
                return a
    else:
        return '-'


#######################
# Initial Data Prep
#######################

players = pd.read_csv('players.csv')
players['Team'] = pd.NA

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
                dcc.Dropdown(id='n-of-dropdown',options=list(range(3,8)),value=3), 
                html.Div(children='Select number of OF')  
            ],style = {'width':'75%'}), md=2),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-p-dropdown',options=list(range(5,16)),value=9), 
                html.Div(children='Select number of Pitchers')  
            ],style = {'width':'75%'}), md=2),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-ut-dropdown',options=list(range(0,21)),value=2), 
                html.Div(children='Select number of Utility players')  
            ],style = {'width':'75%'}), md=2),
        dbc.Col(
            html.Div([
                dcc.Dropdown(id='n-be-dropdown',options=list(range(0,21)),value=2), 
                html.Div(children='Select number of Bench Players')  
            ],style = {'width':'25%'}), md=6)
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
        html.H3('Select Player'),
        dcc.Dropdown(options = players.Rank.astype(str)+'. '+players.Name+' ('+players['Position(s)']+')'
                     ,id = 'pick-dropdown'),
        html.Button('Draft Player', id='draft-button', n_clicks=0),
        html.Table(make_table(pd.DataFrame({})),id='bat-proj-table',className='table'),
        html.Table(make_table(pd.DataFrame({})),id='pit-proj-table',className='table'),
        html.Div(' ',style={'height':'20px'}),
        html.H3('Team Roster'),
        dcc.Dropdown(id='team-roster-dropdown',options=['My-Team'], value = 'My-Team'), 
        html.Table(make_table(pd.DataFrame({})),id='roster-table',className='table')
    ],id='draft-panel',style={"width": "90"})
]

pickspanel = [
    html.Div([
        html.H3('Last Picks'),
        html.Table(make_table(pd.DataFrame({})),id='last-picks-table',className='table'),
        html.Div(0,id='picks',style={'display': 'none'}),
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
            daq.ToggleSwitch('proj-style-toggle',value=False),
            html.Div('Show Stats',id='proj-toggle-label'),
            html.Table(make_table(pd.DataFrame({})),id='proj-standings-table',className='table')
        ])
]

# lay out the app based on the above panel definitions
app.layout = dbc.Container([
        html.Div(header),
        html.Div(startsection,id ='start-section'),
        html.Div(dbc.Row([dbc.Col(draftpanel, md=3),
                 dbc.Col(pickspanel, md=4),
                 dbc.Col(projpanel, md=5)])
                ,id = 'main-section',style = {'display':'none'})
],fluid=True)


# #######################
# # Reactive callbacks
# #######################
@app.callback(
    Output('roster','children'),
    [Input('n-of-dropdown','value'),
     Input('n-p-dropdown','value'),
     Input('n-ut-dropdown','value'),
     Input('n-be-dropdown','value'),
     Input('begin-button','n_clicks')]
)
def update_roster(n_of,n_p,n_ut,n_be,n_clicks):
    slots = (['C','1B','2B','3B','SS'] + 
             ['OF'+str(i+1) for i in range(n_of)] + 
             ['P'+str(i+1) for i in range(n_p)] + 
             ['UT'+str(i+1) for i in range(n_ut)] + 
             ['BE'+str(i+1) for i in range(n_be)])
    
    roster = pd.DataFrame({'Slot': slots,'Num': list(range(len(slots)))})
    return roster.to_json()

@app.callback(
    Output('position-dropdown', 'options'),
    [Input('n-teams-dropdown', 'value')]
)
def update_date_dropdown(num_teams):
    return list(range(1,num_teams+1))

@app.callback(
    [Output('pick-dropdown','options')],
    [Input('players','children')]
)
def update_pick_options(players_json):
    pl = pd.read_json(players_json)
    pl = pl.loc[pl.Available]
    return [list(pl.Rank.astype(str)+'. '+pl.Player+' ('+pl['Position(s)']+')')]

@app.callback(
    Output('last-picks-table', 'children'),
    [Input('picks','children')],
    [State('n-teams','children')]
)
def update_last_picks_table(picks_json,n_teams):
    picks = pd.read_json(picks_json)
    last_picks = picks.iloc[-2*n_teams:]
    return make_table(last_picks)
    
@app.callback(
    Output('roster-table', 'children'),
    [Input('picks','children'),
     Input('team-roster-dropdown','value')],
    [State('roster','children')]
)
def update_roster_table(picks_json,teamchoice,roster_json):
    ros = pd.read_json(roster_json)
    px = pd.read_json(picks_json)
    teampx = px.loc[px.Team == teamchoice]
    ret = ros.merge(teampx,on='Slot',how='left').sort_values('Num')
    return make_table(ret[['Slot','Player','Round']])

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
    [Output('proj-standings-table','children'),
     Output('proj-toggle-label','children')],
    [Input('players','children'),
     Input('proj-style-toggle','value')]    
)
def update_proj_standings(players_json,toggle):
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
    
    if toggle:
        return make_table(rdf.sort_values('Score')), 'Show Ranks'
    else:
        dfg['Score'] = rdf.Score
        return make_table(dfg[rdf.columns].sort_values('Score')), 'Show Stats'
    
@app.callback(
    [Output('n-teams','children'),
     Output('position','children'),
     Output('pick-number','children'),
     Output('picks','children'),
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
     State('picks','children'),
     State('players','children'),
     State('roster','children')]
)
def update_data(begin_clicks,n_teams,position,draft_clicks,pick,
                prev_n_teams,prev_position,pick_number,prev_opts,
                prev_style1,prev_style2,picks_json,players_json,roster_json):
    if begin_clicks is not None:
    
        # prepare data frames
        px = pd.DataFrame({'Team':[],'Position':[],'Player':[],'Round':[],'Pick':[],'Slot':[]})
        pl = pd.read_json(players_json)
        ros = pd.read_json(roster_json)
    
        # initial autopicks    
        px, pl = get_auto_picks(1, position, px, pl, n_teams, ros)   
        
        # list of team names
        opts = ['My-Team'] + [teamnames[i] for i in range(1,n_teams+1) if i != position]
        return (n_teams, position, position, px.to_json(), pl.to_json(),
                None, None, opts, {'display':'block'}, {'display':'none'})

    elif draft_clicks is not None:
        
        pl = pd.read_json(players_json)
        pickrank = int(pick.split('.')[0])
        pick_idx = pl.loc[pl.Rank == pickrank].index[0]
        pos = pl.loc[pick_idx,'Position(s)']
        
        px = pd.read_json(picks_json)
        ros = pd.read_json(roster_json)
        
        px = px.append({'Team':'My-Team'
                        ,'Position': pos
                        ,'Player':pl.loc[pick_idx,'Player']
                        ,'Round':(pick_number-1) // n_teams + 1
                        ,'Pick':(pick_number-1) % n_teams + 1
                        ,'Slot':determine_slot(pos,ros,px.loc[px.Team == 'My-Team'])}
                      ,ignore_index = True)
        
        pl.loc[pick_idx,'Available'] = False
        pl.loc[pick_idx,'Team'] = 'My-Team'

        # auto draft to next human pick or end of draft
        human_picks = [position, (2*n_teams + 1 - position)] 
        end_pick = pick_number+1
        while (end_pick % (n_teams*2) not in human_picks) & (end_pick <= len(ros.Num)*n_teams): 
            end_pick += 1
        
        px, pl = get_auto_picks(pick_number+1,end_pick,px,pl,n_teams,ros)
        
        return (n_teams, position, end_pick, px.to_json(), pl.to_json(), 
                None, None, prev_opts, prev_style1, prev_style2)
    else:
        return (prev_n_teams, prev_position, pick_number, picks_json, players_json, 
                None, None, prev_opts, prev_style1, prev_style2)
    
@app.callback(
    Output('draft-panel','style'),
    [Input('pick-number','children')],
    [State('n-teams','children'),
     State('roster','children'),
     State('draft-panel','style')]
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