"""
Dash App Module - Bitcoin Chart Library Web Interface

This module provides a simple Dash web application to display all generated
Bitcoin analytics charts in a scrollable webpage.
"""

from dash import Dash, html, dcc

# Global list populated by main.py with Plotly figure objects
figures = []


def generate_dash_app():
    """
    Create and configure the Dash application with all charts.

    Returns:
    Dash: Configured Dash app with layout containing all figures.
    """
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
