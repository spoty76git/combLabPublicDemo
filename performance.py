import dash
from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime



# Import database utilities
from db_utils import CFDDatabase, SCHEMA

# Initialize database
db = CFDDatabase()

# Helper function to create form inputs dynamically
def create_parameter_inputs(param_type, id_prefix="new-"):
    """Create input fields based on schema parameters"""
    inputs = []
    params = SCHEMA.get(param_type, {})

    # Group parameters into rows of 3
    param_items = list(params.items())
    for i in range(0, len(param_items), 3):
        row_items = param_items[i : i + 3]
        row_cols = []

        for param_name, param_info in row_items:
            label = param_name.replace("_", " ").title()
            if param_info.get("unit") and param_info["unit"] != "-":
                label += f" ({param_info['unit']})"

            col = dbc.Col(
                [
                    dbc.Label(label),
                    dbc.Input(
                        id=f"{id_prefix}{param_name}",
                        type="number",
                        value=param_info.get("default"),
                        step=0.01 if param_info["type"] == "REAL" else 1,
                    ),
                ],
                width=4,
            )
            row_cols.append(col)

        inputs.append(dbc.Row(row_cols, className="mb-2"))

    return inputs


# Helper function to get parameter options for dropdowns
def get_parameter_options():
    """Get parameter options for dropdown selection"""
    options = []

    # Add design parameters
    for param_name, param_info in SCHEMA["design_parameters"].items():
        label = param_name.replace("_", " ").title()
        if param_info.get("unit") and param_info["unit"] != "-":
            label += f" ({param_info['unit']})"
        options.append({"label": label, "value": param_name})

    return options


# Helper function to get metrics for radar chart
def get_radar_metrics():
    """Get metrics suitable for radar chart visualization"""
    # Select key performance metrics for radar chart
    metrics = []
    metric_labels = []

    # Prioritize certain metrics if they exist
    priority_metrics = [
        "nox_emissions",
        "co_emissions",
        "pattern_factor",
        "combustion_efficiency",
        "mixing_quality",
    ]

    for metric in priority_metrics:
        if metric in SCHEMA["performance_metrics"]:
            metrics.append(metric)
            # Add directional indicator
            if metric in ["nox_emissions", "co_emissions", "pattern_factor"]:
                metric_labels.append(metric.replace("_", " ").title() + "↓")
            else:
                metric_labels.append(metric.replace("_", " ").title() + "↑")

    # If we don't have enough metrics, add more
    if len(metrics) < 5:
        for metric_name in SCHEMA["performance_metrics"]:
            if metric_name not in metrics and len(metrics) < 5:
                metrics.append(metric_name)
                metric_labels.append(metric_name.replace("_", " ").title())

    return metrics, metric_labels


