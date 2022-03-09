import json
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd


def main_bar(data):

    df = pd.DataFrame(data, columns=['TYPE', 'VALUE_LOCKED', 'DEBT'])
    data = []
    data.append(go.Bar(
        x=df['TYPE'].tolist(),
        y=df['VALUE_LOCKED'].tolist(),
        name='Value locked (USD)',
        marker_color='#dddddd'
    ))

    data.append(go.Bar(
        x=df['TYPE'].tolist(),
        y=df['DEBT'].tolist(),
        name='Debt (DAI)',
        marker_color='#1aab9b'
    ))

    # Here we modify the tickangle of the xaxis, resulting in rotated labels.
    layout = go.Layout(
        title= {"text": "Value locked (USD) & debt (DAI) split by vault type", "x": 0.5, "xanchor": "center"},
        barmode='group',
        xaxis_tickangle= -45,
        hovermode= "x unified",
        paper_bgcolor= "#fcfcfc",
        plot_bgcolor= "#fcfcfc"
        )
    
    fig = go.Figure(data=data, layout=layout)
    fig.update_traces(hovertemplate="%{y:,.2f}<extra></extra>")

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json