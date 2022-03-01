import json
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd

def main_pie(data):

    labels = []
    values = []
    for label, value, debt in data:

        labels.append(label)
        values.append(value)

    # Use `hole` to create a donut-like pie chart
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json


def main_sunburst(data, colour_scale):

    
    df = pd.DataFrame(data, columns=['ID', 'TYPE', 'ILK', 'TOKEN', 'VALUE_LOCKED', 'DEBT'])
    fig = px.sunburst(
        df,
        path=['TYPE', 'TOKEN', 'ILK'],
        values='VALUE_LOCKED',
        color='VALUE_LOCKED',
        hover_data={
            'DEBT':':,.2f',
        },
        color_continuous_scale = 'Sunsetdark',
    )

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graph_json