import dash
from dash import dcc
from dash import html
import networkx as nx
import plotly.graph_objs as go
import pandas as pd
from textwrap import dedent as d
import json
import utm
import math

"""
Interactive web-app to visualization the PI network and its flows
"""

# choose situation to visualize
folder = 'networks/network-europe-volume'
orderfreq_mult = 1

# import the css template, and pass the css template into dash
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Physical Internet"

# get data to visualize
parameters = pd.read_csv(f'{folder}/input/parameters.csv')
nodes = pd.read_csv(f'{folder}/input/nodes.csv')
output_folder = f'{folder}/output/orderfreq_{orderfreq_mult}'
Transports = pd.read_csv(f'{output_folder}/transports.csv')
Transports['arc'] = Transports['startnode'] + ' => ' + Transports['endnode']

# rescale x and y coordinates to between 0 and 1
x = []; y = []
for idx in range(nodes.shape[0]):
    xval, yval, zone, zonel = utm.from_latlon(nodes['lat'][idx], nodes['lon'][idx], force_zone_number=31, force_zone_letter='U')
    x.append(xval); y.append(yval)
nodes['x'] = x
nodes['y'] = y
nodes['x'] = 2 * ((nodes['x'] - min(nodes['x'])) / (max(nodes['x']) - min(nodes['x']))) - 1
nodes['y'] = 2 * ((nodes['y'] - min(nodes['y'])) / (max(nodes['y']) - min(nodes['y']))) - 1

# initial time range and flow to visualize
SIM_TIME = float(parameters['sim_days'])*24
timeRange = [0, SIM_TIME]
flow = 'Containers'

def network_graph(timeRange,flow,nodes=nodes,Transports=Transports):

    # only keep data within time window
    TimeSubset = Transports.loc[timeRange[0]<Transports['endtime'].values]
    TimeSubset = TimeSubset.loc[TimeSubset['endtime'].values<timeRange[1]]

    # initialize graph
    G = nx.DiGraph()
    for idx in range(nodes.shape[0]):
        name,_,_,numforklifts,numtrucks,x,y = nodes.iloc[idx]
        G.add_node(name)
        G.nodes[name]['name'] = name
        G.nodes[name]['numforklifts'] = numforklifts
        G.nodes[name]['numtrucks'] = numtrucks
        G.nodes[name]['pos'] = [x,y]

    # calculate flows and assign to edge weights
    maxflow = 0
    for arc in TimeSubset['arc'].unique():
        Subset = TimeSubset.loc[TimeSubset['arc'].values == arc]
        startid,endid = Subset.iloc[0][1:3]

        if flow == 'Containers':
            weight = sum(Subset['load'])
            if weight > 0:
                G.add_edge(startid,endid,weight=weight)
                maxflow = max(maxflow,sum(Subset['load']))
        elif flow == 'Trucks':
            weight = Subset.shape[0]
            if weight > 0:
                G.add_edge(startid,endid,weight=weight)
                maxflow = max(maxflow,Subset.shape[0])

    # draw edges between nodes
    traceRecode = []
    for edge in G.edges:
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        weight = float(G.edges[edge]['weight']) / maxflow * 10
        d = 0.05
        dx = x0-x1
        dy = y0-y1
        dist = math.sqrt(dx*dx + dy*dy)
        dx /= dist
        dy /= dist
        G.edges[edge]['pos'] = [[x0-d*dy, x1-d*dy],[y0+d*dx, y1+d*dx]]
        trace = go.Scatter(x=[x0-d*dy, x1-d*dy], y=[y0+d*dx, y1+d*dx],
                           mode='lines',
                           line={'width': weight},
                           marker=dict(color='rgb(255, 175, 14)'),
                           line_shape='spline',
                           opacity=1)
        traceRecode.append(trace)

    # draw nodes
    node_trace = go.Scatter(x=[], y=[], hovertext=[], text=[], mode='markers+text', textposition="middle center",
                            hoverinfo="text", marker={'size': 60, 'color': 'LightSkyBlue'})
    for node in G.nodes:
        x,y = G.nodes[node]['pos']
        hovertext = "NumForklifts: " + str(
            G.nodes[node]['numforklifts']) + "<br>" + "NumTrucks: " + str(
            G.nodes[node]['numtrucks'])
        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])
        node_trace['hovertext'] += tuple([hovertext])
        node_trace['text'] += tuple([node])

    traceRecode.append(node_trace)

    # draw entire figure and add arrows on the edges
    figure = {
        "data": traceRecode,
        "layout": go.Layout(title='', showlegend=False, hovermode='closest',
                            margin={'b': 10, 'l': 10, 'r': 10, 't': 10},
                            xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                            yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                            height=700,
                            width=700,
                            clickmode='event+select',
                            annotations=[
                                dict(
                                    ax=sum(G.edges[edge]['pos'][0]) / 2,
                                    ay=sum(G.edges[edge]['pos'][1]) / 2, axref='x', ayref='y',
                                    x=(G.edges[edge]['pos'][0][1] * 2 + G.edges[edge]['pos'][0][0] * 1) / 3,
                                    y=(G.edges[edge]['pos'][1][1] * 2 + G.edges[edge]['pos'][1][0] * 1) / 3, xref='x', yref='y',
                                    showarrow=True,
                                    arrowhead=3,
                                    arrowsize=2*20,
                                    arrowwidth=0.1,
                                    opacity=1
                                ) for edge in G.edges]
                            )}
    return figure