# Layout
layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H1(
                                            "Performance Tracking & Analysis",
                                            className="text-center text-primary mb-2",
                                        ),
                                        html.P(
                                            "Not ACTUAL lab data, examples for demonstration purposes only!",
                                            className="text-center text-danger mb-0 fw-bold",
                                            style={
                                                "background-color": "rgba(255, 0, 0, 0.1)",
                                                "padding": "8px",
                                                "border-radius": "4px",
                                                "border-left": "4px solid #dc3545",
                                                "border-right": "4px solid #dc3545",
                                            },
                                        ),
                                    ]
                                )
                            ],
                            className="bg-dark border-0 shadow-lg mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Control Panel and Summary Cards
        dbc.Row(
            [
                # Left Panel - Case Selection and Filters
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="fas fa-filter me-2"),
                                                "Case Selection",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Label(
                                            "Select Cases to Compare",
                                            className="text-warning",
                                        ),
                                        dcc.Dropdown(
                                            id="case-selector",
                                            options=[],
                                            value=[],
                                            multi=True,
                                            placeholder="Select cases... (all selected by default)",
                                            className="mb-3 darkly-dropdown",
                                        ),
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "Select All",
                                                    id="select-all-btn",
                                                    color="info",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Clear All",
                                                    id="clear-all-btn",
                                                    color="secondary",
                                                    size="sm",
                                                ),
                                            ],
                                            className="mb-3 w-100",
                                        ),
                                        html.Hr(),
                                        dbc.Label(
                                            "Time Range Filter",
                                            className="text-warning",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dcc.DatePickerRange(
                                                        id="date-range-picker",
                                                        start_date_placeholder_text="Start Date",
                                                        end_date_placeholder_text="End Date",
                                                        display_format="YYYY-MM-DD",
                                                        className="mb-3 w-100",
                                                    ),
                                                    width=10,
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        html.I(
                                                            className="fas fa-times"
                                                        ),
                                                        id="clear-dates-button",
                                                        color="danger",
                                                        className="mb-3",
                                                        n_clicks=0,
                                                    ),
                                                    width=2,
                                                    className="d-flex align-items-left",
                                                ),
                                            ],
                                            className="g-2",  # gutter spacing
                                        ),
                                        html.Hr(),
                                        # Add New Case Button
                                        dbc.Button(
                                            [
                                                html.I(className="fas fa-plus me-2"),
                                                "Add New Case",
                                            ],
                                            id="add-case-btn",
                                            color="success",
                                            className="w-100 mb-3",
                                        ),
                                    ],
                                    className="p-3",
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=3,
                ),
                # Summary Cards
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            "Best NOx Performance",
                                                            className="text-warning",
                                                        ),
                                                        html.H3(
                                                            id="best-nox-value",
                                                            children="--",
                                                            className="text-success mb-1",
                                                        ),
                                                        html.P(
                                                            id="best-nox-case",
                                                            children="No data",
                                                            className="text-muted mb-0 small",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-dark text-center shadow",
                                        )
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            "Best Efficiency",
                                                            className="text-warning",
                                                        ),
                                                        html.H3(
                                                            id="best-efficiency-value",
                                                            children="--",
                                                            className="text-info mb-1",
                                                        ),
                                                        html.P(
                                                            id="best-efficiency-case",
                                                            children="No data",
                                                            className="text-muted mb-0 small",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-dark text-center shadow",
                                        )
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            "Lowest Adiabatic Flame Temperature",
                                                            className="text-warning",
                                                        ),
                                                        html.H3(
                                                            id="best-temp-value",
                                                            children="--",
                                                            className="text-info mb-1",
                                                        ),
                                                        html.P(
                                                            id="best-temp-case",
                                                            children="No data",
                                                            className="text-muted mb-0 small",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-dark text-center shadow",
                                        )
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            "Total Cases",
                                                            className="text-warning",
                                                        ),
                                                        html.H3(
                                                            id="total-cases",
                                                            children="0",
                                                            className="text-secondary mb-1",
                                                        ),
                                                        html.P(
                                                            "Completed",
                                                            className="text-muted mb-0 small",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-dark text-center shadow",
                                        )
                                    ],
                                    width=3,
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=9,
                ),
            ]
        ),
        # Main Visualization Area
        dbc.Row(
            [
                # Graph 1: Primary Emissions Comparison
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-chart-bar me-2"
                                                ),
                                                "Emissions Comparison",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-emissions",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="emissions-comparison-plot",
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=6,
                ),
                # Graph 2: Temperature Distribution
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-thermometer-half me-2"
                                                ),
                                                "Temperature Performance",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-temp",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="temperature-plot",
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=6,
                ),
            ]
        ),
        dbc.Row(
            [
                # Graph 3: Design Parameters Correlation
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-project-diagram me-2"
                                                ),
                                                "Design Parameters Correlation",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Label("X-Axis Parameter"),
                                                        dbc.Select(
                                                            id="param-x-selector",
                                                            options=get_parameter_options(),
                                                            value=list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[0],
                                                            className="mb-2",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Y-Axis Metric"),
                                                        dbc.Select(
                                                            id="param-y-selector",
                                                            options=[
                                                                {
                                                                    "label": k.replace(
                                                                        "_", " "
                                                                    ).title(),
                                                                    "value": k,
                                                                }
                                                                for k in SCHEMA[
                                                                    "performance_metrics"
                                                                ]
                                                            ],
                                                            value=list(
                                                                SCHEMA[
                                                                    "performance_metrics"
                                                                ].keys()
                                                            )[0],
                                                            className="mb-2",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                            ]
                                        ),
                                        dcc.Loading(
                                            id="loading-correlation",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="correlation-plot",
                                                )
                                            ],
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=6,
                ),
                # Graph 4: Performance Radar Chart
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-chart-radar me-2"
                                                ),
                                                "Multi-Parameter Performance",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-radar",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="radar-plot",
                                                )
                                            ],
                                        )
                                    ],
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=6,
                ),
            ]
        ),
        dbc.Row(
            [
                # Graph 5: Time Series Evolution
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-chart-line me-2"
                                                ),
                                                "Performance Evolution Over Time",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-timeline",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="timeline-plot",
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        dbc.Row(
            [
                # Graph 6: 3D Parameter Space
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="fas fa-cube me-2"),
                                                "3D Design Space Exploration",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Label("X-Axis"),
                                                        dbc.Select(
                                                            id="3d-x-selector",
                                                            options=get_parameter_options(),
                                                            value=list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[0],
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Y-Axis"),
                                                        dbc.Select(
                                                            id="3d-y-selector",
                                                            options=get_parameter_options(),
                                                            value=list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[1]
                                                            if len(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ]
                                                            )
                                                            > 1
                                                            else list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[0],
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Z-Axis"),
                                                        dbc.Select(
                                                            id="3d-z-selector",
                                                            options=get_parameter_options(),
                                                            value=list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[2]
                                                            if len(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ]
                                                            )
                                                            > 2
                                                            else list(
                                                                SCHEMA[
                                                                    "design_parameters"
                                                                ].keys()
                                                            )[0],
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dcc.Loading(
                                            id="loading-3d",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="parameter-3d-plot",
                                                )
                                            ],
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Detailed Data Table
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="fas fa-table me-2"),
                                                "Detailed Case Data",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody([html.Div(id="data-table-container")]),
                            ],
                            className="shadow-lg",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Add New Case Modal
        dbc.Modal(
            [
                dbc.ModalHeader("Add New Case"),
                dbc.ModalBody(
                    [
                        dbc.Form(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Case Name"),
                                                dbc.Input(
                                                    id="new-case-name",
                                                    placeholder="e.g., Opt_Design_X",
                                                ),
                                            ],
                                            width=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Status"),
                                                dbc.Select(
                                                    id="new-case-status",
                                                    options=[
                                                        {
                                                            "label": "Planned",
                                                            "value": "planned",
                                                        },
                                                        {
                                                            "label": "Running",
                                                            "value": "running",
                                                        },
                                                        {
                                                            "label": "Completed",
                                                            "value": "completed",
                                                        },
                                                    ],
                                                    value="planned",
                                                ),
                                            ],
                                            width=6,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Description"),
                                                dbc.Input(
                                                    id="new-case-desc",
                                                    placeholder="Brief description",
                                                ),
                                            ],
                                            width=12,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Timestamp"),
                                                dcc.DatePickerSingle(
                                                    id="case-timestamp",
                                                    date=datetime.today(),
                                                    display_format="YYYY-MM-DD",
                                                    placeholder="Select date",
                                                    className="mb-3 w-100",
                                                    clearable=True,
                                                ),
                                            ],
                                            width=12,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                html.H6(
                                    "Design Parameters",
                                    className="text-warning mt-3 mb-2",
                                ),
                                html.Div(
                                    id="design-parameters-inputs",
                                    children=create_parameter_inputs(
                                        "design_parameters"
                                    ),
                                ),
                                # Performance Metrics Section (hidden by default)
                                html.Div(
                                    [
                                        html.Hr(),
                                        html.H6(
                                            "Performance Metrics",
                                            className="text-warning mt-3 mb-2",
                                        ),
                                        html.Div(
                                            id="performance-metrics-inputs",
                                            children=create_parameter_inputs(
                                                "performance_metrics"
                                            ),
                                        ),
                                    ],
                                    id="performance-metrics-section",
                                    style={"display": "none"},
                                ),
                            ]
                        )
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="cancel-btn", color="secondary"),
                        dbc.Button("Add Case", id="save-case-btn", color="primary"),
                    ]
                ),
            ],
            id="add-case-modal",
            is_open=False,
            size="lg",
        ),
        # Hidden div to store refresh trigger
        html.Div(id="refresh-trigger", children="init", style={"display": "none"}),
        # Add Font Awesome
        html.Link(
            rel="stylesheet",
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        ),
    ],
    fluid=True,
    id="main-content-container",
    className="py-3",
)


