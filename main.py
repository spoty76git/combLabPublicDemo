import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

# Import layouts and callbacks from pages
from homepage import (
    layout as homepage_layout,
    register_callbacks as register_homepage_callbacks,
)
from performance import (
    layout as performance_layout,
    register_callbacks as register_performance_callbacks,
)

# Initialize the Dash app with Bootswatch dark theme
# Use themes: CYBORG, DARKLY, SLATE, SOLAR, SUPERHERO, VAPOR (currently DARKLY for dark mode tech vibe)
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    assets_folder="assets",
)

# App configuration
app.title = "Combustion Lab Dashboard"

# Server instance for deployment
server = app.server

# Navigation bar
navbar = html.Div(
    [
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(
                    dbc.NavLink(
                        "Visualization",
                        href="/",
                        active="exact",
                        style={
                            "fontSize": "1.1rem",
                        },
                    )
                ),
                dbc.NavItem(
                    dbc.NavLink(
                        "Tracking",
                        href="/tracking",
                        active="exact",
                        style={
                            "fontSize": "1.1rem",
                        },
                    )
                ),
            ],
            brand=[
                html.Div(
                    [
                        html.Img(
                            src="/assets/lab.png",
                            height="50",
                            className="me-3 align-self-center",
                        ),
                        html.Div(
                            [
                                html.Strong(
                                    "Ben T. Zinn Lab CFD Dashboard",
                                    style={
                                        "fontSize": "1.5rem",
                                        "lineHeight": "1.2",
                                        "marginBottom": "0.2rem",
                                    },
                                ),
                                html.Small(
                                    [
                                        "Created by ",
                                        html.A(
                                            "Adil Shirinov",
                                            href="https://www.linkedin.com/in/adilsh/",
                                            target="_blank",
                                            rel="noopener noreferrer",
                                            className="text-decoration-none",
                                            style={
                                                "color": "#17a2b8",
                                                "transition": "color 0.3s ease",
                                            },
                                        ),
                                    ],
                                    className="text-muted",
                                    style={"fontSize": "0.9rem"},
                                ),
                            ],
                            className="d-flex flex-column",
                        ),
                    ],
                    className="d-flex align-items-center",
                )
            ],
            brand_href="https://www.linkedin.com/in/adilsh/",
            color="dark",
            dark=True,
            className="mb-0",
        ),
    ],
    className="mb-2",
)

# Set the app layout
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        navbar,
        html.Div(id="page-content", className="flex-grow-1"),
 
    ],
    className="d-flex flex-column min-vh-100",  # Full height layout
)


# Register page callbacks
@app.callback(
    dash.dependencies.Output("page-content", "children"),
    [dash.dependencies.Input("url", "pathname")],
)
def display_page(pathname):
    if pathname == "/" or pathname is None:
        return homepage_layout
    elif pathname == "/tracking":
        return performance_layout
    else:
        return html.Div(
            [
                html.H1("404: Page not found", className="text-center mt-5"),
                html.P("The requested page was not found.", className="text-center"),
                dcc.Link("Go to Home", href="/", className="text-center d-block"),
            ]
        )


# Register all callbacks
register_homepage_callbacks(app)
register_performance_callbacks(app)

if __name__ == "__main__":
    
    app.run(debug=False)