# HTML style and layout of web-app
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}
app.layout = html.Div([
    html.Div([html.H1("Physical internet interactive visualization")],
             className="row",
             style={'textAlign': "center"}),
    html.Div(
        className="row",
        children=[
            html.Div(
                className="two columns",
                children=[
                    dcc.Markdown(d("""
                            **Time Range To Visualize**

                            Slide the bar to define the time range.
                            """)),
                    html.Div(
                        className="twelve columns",
                        children=[
                            dcc.RangeSlider(
                                id='my-range-slider',
                                min=0,
                                max=SIM_TIME,
                                step=24,
                                value=[0, SIM_TIME],
                                marks={
                                    0: {'label': 'Day 0'},
                                    SIM_TIME: {'label': f'Day {SIM_TIME/24}'}
                                }
                            ),
                            html.Br(),
                            html.Div(id='output-container-range-slider')
                        ],
                        style={'height': '300px'}
                    ),
                    html.Div(
                        className="twelve columns",
                        children=[
                            dcc.Markdown(d("""
                            **Flow to visualize**

                            Input the flow metric to visualize.
                            """)),
                            dcc.RadioItems(['Containers', 'Trucks'],'Containers',id='input1',inline=True),
                            html.Div(id="output")
                        ],
                        style={'height': '300px'}
                    )
                ],
            ),
            html.Div(
                className="eight columns",
                children=[dcc.Graph(id="my-graph",
                                    figure=network_graph(timeRange,flow))],
                style={'textAlign': "center"},
            ),
           html.Div(
                className="two columns",
                children=[
                    html.Div(
                        className='twelve columns',
                        children=[
                            dcc.Markdown(d("""
                            **Orders from source node**

                            Click on nodes in the graph to see generated orders.
                            """)),
                            html.Pre(id='click-data', style=styles['pre'])
                        ],
                        style={'height': '400px'})
                ]
            )
        ]
    )
])

# callback for visualization options
@app.callback(
    dash.dependencies.Output('my-graph', 'figure'),
    [dash.dependencies.Input('my-range-slider', 'value'), dash.dependencies.Input('input1', 'value')])
def update_output(value,input1):
    timeRange = value
    flow = input1
    return network_graph(timeRange, flow)

# callback for order data
@app.callback(
    dash.dependencies.Output('click-data', 'children'),
    [dash.dependencies.Input('my-graph', 'clickData')])
def display_click_data(clickData):
    orders = pd.read_csv(f'{folder}/input/orders.csv')
    if clickData:
        start = clickData['points'][0]['text']
        orders = orders.loc[orders['source'] == start]
        result = orders.to_json(orient="index")
        parsed = json.loads(result)
        return json.dumps(parsed, indent=4)

if __name__ == '__main__':
    app.run_server(debug=True)