# Callbacks
def register_callbacks(app):
    
    # Update case selector options
    @app.callback(
        [
            Output("case-selector", "options"),
            Output("date-range-picker", "start_date"),
            Output("date-range-picker", "end_date"),
        ],
        [Input("refresh-trigger", "data")],
    )
    def update_case_options(_):
        try:
            # Fetch all cases from the database
            df = db.get_all_cases()
            if df.empty:
                print("No cases found in the database (case selector)")
                return [], None, None

            # Get unique cases
            cases_df = df[["case_name", "status", "timestamp"]].drop_duplicates(
                subset=["case_name"]
            )

            options = [
                {
                    "label": f"{row['case_name']} ({row['status']})",
                    "value": row["case_name"],
                }
                for _, row in cases_df.iterrows()
            ]

            start_date = df["timestamp"].min()
            end_date = df["timestamp"].max()

            return options, start_date, end_date

        except Exception as e:
            print(f"Callback error: {str(e)}")
            raise

    # Select/Clear all buttons
    @app.callback(
        Output("case-selector", "value"),
        [Input("select-all-btn", "n_clicks"), Input("clear-all-btn", "n_clicks")],
        [State("case-selector", "options")],
    )
    def select_clear_all(select_clicks, clear_clicks, options):
        ctx = callback_context
        if not ctx.triggered:
            return []

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "select-all-btn" and options:
            return [opt["value"] for opt in options]
        return []
    
    # Clear date range picker
    @app.callback(
        Output("date-range-picker", "start_date", allow_duplicate=True),
        Output("date-range-picker", "end_date", allow_duplicate=True),
        Input("clear-dates-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_dates(n_clicks):
        if n_clicks:
            return None, None
        return dash.no_update, dash.no_update

    # Update summary cards
    @app.callback(
        [
            Output("best-nox-value", "children"),
            Output("best-nox-case", "children"),
            Output("best-efficiency-value", "children"),
            Output("best-efficiency-case", "children"),
            Output("best-temp-value", "children"),
            Output("best-temp-case", "children"),
            Output("total-cases", "children"),
        ],
        [
            Input("case-selector", "value"),
            Input("date-range-picker", "start_date"),
            Input("date-range-picker", "end_date"),
        ],
    )
    def update_summary_cards(selected_cases, start_date, end_date):
        df = db.get_all_cases()

        # Filter by date if provided
        if start_date and end_date:
            df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]

        # Filter completed cases
        df_complete = df[df["status"] == "completed"]

        # Dynamic summary based on available metrics
        best_nox_val = "--"
        best_nox_case = "No data"
        best_eff_val = "--"
        best_eff_case = "No data"
        best_pattern_val = "--"
        best_pattern_case = "No data"

        # Check for NOx emissions
        if "nox_emissions" in df_complete.columns:
            df_nox = df_complete.dropna(subset=["nox_emissions"])
            if not df_nox.empty:
                best_row = df_nox.loc[df_nox["nox_emissions"].idxmin()]
                best_nox_val = f"{best_row['nox_emissions']:.1f} ppm"
                best_nox_case = best_row["case_name"]

        # Check for efficiency
        if "combustion_efficiency" in df_complete.columns:
            df_eff = df_complete.dropna(subset=["combustion_efficiency"])
            if not df_eff.empty:
                best_row = df_eff.loc[df_eff["combustion_efficiency"].idxmax()]
                best_eff_val = f"{best_row['combustion_efficiency']:.1f}%"
                best_eff_case = best_row["case_name"]

        # Check for pattern factor
        if "temperature_max" in df_complete.columns:
            df_pattern = df_complete.dropna(subset=["temperature_max"])
            if not df_pattern.empty:
                best_row = df_pattern.loc[df_pattern["temperature_max"].idxmin()]
                best_pattern_val = f"{best_row['temperature_max']:.1f} K"
                best_pattern_case = best_row["case_name"]

        total_complete = len(df_complete)

        # Quick stats
        stats_content = []
        if selected_cases:
            selected_df = df[df["case_name"].isin(selected_cases)]
            stats_content.append(
                html.P(f"Selected: {len(selected_cases)}", className="mb-1")
            )
            stats_content.append(
                html.P(
                    f"Completed: {len(selected_df[selected_df['status'] == 'completed'])}",
                    className="mb-1",
                )
            )
            stats_content.append(
                html.P(
                    f"Running: {len(selected_df[selected_df['status'] == 'running'])}",
                    className="mb-0",
                )
            )
        else:
            stats_content.append(html.P("No cases selected", className="text-muted"))

        return (
            best_nox_val,
            best_nox_case,
            best_eff_val,
            best_eff_case,
            best_pattern_val,
            best_pattern_case,
            str(total_complete),
        )

    # Show/hide performance metrics based on status
    @app.callback(
        Output("performance-metrics-section", "style"),
        Input("new-case-status", "value"),
    )
    def toggle_performance_section(status):
        if status == "completed":
            return {"display": "block"}
        return {"display": "none"}

    # Modal toggle
    @app.callback(
        Output("add-case-modal", "is_open"),
        [
            Input("add-case-btn", "n_clicks"),
            Input("cancel-btn", "n_clicks"),
            Input("save-case-btn", "n_clicks"),
        ],
        [State("add-case-modal", "is_open")],
    )
    def toggle_modal(add_clicks, cancel_clicks, save_clicks, is_open):
        if add_clicks or cancel_clicks or save_clicks:
            return not is_open
        return is_open

    # Dynamic callback for saving new case with all parameters
    @app.callback(
        Output("refresh-trigger", "children"),
        [Input("save-case-btn", "n_clicks"),
         Input("case-timestamp", "date")],
        [
            State("new-case-name", "value"),
            State("new-case-desc", "value"),
            State("new-case-status", "value"),
        ]
        +
        # Dynamically add all design parameter states
        [State(f"new-{param}", "value") for param in SCHEMA["design_parameters"]]
        +
        # Dynamically add all performance metric states
        [State(f"new-{metric}", "value") for metric in SCHEMA["performance_metrics"]],
    )
    def save_new_case(n_clicks, case_date, name, desc, status, *args):
        if not n_clicks or not name:
            return no_update

        # Split args into design parameters and performance metrics
        design_param_values = args[: len(SCHEMA["design_parameters"])]
        performance_metric_values = args[len(SCHEMA["design_parameters"]) :]

        # Prepare design parameters
        design_params = {}
        for i, (param_name, param_info) in enumerate(
            SCHEMA["design_parameters"].items()
        ):
            value = design_param_values[i]
            if value is None:
                value = param_info.get("default", 0)
            design_params[param_name] = value

        # Prepare performance metrics if status is completed
        performance_metrics = None
        if status == "completed":
            # Check if any performance metric has been provided
            has_metrics = any(v is not None for v in performance_metric_values)
            if has_metrics:
                performance_metrics = {}
                for i, metric_name in enumerate(SCHEMA["performance_metrics"].keys()):
                    value = performance_metric_values[i]
                    if value is not None:
                        performance_metrics[metric_name] = value

        # Insert the case
        success = db.insert_case(
            name, desc or "", status, case_date, design_params, performance_metrics
        )

        if success:
            return "refresh"
        else:
            return no_update

    # Graph 1: Emissions Comparison (Dynamic)
    @app.callback(
        Output("emissions-comparison-plot", "figure"), [Input("case-selector", "value")]
    )
    def update_emissions_plot(selected_cases):
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]

        # Find emission-related metrics
        emission_metrics = []
        for metric in SCHEMA["performance_metrics"]:
            if "emission" in metric.lower() or metric in [
                "nox_emissions",
                "co_emissions",
            ]:
                if metric in df_complete.columns:
                    emission_metrics.append(metric)

        if selected_cases:
            df_complete = df_complete[df_complete["case_name"].isin(selected_cases)]

        fig = go.Figure()

        if not df_complete.empty and emission_metrics:
            # Create bars for each emission metric
            colors = ["#00D9FF", "#FF6B6B", "#4ECDC4", "#FFE66D", "#A06CD5"]

            for i, metric in enumerate(emission_metrics):
                df_metric = df_complete.dropna(subset=[metric])
                if not df_metric.empty:
                    fig.add_trace(
                        go.Bar(
                            x=df_metric["case_name"],
                            y=df_metric[metric],
                            name=metric.replace("_", " ").title(),
                            marker_color=colors[i % len(colors)],
                            marker_line_color="#ffffff",
                            marker_line_width=1.5,
                            text=df_metric[metric].round(1),
                            textposition="outside",
                            textfont=dict(color="#ffffff"),
                        )
                    )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", title="Case Name", tickangle=-45),
            yaxis=dict(gridcolor="#444444", title="Emissions (ppm)"),
            barmode="group",
            hovermode="x unified",
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)", bordercolor="#444444", borderwidth=1
            ),
        )

        return fig

    # Graph 2: Temperature Performance (Dynamic)
    @app.callback(
        Output("temperature-plot", "figure"), [Input("case-selector", "value")]
    )
    def update_temperature_plot(selected_cases):
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]

        # Find temperature-related metrics
        temp_metrics = []
        for metric in SCHEMA["performance_metrics"]:
            if "temperature" in metric.lower() or "temp" in metric.lower():
                if metric in df_complete.columns:
                    temp_metrics.append(metric)

        if selected_cases:
            df_complete = df_complete[df_complete["case_name"].isin(selected_cases)]

        fig = go.Figure()

        if not df_complete.empty and temp_metrics:
            colors = {
                "max": "#FF6B6B",
                "avg": "#4ECDC4",
                "min": "#00D9FF",
                "std": "#FFE66D",
            }

            for metric in temp_metrics:
                df_metric = df_complete.dropna(subset=[metric])
                if not df_metric.empty:
                    # Determine color based on metric name
                    color = "#00D9FF"  # default
                    for key, col in colors.items():
                        if key in metric:
                            color = col
                            break

                    fig.add_trace(
                        go.Scatter(
                            x=df_metric["case_name"],
                            y=df_metric[metric],
                            name=metric.replace("_", " ").title(),
                            mode="lines+markers",
                            line=dict(color=color, width=3),
                            marker=dict(
                                size=10,
                                color=color,
                                line=dict(width=2, color="#ffffff"),
                            ),
                        )
                    )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", title="Case Name", tickangle=-45),
            yaxis=dict(gridcolor="#444444", title="Temperature (K)"),
            hovermode="x unified",
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)", bordercolor="#444444", borderwidth=1
            ),
        )

        return fig

    # Graph 3: Design Parameters Correlation (Dynamic)
    @app.callback(
        Output("correlation-plot", "figure"),
        [
            Input("case-selector", "value"),
            Input("param-x-selector", "value"),
            Input("param-y-selector", "value"),
        ],
    )
    def update_correlation_plot(selected_cases, param_x, param_y):
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]

        # Ensure both parameters exist in the dataframe
        if param_x not in df_complete.columns or param_y not in df_complete.columns:
            return go.Figure()

        df_complete = df_complete.dropna(subset=[param_x, param_y])

        if selected_cases:
            df_plot = df_complete[df_complete["case_name"].isin(selected_cases)]
        else:
            df_plot = df_complete

        fig = go.Figure()

        if not df_plot.empty:
            # Find a suitable color metric (prefer efficiency if available)
            color_metric = None
            if "combustion_efficiency" in df_plot.columns:
                color_metric = "combustion_efficiency"
            elif "mixing_quality" in df_plot.columns:
                color_metric = "mixing_quality"
            else:
                # Use the first available performance metric
                for metric in SCHEMA["performance_metrics"]:
                    if metric in df_plot.columns and metric != param_y:
                        color_metric = metric
                        break

            # Scatter plot
            marker_config = {
                "size": 15,
                "line": dict(width=2, color="#ffffff"),
            }

            if color_metric:
                marker_config["color"] = df_plot[color_metric]
                marker_config["colorscale"] = "Viridis"
                marker_config["showscale"] = True
                marker_config["colorbar"] = dict(
                    title=color_metric.replace("_", " ").title(),
                    bgcolor="rgba(0,0,0,0.5)",
                    bordercolor="#444444",
                    borderwidth=1,
                    tickfont=dict(color="#ffffff"),
                )
            else:
                marker_config["color"] = "#00D9FF"

            fig.add_trace(
                go.Scatter(
                    x=df_plot[param_x],
                    y=df_plot[param_y],
                    mode="markers+text",
                    marker=marker_config,
                    text=df_plot["case_name"],
                    textposition="top center",
                    textfont=dict(size=10, color="#ffffff"),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        + f"{param_x.replace('_', ' ').title()}: %{{x:.2f}}<br>"
                        + f"{param_y.replace('_', ' ').title()}: %{{y:.2f}}<br>"
                        + "<extra></extra>"
                    ),
                )
            )

            # Add trend line
            if len(df_plot) > 2:
                z = np.polyfit(df_plot[param_x], df_plot[param_y], 1)
                p = np.poly1d(z)
                x_trend = np.linspace(
                    df_plot[param_x].min(), df_plot[param_x].max(), 100
                )

                fig.add_trace(
                    go.Scatter(
                        x=x_trend,
                        y=p(x_trend),
                        mode="lines",
                        line=dict(color="#FF6B6B", width=2, dash="dash"),
                        name="Trend",
                        hoverinfo="skip",
                    )
                )

        # Get labels with units
        x_label = param_x.replace("_", " ").title()
        y_label = param_y.replace("_", " ").title()

        if param_x in SCHEMA["design_parameters"]:
            unit = SCHEMA["design_parameters"][param_x].get("unit", "")
            if unit and unit != "-":
                x_label += f" ({unit})"

        if param_y in SCHEMA["performance_metrics"]:
            unit = SCHEMA["performance_metrics"][param_y].get("unit", "")
            if unit and unit != "-":
                y_label += f" ({unit})"

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", title=x_label),
            yaxis=dict(gridcolor="#444444", title=y_label),
            showlegend=False,
            autosize = True
        )

        return fig

    # Graph 4: Performance Radar Chart (Dynamic)
    @app.callback(Output("radar-plot", "figure"), [Input("case-selector", "value")])
    def update_radar_plot(selected_cases):
        
        lower_is_better_metrics = [
            "nox_emissions",
            "co_emissions",
            "pattern_factor",
        ]
        
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]

        # Get radar metrics dynamically
        metrics, metric_labels = get_radar_metrics()

        # Filter out metrics that don't exist in the dataframe
        available_metrics = []
        available_labels = []
        for metric, label in zip(metrics, metric_labels):
            if metric in df_complete.columns:
                available_metrics.append(metric)
                available_labels.append(label)

        if not available_metrics:
            return go.Figure()

        if not selected_cases or len(selected_cases) == 0:
            # Show best performing cases if none selected
            if "nox_emissions" in df_complete.columns:
                df_nox = df_complete.dropna(subset=["nox_emissions"])
                if not df_nox.empty:
                    best_cases = df_nox.nsmallest(3, "nox_emissions")[
                        "case_name"
                    ].tolist()
                    df_plot = df_complete[df_complete["case_name"].isin(best_cases)]
                else:
                    df_plot = df_complete.head(3)
            else:
                df_plot = df_complete.head(3)
        else:
            df_plot = df_complete[
                df_complete["case_name"].isin(selected_cases)
            ]  # Limit to 5 add [:5]

        fig = go.Figure()

        if not df_plot.empty:
            colors = ["#00D9FF", "#FF6B6B", "#4ECDC4", "#FFE66D", "#A06CD5"]

            for idx, (_, row) in enumerate(df_plot.iterrows()):
                values = []
                for metric in available_metrics:
                    if pd.notna(row.get(metric, None)):
                        # Check if metric values exist in the complete dataset for normalization
                        metric_values = df_complete[metric].dropna()
                        if (
                            len(metric_values) > 0
                            and metric_values.max() != metric_values.min()
                        ):
                            if metric in lower_is_better_metrics:
                                # Lower is better - invert normalization
                                normalized = 1 - (row[metric] - metric_values.min()) / (
                                    metric_values.max() - metric_values.min()
                                )
                            else:
                                # Higher is better
                                normalized = (row[metric] - metric_values.min()) / (
                                    metric_values.max() - metric_values.min()
                                )
                        else:
                            normalized = 0.5  # Default if no variation
                    else:
                        normalized = 0
                    values.append(normalized)

                if values:  # Only plot if we have data
                    fig.add_trace(
                        go.Scatterpolar(
                            r=values + [values[0]],  # Close the polygon
                            theta=available_labels + [available_labels[0]],
                            fill="toself",
                            fillcolor=f"rgba({int(colors[idx % len(colors)][1:3], 16)}, "
                            f"{int(colors[idx % len(colors)][3:5], 16)}, "
                            f"{int(colors[idx % len(colors)][5:7], 16)}, 0.2)",
                            line=dict(color=colors[idx % len(colors)], width=2),
                            name=row["case_name"],
                            hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
                        )
                    )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    gridcolor="#444444",
                    tickfont=dict(color="#ffffff"),
                ),
                angularaxis=dict(gridcolor="#444444", tickfont=dict(color="#ffffff")),
                bgcolor="rgba(0,0,0,0)",
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)", bordercolor="#444444", borderwidth=1
            ),
            autosize=True,
        )

        return fig

    # Graph 5: Time Series Evolution (Dynamic)
    @app.callback(Output("timeline-plot", "figure"), [Input("case-selector", "value")])
    def update_timeline_plot(selected_cases):
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]
        df_complete = df_complete.sort_values("timestamp")

        fig = go.Figure()

        # Select up to 3 key metrics to plot
        priority_metrics = []

        # Priority order for metrics
        metric_priorities = [
            ("nox_emissions", "NOx Emissions", "#00D9FF", 1.0),
            ("combustion_efficiency", "Efficiency", "#4ECDC4", 1.0),
            ("pattern_factor", "Pattern Factor", "#FF6B6B", 100.0),  # Scale factor
            ("co_emissions", "CO Emissions", "#FFE66D", 1.0),
            ("temperature_max", "Max Temperature", "#A06CD5", 0.1),  # Scale down
        ]

        for metric_name, display_name, color, scale in metric_priorities:
            if metric_name in df_complete.columns and len(priority_metrics) < 3:
                df_metric = df_complete.dropna(subset=[metric_name])
                if not df_metric.empty:
                    priority_metrics.append((metric_name, display_name, color, scale))

        for metric_name, display_name, color, scale in priority_metrics:
            df_metric = df_complete.dropna(subset=[metric_name])
            if not df_metric.empty:
                y_values = df_metric[metric_name].values * scale

                # Add unit to display name
                if metric_name in SCHEMA["performance_metrics"]:
                    unit = SCHEMA["performance_metrics"][metric_name].get("unit", "")
                    if unit and unit != "-":
                        display_name += f" ({unit})"
                    if scale != 1.0:
                        display_name += f" ×{scale}"

                fig.add_trace(
                    go.Scatter(
                        x=df_metric["timestamp"],
                        y=y_values,
                        name=display_name,
                        mode="lines+markers",
                        line=dict(color=color, width=3),
                        marker=dict(
                            size=8, color=color, line=dict(width=2, color="#ffffff")
                        ),
                        connectgaps=False,
                    )
                )

                # Highlight selected cases
                if selected_cases:
                    selected_df = df_metric[df_metric["case_name"].isin(selected_cases)]
                    if not selected_df.empty:
                        y_selected = selected_df[metric_name].values * scale

                        fig.add_trace(
                            go.Scatter(
                                x=selected_df["timestamp"],
                                y=y_selected,
                                mode="markers",
                                marker=dict(
                                    size=15,
                                    color=color,
                                    symbol="star",
                                    line=dict(width=2, color="#ffffff"),
                                ),
                                showlegend=False,
                                hoverinfo="skip",
                            )
                        )

        # Add annotations for selected cases
        if selected_cases and priority_metrics:
            selected_df = df_complete[df_complete["case_name"].isin(selected_cases)]
            first_metric = priority_metrics[0][0]
            scale = priority_metrics[0][3]

            for _, row in selected_df.iterrows():
                if pd.notna(row.get(first_metric)):
                    fig.add_annotation(
                        x=row["timestamp"],
                        y=row[first_metric] * scale,
                        text=row["case_name"],
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#ffffff",
                        font=dict(color="#ffffff", size=10),
                        bgcolor="rgba(0,0,0,0.7)",
                        bordercolor="#00D9FF",
                    )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", title="Date", tickformat="%Y-%m-%d"),
            yaxis=dict(gridcolor="#444444", title="Metric Value (Scaled)"),
            hovermode="x unified",
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)", bordercolor="#444444", borderwidth=1
            ),
        )

        return fig

    # Graph 6: 3D Parameter Space (Dynamic)
    @app.callback(
        Output("parameter-3d-plot", "figure"),
        [
            Input("case-selector", "value"),
            Input("3d-x-selector", "value"),
            Input("3d-y-selector", "value"),
            Input("3d-z-selector", "value"),
        ],
    )
    def update_3d_plot(selected_cases, x_param, y_param, z_param):
        df = db.get_all_cases()
        df_complete = df[df["status"] == "completed"]

        # Ensure all parameters exist
        required_cols = [x_param, y_param, z_param]
        for col in required_cols:
            if col not in df_complete.columns:
                return go.Figure()

        df_complete = df_complete.dropna(subset=required_cols)

        if selected_cases and not len(selected_cases) == 0:
            df_complete = df_complete[df_complete["case_name"].isin(selected_cases)]

        fig = go.Figure()

        if not df_complete.empty:
            # Find a suitable color metric
            color_metric = None
            if "nox_emissions" in df_complete.columns:
                color_metric = "nox_emissions"
                color_title = "NOx (ppm)"
            elif "combustion_efficiency" in df_complete.columns:
                color_metric = "combustion_efficiency"
                color_title = "Efficiency (%)"
            else:
                # Use first available performance metric
                for metric in SCHEMA["performance_metrics"]:
                    if metric in df_complete.columns:
                        color_metric = metric
                        color_title = metric.replace("_", " ").title()
                        unit = SCHEMA["performance_metrics"][metric].get("unit", "")
                        if unit and unit != "-":
                            color_title += f" ({unit})"
                        break

            marker_config = {
                "size": 7,
                "line": dict(width=1, color="#ffffff"),
            }

            if color_metric:
                df_color = df_complete.dropna(subset=[color_metric])
                if not df_color.empty:
                    marker_config["color"] = df_color[color_metric]
                    marker_config["colorscale"] = "Turbo"
                    marker_config["showscale"] = True
                    marker_config["colorbar"] = dict(
                        title=color_title,
                        bgcolor="rgba(0,0,0,0.5)",
                        bordercolor="#444444",
                        borderwidth=1,
                        tickfont=dict(color="#ffffff"),
                    )
                    df_complete = df_color
                else:
                    marker_config["color"] = "#00D9FF"
            else:
                marker_config["color"] = "#00D9FF"

            # Create 3D scatter plot
            fig.add_trace(
                go.Scatter3d(
                    x=df_complete[x_param],
                    y=df_complete[y_param],
                    z=df_complete[z_param],
                    mode="markers+text",
                    marker=marker_config,
                    text=df_complete["case_name"],
                    textposition="top center",
                    textfont=dict(size=10, color="#ffffff"),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        + f"{x_param.replace('_', ' ').title()}: %{{x:.2f}}<br>"
                        + f"{y_param.replace('_', ' ').title()}: %{{y:.2f}}<br>"
                        + f"{z_param.replace('_', ' ').title()}: %{{z:.2f}}<br>"
                        + "<extra></extra>"
                    ),
                )
            )

        # Get axis labels with units
        def get_axis_label(param):
            label = param.replace("_", " ").title()
            if param in SCHEMA["design_parameters"]:
                unit = SCHEMA["design_parameters"][param].get("unit", "")
                if unit and unit != "-":
                    label += f" ({unit})"
            return label

        fig.update_layout(
            scene=dict(
                xaxis=dict(
                    title=get_axis_label(x_param),
                    backgroundcolor="rgba(0,0,0,0)",
                    gridcolor="#444444",
                    showbackground=True,
                    zerolinecolor="#444444",
                ),
                yaxis=dict(
                    title=get_axis_label(y_param),
                    backgroundcolor="rgba(0,0,0,0)",
                    gridcolor="#444444",
                    showbackground=True,
                    zerolinecolor="#444444",
                ),
                zaxis=dict(
                    title=get_axis_label(z_param),
                    backgroundcolor="rgba(0,0,0,0)",
                    gridcolor="#444444",
                    showbackground=True,
                    zerolinecolor="#444444",
                ),
                camera=dict(eye=dict(x=2.0, y=2.0, z=2.0)),
                bgcolor="rgba(0,0,0,0)",
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            margin=dict(l=0, r=0, t=0, b=0),
            autosize=True
        )

        return fig

    # Data table (Dynamic)
    @app.callback(
        Output("data-table-container", "children"), [Input("case-selector", "value")]
    )
    def update_data_table(selected_cases):
        df = db.get_all_cases()

        if selected_cases:
            df = df[df["case_name"].isin(selected_cases)]

        if df.empty:
            return dbc.Alert("No data to display", color="secondary")

        # Select key columns for display dynamically
        display_cols = ["case_name", "timestamp", "status"]

        # Add key design parameters (first 3-4)
        design_params = list(SCHEMA["design_parameters"].keys())[:4]
        for param in design_params:
            if param in df.columns:
                display_cols.append(param)

        # Add key performance metrics (first 3-4)
        perf_metrics = list(SCHEMA["performance_metrics"].keys())[:4]
        for metric in perf_metrics:
            if metric in df.columns:
                display_cols.append(metric)

        # Only include columns that exist in the dataframe
        display_cols = [col for col in display_cols if col in df.columns]

        df_display = df[display_cols].round(2)

        # Create table
        table = dbc.Table.from_dataframe(
            df_display,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-dark",
        )

        return table
