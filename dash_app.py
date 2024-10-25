from dash import Dash, html, dcc

figures = []


def generate_dash_app():
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.layout = html.Div(
        [
            html.H1("Bitcoin Chart Pack"),
            html.Div(
                id="content-area",
                children=[
                    dcc.Graph(id="graph-{}".format(i), figure=fig)
                    for i, fig in enumerate(figures)
                ],
            ),
        ]
    )
    return app
