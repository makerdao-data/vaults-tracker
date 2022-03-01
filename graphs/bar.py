import json
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd


def main_bar(data):

    df = pd.DataFrame(data, columns=['TYPE', 'VALUE_LOCKED', 'DEBT'])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['TYPE'].tolist(),
        y=df['VALUE_LOCKED'].tolist(),
        name='Value locked (USD)',
        marker_color='#dddddd'
    ))
    fig.add_trace(go.Bar(
        x=df['TYPE'].tolist(),
        y=df['DEBT'].tolist(),
        name='Debt (DAI)',
        marker_color='#1aab9b'
    ))

    # Here we modify the tickangle of the xaxis, resulting in rotated labels.
    fig.update_layout(
        title= {'text': 'Value locked (USD) & debt (DAI) split by vault type'},
        barmode='group',
        xaxis_tickangle= -45,
        xaxis_tick0= 1,
        )

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json