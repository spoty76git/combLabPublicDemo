import base64
import io
import json
import os
import pickle
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback_context, dcc, html

# Data processing
from scipy.interpolate import griddata

# CONSTANTS

DEFAULT_CSV_PATH = "default_data.csv"

FILTERED_DATA_DIR = "filtered"

number_of_slices_per_plane = 15


# Ensure filtered directory exists

Path(FILTERED_DATA_DIR).mkdir(exist_ok=True)


class DataStore:
    def __init__(self, default_csv_path):
        self.default_csv_path = default_csv_path

        self.df = None

        self.metadata = {}

        self.alreadyProcessed = True  # Flag to check if data is already processed

        self.number_of_slices_per_plane = number_of_slices_per_plane # Number of slices per plane

        # Processing tolerance

        self.sliceInterptTol = 0.01

        self.lineInterptTol = 0.05

        self.GRID_SIZE = 400

        self.load_default_data()

    def load_default_data(self):
        """Load default CSV file if it exists during initialization"""

        if os.path.exists(self.default_csv_path):
            try:
                self.df = pd.read_csv(self.default_csv_path)

                print(f"Default CSV loaded: {self.default_csv_path}")

                self.preprocess_data()

            except Exception as e:
                print(f"Error loading default CSV: {e}")

                self.df = None

    def set_dataframe(self, df):
        """Set a new DataFrame and trigger preprocessing"""

        self.df = df
        self.alreadyProcessed = False   # Reset processed flag
        self.preprocess_data()

    def get_dataframe(self):
        """Return the stored DataFrame"""

        return self.df

    def get_metadata(self):
        """Return metadata about the data"""

        return self.metadata

    def preprocess_data(self):
        """Preprocess data and save interpolated slices"""

        if self.df is None:
            return

        if self.alreadyProcessed:
            return

        print("Starting data preprocessing...")

        # Store metadata

        self.metadata = {
            "x_range": [self.df["x"].min(), self.df["x"].max()],
            "y_range": [self.df["y"].min(), self.df["y"].max()],
            "z_range": [self.df["z"].min(), self.df["z"].max()],
            "variables": [col for col in self.df.columns if col not in ["x", "y", "z"]],
            "num_points": len(self.df),
        }

        # Save metadata

        with open(os.path.join(FILTERED_DATA_DIR, "metadata.json"), "w") as f:
            json.dump(self.metadata, f)

        # Get numeric variables

        variables = self.metadata["variables"]

        # Process each plane type

        planes = ["XY", "YZ", "XZ"]

        num_slices = self.number_of_slices_per_plane # Number of slices per plane

        for plane in planes:
            print(f"Processing {plane} plane...")

            if plane == "XY":
                z_min, z_max = self.metadata["z_range"]

                slice_positions = np.linspace(z_min, z_max, num_slices)

                for i, z_val in enumerate(slice_positions):
                    slice_data = self._process_xy_slice(z_val, variables)

                    if slice_data is not None:
                        filename = os.path.join(
                            FILTERED_DATA_DIR, f"{plane}_slice_{i}.pkl"
                        )

                        # Use pickle directly instead of DataFrame

                        with open(filename, "wb") as f:
                            pickle.dump(slice_data, f)

            elif plane == "YZ":
                x_min, x_max = self.metadata["x_range"]

                slice_positions = np.linspace(x_min, x_max, num_slices)

                for i, x_val in enumerate(slice_positions):
                    slice_data = self._process_yz_slice(x_val, variables)

                    if slice_data is not None:
                        filename = os.path.join(
                            FILTERED_DATA_DIR, f"{plane}_slice_{i}.pkl"
                        )

                        # Use pickle directly instead of DataFrame

                        with open(filename, "wb") as f:
                            pickle.dump(slice_data, f)

            else:  # XZ
                y_min, y_max = self.metadata["y_range"]

                slice_positions = np.linspace(y_min, y_max, num_slices)

                for i, y_val in enumerate(slice_positions):
                    slice_data = self._process_xz_slice(y_val, variables)

                    if slice_data is not None:
                        filename = os.path.join(
                            FILTERED_DATA_DIR, f"{plane}_slice_{i}.pkl"
                        )

                        # Use pickle directly instead of DataFrame

                        with open(filename, "wb") as f:
                            pickle.dump(slice_data, f)

        # Process line data for each axis

        self._process_line_data_direct(variables)

        self.alreadyProcessed = True  # Set processed flag

        print("Data preprocessing complete!")

    def _process_xy_slice(self, z_val, variables):
        """Process and interpolate XY slice at given Z value"""

        tolerance = (
            self.metadata["z_range"][1] - self.metadata["z_range"][0]
        ) * self.sliceInterptTol

        slice_df = self.df[np.abs(self.df["z"] - z_val) < tolerance]

        if len(slice_df) < 10:
            return None

        # Create grid

        x_min, x_max = self.metadata["x_range"]

        y_min, y_max = self.metadata["y_range"]

        xi = np.linspace(x_min, x_max, self.GRID_SIZE)

        yi = np.linspace(y_min, y_max, self.GRID_SIZE)

        Xi, Yi = np.meshgrid(xi, yi)

        # Interpolate each variable

        result_data = {
            "xi": xi,
            "yi": yi,
            "z_val": z_val,
            "plane": "XY",
            "grid_shape": (self.GRID_SIZE, self.GRID_SIZE),
        }

        points = slice_df[["x", "y"]].values

        for var in variables:
            values = slice_df[var].values

            Zi = griddata(points, values, (Xi, Yi), method="linear", fill_value=np.nan)

            # Flatten the 2D array for storage

            result_data[f"{var}_grid"] = Zi.flatten()

        return result_data

    def _process_yz_slice(self, x_val, variables):
        """Process and interpolate YZ slice at given X value"""

        tolerance = (
            self.metadata["x_range"][1] - self.metadata["x_range"][0]
        ) * self.sliceInterptTol

        slice_df = self.df[np.abs(self.df["x"] - x_val) < tolerance]

        if len(slice_df) < 10:
            return None

        # Create grid

        y_min, y_max = self.metadata["y_range"]

        z_min, z_max = self.metadata["z_range"]

        yi = np.linspace(y_min, y_max, self.GRID_SIZE)

        zi = np.linspace(z_min, z_max, self.GRID_SIZE)

        Yi, Zi = np.meshgrid(yi, zi)

        # Interpolate each variable

        result_data = {
            "yi": yi,
            "zi": zi,
            "x_val": x_val,
            "plane": "YZ",
            "grid_shape": (self.GRID_SIZE, self.GRID_SIZE),
        }

        points = slice_df[["y", "z"]].values

        for var in variables:
            values = slice_df[var].values

            Zi_interp = griddata(
                points, values, (Yi, Zi), method="linear", fill_value=np.nan
            )

            # Flatten the 2D array for storage

            result_data[f"{var}_grid"] = Zi_interp.flatten()

        return result_data

    def _process_xz_slice(self, y_val, variables):
        """Process and interpolate XZ slice at given Y value"""

        tolerance = (
            self.metadata["y_range"][1] - self.metadata["y_range"][0]
        ) * self.sliceInterptTol

        slice_df = self.df[np.abs(self.df["y"] - y_val) < tolerance]

        if len(slice_df) < 10:
            return None

        # Create grid

        x_min, x_max = self.metadata["x_range"]

        z_min, z_max = self.metadata["z_range"]

        xi = np.linspace(x_min, x_max, self.GRID_SIZE)

        zi = np.linspace(z_min, z_max, self.GRID_SIZE)

        Xi, Zi = np.meshgrid(xi, zi)

        # Interpolate each variable

        result_data = {
            "xi": xi,
            "zi": zi,
            "y_val": y_val,
            "plane": "XZ",
            "grid_shape": (self.GRID_SIZE, self.GRID_SIZE),
        }

        points = slice_df[["x", "z"]].values

        for var in variables:
            values = slice_df[var].values

            Zi_interp = griddata(
                points, values, (Xi, Zi), method="linear", fill_value=np.nan
            )

            # Flatten the 2D array for storage

            result_data[f"{var}_grid"] = Zi_interp.flatten()

        return result_data

    def _process_line_data(self, variables):
        """Process and interpolate line data along each axis"""

        print("Processing line data...")

        # --- X-axis line (through center of Y and Z) ---

        y_mid = (self.metadata["y_range"][0] + self.metadata["y_range"][1]) / 2

        z_mid = (self.metadata["z_range"][0] + self.metadata["z_range"][1]) / 2

        # Create a plane perpendicular to X axis for interpolation

        x_positions = np.linspace(
            self.metadata["x_range"][0], self.metadata["x_range"][1], self.GRID_SIZE
        )

        line_data_x = {"position": x_positions, "axis": "X"}

        # Get nearby points for interpolation

        y_tol = (
            self.metadata["y_range"][1] - self.metadata["y_range"][0]
        ) * self.lineInterptTol

        z_tol = (
            self.metadata["z_range"][1] - self.metadata["z_range"][0]
        ) * self.lineInterptTol

        nearby_df = self.df[
            (np.abs(self.df["y"] - y_mid) < y_tol)
            & (np.abs(self.df["z"] - z_mid) < z_tol)
        ]

        if len(nearby_df) > 3:
            for var in variables:
                # Interpolate along X axis

                interp_values = griddata(
                    nearby_df[["x", "y", "z"]].values,
                    nearby_df[var].values,
                    np.column_stack(
                        [
                            x_positions,
                            np.full_like(x_positions, y_mid),
                            np.full_like(x_positions, z_mid),
                        ]
                    ),
                    method="linear",
                )

                line_data_x[var] = interp_values

        pd.DataFrame(line_data_x).to_pickle(
            os.path.join(FILTERED_DATA_DIR, "line_X.pkl")
        )

        # --- Y-axis line (through center of X and Z) ---

        x_mid = (self.metadata["x_range"][0] + self.metadata["x_range"][1]) / 2

        z_mid = (self.metadata["z_range"][0] + self.metadata["z_range"][1]) / 2

        y_positions = np.linspace(
            self.metadata["y_range"][0], self.metadata["y_range"][1], self.GRID_SIZE
        )

        line_data_y = {"position": y_positions, "axis": "Y"}

        x_tol = (
            self.metadata["x_range"][1] - self.metadata["x_range"][0]
        ) * self.lineInterptTol

        z_tol = (
            self.metadata["z_range"][1] - self.metadata["z_range"][0]
        ) * self.lineInterptTol

        nearby_df = self.df[
            (np.abs(self.df["x"] - x_mid) < x_tol)
            & (np.abs(self.df["z"] - z_mid) < z_tol)
        ]

        if len(nearby_df) > 3:
            for var in variables:
                interp_values = griddata(
                    nearby_df[["x", "y", "z"]].values,
                    nearby_df[var].values,
                    np.column_stack(
                        [
                            np.full_like(y_positions, x_mid),
                            y_positions,
                            np.full_like(y_positions, z_mid),
                        ]
                    ),
                    method="linear",
                )

                line_data_y[var] = interp_values

        pd.DataFrame(line_data_y).to_pickle(
            os.path.join(FILTERED_DATA_DIR, "line_Y.pkl")
        )

        # --- Z-axis line (through center of X and Y) ---

        x_mid = (self.metadata["x_range"][0] + self.metadata["x_range"][1]) / 2

        y_mid = (self.metadata["y_range"][0] + self.metadata["y_range"][1]) / 2

        z_positions = np.linspace(
            self.metadata["z_range"][0], self.metadata["z_range"][1], self.GRID_SIZE
        )

        line_data_z = {"position": z_positions, "axis": "Z"}

        x_tol = (
            self.metadata["x_range"][1] - self.metadata["x_range"][0]
        ) * self.lineInterptTol

        y_tol = (
            self.metadata["y_range"][1] - self.metadata["y_range"][0]
        ) * self.lineInterptTol

        nearby_df = self.df[
            (np.abs(self.df["x"] - x_mid) < x_tol)
            & (np.abs(self.df["y"] - y_mid) < y_tol)
        ]

        if len(nearby_df) > 3:
            for var in variables:
                interp_values = griddata(
                    nearby_df[["x", "y", "z"]].values,
                    nearby_df[var].values,
                    np.column_stack(
                        [
                            np.full_like(z_positions, x_mid),
                            np.full_like(z_positions, y_mid),
                            z_positions,
                        ]
                    ),
                    method="linear",
                )

                line_data_z[var] = interp_values

        pd.DataFrame(line_data_z).to_pickle(
            os.path.join(FILTERED_DATA_DIR, "line_Z.pkl")
        )

    def _process_line_data_direct(self, variables):
        """Process line data by direct sampling along each axis"""

        print("Processing line data with direct sampling...")

        # For each axis, bin the data and take averages

        for axis in ["X", "Y", "Z"]:
            if axis == "X":
                positions = np.linspace(
                    self.metadata["x_range"][0],
                    self.metadata["x_range"][1],
                    self.GRID_SIZE,
                )

                coord_col = "x"

            elif axis == "Y":
                positions = np.linspace(
                    self.metadata["y_range"][0],
                    self.metadata["y_range"][1],
                    self.GRID_SIZE,
                )

                coord_col = "y"

            else:  # Z
                positions = np.linspace(
                    self.metadata["z_range"][0],
                    self.metadata["z_range"][1],
                    self.GRID_SIZE,
                )

                coord_col = "z"

            line_data = {"position": positions, "axis": axis}

            # Bin the data and compute averages in each bin

            bin_width = (positions[1] - positions[0]) * 1.1  # Slightly wider bins

            for var in variables:
                values = []

                for pos in positions:
                    # Find points within bin

                    mask = np.abs(self.df[coord_col] - pos) < bin_width

                    if np.any(mask):
                        values.append(self.df[mask][var].mean())

                    else:
                        values.append(np.nan)

                line_data[var] = np.array(values)

            # Save the line data

            with open(os.path.join(FILTERED_DATA_DIR, f"line_{axis}.pkl"), "wb") as f:
                pickle.dump(line_data, f)


# Initialize data store

dataStore = DataStore(DEFAULT_CSV_PATH)


# Define layout with DBC components

layout = dbc.Container(
    [
        # Header Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H1(
                                            "CFD Results Visualizer",
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
        # Main Content Area
        dbc.Row(
            [
                # Left Sidebar - Control Panel
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-sliders-h me-2"
                                                ),
                                                "Control Panel",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        # Spatial Filters Section
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            [
                                                                html.I(
                                                                    className="fas fa-cube me-2"
                                                                ),
                                                                "Spatial Filters",
                                                            ],
                                                            className="text-warning mb-3",
                                                        ),
                                                        dbc.Label(
                                                            "View Mode",
                                                            className="text-info",
                                                        ),
                                                        dbc.RadioItems(
                                                            id="slice-plane",
                                                            options=[
                                                                {
                                                                    "label": " XY Plane",
                                                                    "value": "XY",
                                                                },
                                                                {
                                                                    "label": " YZ Plane",
                                                                    "value": "YZ",
                                                                },
                                                                {
                                                                    "label": " XZ Plane",
                                                                    "value": "XZ",
                                                                },
                                                                {
                                                                    "label": " 3D View",
                                                                    "value": "3D",
                                                                },
                                                            ],
                                                            value="YZ",
                                                            className="mb-3",
                                                        ),
                                                        dbc.Fade(
                                                            [
                                                                dbc.Label(
                                                                    "Slice Position",
                                                                    className="text-info",
                                                                ),
                                                                dcc.Slider(
                                                                    id="slice-position",
                                                                    min=0,
                                                                    max=1,
                                                                    value=0.0,
                                                                    step=0.01,
                                                                    marks={
                                                                        0: "0",
                                                                        0.5: "0.5",
                                                                        1: "1",
                                                                    },
                                                                    tooltip={
                                                                        "placement": "bottom",
                                                                        "always_visible": True,
                                                                    },
                                                                    className="mb-3",
                                                                ),
                                                            ],
                                                            id="slice-position-container",
                                                            is_in=True,
                                                        ),
                                                        dbc.Label(
                                                            "Spatial Ranges",
                                                            className="text-info mt-2",
                                                        ),
                                                        dbc.Accordion(
                                                            [
                                                                dbc.AccordionItem(
                                                                    [
                                                                        dcc.RangeSlider(
                                                                            id="x-range",
                                                                            min=0,
                                                                            max=1,
                                                                            value=[
                                                                                0,
                                                                                1,
                                                                            ],
                                                                            step=0.01,
                                                                            marks={
                                                                                0: "0",
                                                                                0.5: "0.5",
                                                                                1: "1",
                                                                            },
                                                                            tooltip={
                                                                                "placement": "bottom",
                                                                                "always_visible": False,
                                                                            },
                                                                        ),
                                                                    ],
                                                                    title="X Range",
                                                                    item_id="x-range-item",
                                                                ),
                                                                dbc.AccordionItem(
                                                                    [
                                                                        dcc.RangeSlider(
                                                                            id="y-range",
                                                                            min=0,
                                                                            max=1,
                                                                            value=[
                                                                                0,
                                                                                1,
                                                                            ],
                                                                            step=0.01,
                                                                            marks={
                                                                                0: "0",
                                                                                0.5: "0.5",
                                                                                1: "1",
                                                                            },
                                                                            tooltip={
                                                                                "placement": "bottom",
                                                                                "always_visible": False,
                                                                            },
                                                                        ),
                                                                    ],
                                                                    title="Y Range",
                                                                    item_id="y-range-item",
                                                                ),
                                                                dbc.AccordionItem(
                                                                    [
                                                                        dcc.RangeSlider(
                                                                            id="z-range",
                                                                            min=0,
                                                                            max=1,
                                                                            value=[
                                                                                0,
                                                                                1,
                                                                            ],
                                                                            step=0.01,
                                                                            marks={
                                                                                0: "0",
                                                                                0.5: "0.5",
                                                                                1: "1",
                                                                            },
                                                                            tooltip={
                                                                                "placement": "bottom",
                                                                                "always_visible": False,
                                                                            },
                                                                        ),
                                                                    ],
                                                                    title="Z Range",
                                                                    item_id="z-range-item",
                                                                ),
                                                            ],
                                                            start_collapsed=True,
                                                            className="mb-3",
                                                        ),
                                                        # Processing status
                                                        dbc.Alert(
                                                            id="processing-status",
                                                            is_open=False,
                                                            duration=4000,
                                                            className="mt-3",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary mb-3",
                                        ),
                                        # Variable Filters Section
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            [
                                                                html.I(
                                                                    className="fas fa-filter me-2"
                                                                ),
                                                                "Variable Filters",
                                                            ],
                                                            className="text-warning mb-3",
                                                        ),
                                                        dbc.Label(
                                                            "Primary Variable",
                                                            className="text-info",
                                                        ),
                                                        dbc.Select(
                                                            id="primary-variable",
                                                            options=[],  # Will be populated dynamically
                                                            value=None,
                                                            className="mb-3",
                                                        ),
                                                        dbc.Label(
                                                            "Secondary Options",
                                                            className="text-info",
                                                        ),
                                                        dbc.Checklist(
                                                            id="secondary-variables",
                                                            options=[

                                                            ],
                                                            value=[],
                                                            className="mb-2",
                                                            switch=True,
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary mb-3",
                                        ),
                                        # # Info Card
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.P(
                                                            [
                                                                html.I(
                                                                    className="fas fa-info-circle me-2"
                                                                ),
                                                                "You may upload your own CSV file with columns in format: 'x', 'y', 'z', 'variable1', 'variable2', '...'",
                                                            ],
                                                            className="text-muted small mb-0",
                                                        )
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary mb-3",
                                        ),
                                        # Data Selection Section
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            [
                                                                html.I(
                                                                    className="fas fa-database me-2"
                                                                ),
                                                                "Data Selection",
                                                            ],
                                                            className="text-warning mb-3",
                                                        ),
                                                        dcc.Upload(
                                                            id="upload-data",
                                                            children=dbc.Card(
                                                                [
                                                                    dbc.CardBody(
                                                                        [
                                                                            html.I(
                                                                                className="fas fa-cloud-upload-alt fa-3x mb-2"
                                                                            ),
                                                                            html.Br(),
                                                                            html.Span(
                                                                                "Drop CSV file here or "
                                                                            ),
                                                                            dbc.Button(
                                                                                "Browse",
                                                                                color="primary",
                                                                                size="sm",
                                                                                className="ms-1",
                                                                            ),
                                                                        ],
                                                                        className="text-center",
                                                                    )
                                                                ],
                                                                className="border-dashed bg-dark",
                                                                style={
                                                                    "borderWidth": "2px"
                                                                },
                                                            ),
                                                            style={"cursor": "pointer"},
                                                            multiple=False,
                                                        ),
                                                        html.Div(
                                                            id="file-status",
                                                            className="mt-2",
                                                        ),
                                                        dbc.Label(
                                                            "Simulation Case",
                                                            className="mt-3 text-info",
                                                        ),
                                                        dbc.Select(
                                                            id="case-dropdown",
                                                            options=[
                                                                {
                                                                    "label": "Case 1: 100% Load",
                                                                    "value": "case1",
                                                                },
                                                                {
                                                                    "label": "Case 2: 80% Load",
                                                                    "value": "case2",
                                                                },
                                                                {
                                                                    "label": "Case 3: 60% Load",
                                                                    "value": "case3",
                                                                },
                                                            ],
                                                            value="case1",
                                                            className="mb-3",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary mb-3",
                                        ),
                                        # Graph Settings Section
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        html.H6(
                                                            [
                                                                html.I(
                                                                    className="fas fa-palette me-2"
                                                                ),
                                                                "Graph Settings",
                                                            ],
                                                            className="text-warning mb-3",
                                                        ),
                                                        dbc.Label(
                                                            "Color Scale",
                                                            className="text-info",
                                                        ),
                                                        dbc.Select(
                                                            id="color-scale",
                                                            options=[
                                                                {
                                                                    "label": "Viridis",
                                                                    "value": "Viridis",
                                                                },
                                                                {
                                                                    "label": "Plasma",
                                                                    "value": "Plasma",
                                                                },
                                                                {
                                                                    "label": "Jet",
                                                                    "value": "Jet",
                                                                },
                                                                {
                                                                    "label": "Hot",
                                                                    "value": "Hot",
                                                                },
                                                                {
                                                                    "label": "Blues",
                                                                    "value": "Blues",
                                                                },
                                                                {
                                                                    "label": "Turbo",
                                                                    "value": "Turbo",
                                                                },
                                                            ],
                                                            value="Jet",
                                                            className="mb-3",
                                                        ),
                                                        dbc.ButtonGroup(
                                                            [
                                                                dbc.Button(
                                                                    "Linear",
                                                                    id="linear-scale",
                                                                    color="info",
                                                                    size="sm",
                                                                    active=True,
                                                                ),
                                                                dbc.Button(
                                                                    "Log",
                                                                    id="log-scale",
                                                                    color="info",
                                                                    size="sm",
                                                                    active=False,
                                                                ),
                                                            ],
                                                            className="mb-3 w-100",
                                                        ),
                                                        dbc.Label(
                                                            "Contour Levels",
                                                            className="text-info",
                                                        ),
                                                        dbc.InputGroup(
                                                            [
                                                                dbc.Input(
                                                                    id="contour-levels",
                                                                    type="number",
                                                                    value=20,
                                                                    min=5,
                                                                    max=100,
                                                                    step=1,
                                                                ),
                                                                dbc.InputGroupText(
                                                                    "levels"
                                                                ),
                                                            ],
                                                            size="sm",
                                                        ),
                                                        # Hidden input to store scale type
                                                        html.Div(
                                                            id="scale-type",
                                                            style={"display": "none"},
                                                            children="linear",
                                                        ),
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary",
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-lg sticky-top",
                            style={"top": "10px"},
                        )
                    ],
                    width=3,
                ),
                # Main Visualization Area
                dbc.Col(
                    [
                        # Primary Plot
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-chart-area me-2"
                                                ),
                                                "Primary Visualization",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-primary",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="primary-plot",
                                                    style={"height": "600px"},
                                                    config={
                                                        "displayModeBar": True,
                                                        "displaylogo": False,
                                                        "modeBarButtonsToRemove": [
                                                            "pan2d",
                                                            "lasso2d",
                                                        ],
                                                        "toImageButtonOptions": {
                                                            "format": "png",
                                                            "filename": "cfd_visualization",
                                                            "height": 1080,
                                                            "width": 1920,
                                                            "scale": 2,
                                                        },
                                                    },
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        ),
                        # Secondary Plot
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.H5(
                                                            [
                                                                html.I(
                                                                    className="fas fa-chart-line me-2"
                                                                ),
                                                                "Line Plot Analysis",
                                                            ],
                                                            className="mb-0 text-info",
                                                        )
                                                    ],
                                                    width=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Select(
                                                            id="line-axis",
                                                            options=[
                                                                {
                                                                    "label": "Along X-axis",
                                                                    "value": "X",
                                                                },
                                                                {
                                                                    "label": "Along Y-axis",
                                                                    "value": "Y",
                                                                },
                                                                {
                                                                    "label": "Along Z-axis",
                                                                    "value": "Z",
                                                                },
                                                            ],
                                                            value="X",
                                                            style={"minWidth": "150px"},
                                                        )
                                                    ],
                                                    width=6,
                                                    className="text-end",
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            id="loading-secondary",
                                            type="circle",
                                            color="#00D9FF",
                                            children=[
                                                dcc.Graph(
                                                    id="secondary-plot",
                                                    style={"height": "300px"},
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg",
                        ),
                    ],
                    width=6,
                ),
                # Right Panel - Stats and Annotations
                dbc.Col(
                    [
                        # Stats Panel
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-chart-pie me-2"
                                                ),
                                                "Overall Statistics",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            id="stats-display",
                                            children=[
                                                dbc.Alert(
                                                    "No data loaded",
                                                    color="secondary",
                                                    className="text-center",
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg mb-4",
                        ),
                        # Annotations Panel
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.H5(
                                            [
                                                html.I(
                                                    className="fas fa-sticky-note me-2"
                                                ),
                                                "Annotations",
                                            ],
                                            className="mb-0 text-info",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Card(
                                            [
                                                dbc.CardBody(
                                                    [
                                                        dbc.Checklist(
                                                            id="annotation-options",
                                                            options=[
                                                                {
                                                                    "label": " Show Annotations",
                                                                    "value": "show",
                                                                },
                                                            ],
                                                            value="show",
                                                            switch=True,
                                                        )
                                                    ]
                                                )
                                            ],
                                            className="bg-secondary",
                                        )
                                    ]
                                ),
                            ],
                            className="shadow-lg",
                        ),
                    ],
                    width=3,
                ),
            ]
        ),
        # Hidden div to store processing trigger
        html.Div(id="processing-trigger", style={"display": "none"}),
        # Hidden div to store metadata
        html.Div(id="metadata-store", style={"display": "none"}),
        # Add Font Awesome for icons
        html.Link(
            rel="stylesheet",
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        ),
    ],
    fluid=True,
    className="py-3",
)


# Register callbacks


def register_callbacks(app):
    # -- Data Upload and Processing --

    @app.callback(
        [
            Output("processing-trigger", "children"),
            Output("file-status", "children"),
            Output("processing-status", "children"),
            Output("processing-status", "is_open"),
            Output("processing-status", "color"),
        ],
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
    )
    def handle_file_upload(contents, filename):
        if contents is None:
            # Check if preprocessed data exists

            metadata_path = os.path.join(FILTERED_DATA_DIR, "metadata.json")

            if os.path.exists(metadata_path):
                return (
                    "default",
                    dbc.Alert(
                        "Using preprocessed default data",
                        color="info",
                        dismissable=True,
                    ),
                    "",
                    False,
                    "info",
                )

            else:
                return (
                    "default",
                    dbc.Alert(
                        "Using default data file", color="info", dismissable=True
                    ),
                    "",
                    False,
                    "info",
                )

        else:
            content_type, content_string = contents.split(",")

            decoded = base64.b64decode(content_string)

            try:
                if "csv" in filename:
                    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

                    # Validate required columns

                    required_cols = ["x", "y", "z"]

                    if not all(col in df.columns for col in required_cols):
                        return (
                            None,
                            dbc.Alert(
                                "CSV must contain x, y, z columns",
                                color="danger",
                                dismissable=True,
                            ),
                            "",
                            False,
                            "danger",
                        )

                    # Update data store and trigger preprocessing

                    dataStore.set_dataframe(df)

                    return (
                        "uploaded",
                        dbc.Alert(
                            f"Loaded: {filename}", color="success", dismissable=True
                        ),
                        "Data preprocessing complete!",
                        True,
                        "success",
                    )

            except Exception as e:
                print(e)

                return (
                    None,
                    dbc.Alert(
                        f"Error loading file: {str(e)}",
                        color="danger",
                        dismissable=True,
                    ),
                    "",
                    False,
                    "danger",
                )

    # -- Load metadata --

    @app.callback(
        Output("metadata-store", "children"), Input("processing-trigger", "children")
    )
    def load_metadata(trigger):
        metadata_path = os.path.join(FILTERED_DATA_DIR, "metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.dumps(json.load(f))

        return json.dumps({})

    # -- Update Variable Options --

    @app.callback(
        [Output("primary-variable", "options"), Output("primary-variable", "value")],
        Input("metadata-store", "children"),
    )
    def update_variable_options(metadata_json):
        if not metadata_json:
            return [], None

        metadata = json.loads(metadata_json)

        if "variables" not in metadata:
            return [], None

        variables = metadata["variables"]

        # Create options for dropdown

        options = [
            {"label": col.replace("_", " ").title(), "value": col} for col in variables
        ]

        # Return first match if found, otherwise first element

        desired_var = "temperature"

        matches = [s for s in variables if desired_var.lower() in s.lower()]

        if variables:
            default_value = matches[0] if matches else variables[0]

        else:
            default_value = None

        return options, default_value

    # -- Update Spatial Range Sliders --

    @app.callback(
        [
            Output("x-range", "min"),
            Output("x-range", "max"),
            Output("y-range", "min"),
            Output("y-range", "max"),
            Output("z-range", "min"),
            Output("z-range", "max"),
            Output("x-range", "marks"),
            Output("y-range", "marks"),
            Output("z-range", "marks"),
            Output("x-range", "value"),
            Output("y-range", "value"),
            Output("z-range", "value"),
        ],
        Input("metadata-store", "children"),
    )
    def update_range_sliders(metadata_json):
        if not metadata_json:
            return (
                0,
                1,
                0,
                1,
                0,
                1,
                {0: "0", 1: "1"},
                {0: "0", 1: "1"},
                {0: "0", 1: "1"},
                [0, 1],
                [0, 1],
                [0, 1],
            )

        metadata = json.loads(metadata_json)

        if not metadata or "x_range" not in metadata:
            return (
                0,
                1,
                0,
                1,
                0,
                1,
                {0: "0", 1: "1"},
                {0: "0", 1: "1"},
                {0: "0", 1: "1"},
                [0, 1],
                [0, 1],
                [0, 1],
            )

        x_min, x_max = metadata["x_range"]

        y_min, y_max = metadata["y_range"]

        z_min, z_max = metadata["z_range"]

        x_marks = {x_min: f"{x_min:.2f}", x_max: f"{x_max:.2f}"}

        y_marks = {y_min: f"{y_min:.2f}", y_max: f"{y_max:.2f}"}

        z_marks = {z_min: f"{z_min:.2f}", z_max: f"{z_max:.2f}"}

        return (
            x_min,
            x_max,
            y_min,
            y_max,
            z_min,
            z_max,
            x_marks,
            y_marks,
            z_marks,
            [x_min, x_max],
            [y_min, y_max],
            [z_min, z_max],
        )

    # -- Slice Type Toggle --

    @app.callback(
        Output("slice-position-container", "is_in"), Input("slice-plane", "value")
    )
    def toggle_slice_position(plane):
        return plane != "3D"

    # -- Primary plot --

    @app.callback(
        Output("primary-plot", "figure"),
        [
            Input("metadata-store", "children"),
            Input("primary-variable", "value"),
            Input("slice-plane", "value"),
            Input("slice-position", "value"),
            Input("x-range", "value"),
            Input("y-range", "value"),
            Input("z-range", "value"),
            Input("color-scale", "value"),
            Input("scale-type", "children"),
            Input("contour-levels", "value"),
            Input("secondary-variables", "value"),
            Input("annotation-options", "value"),
        ],
    )
    def update_primary_plot(
        metadata_json,
        primary_var,
        plane,
        slice_pos,
        x_range,
        y_range,
        z_range,
        color_scale,
        scale_type,
        contour_levels,
        secondary_vars,
        annotation_opts,
    ):
        # Create dark theme layout

        layout_theme = dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", zerolinecolor="#444444"),
            yaxis=dict(gridcolor="#444444", zerolinecolor="#444444"),
            margin=dict(l=0, r=0, t=40, b=0),
            hovermode="closest",
        )

        # Check if we have data

        if not metadata_json:
            fig = go.Figure()

            fig.add_annotation(
                text="Please upload a CSV file to visualize",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20, color="#888888"),
            )

            fig.update_layout(**layout_theme)

            return fig

        metadata = json.loads(metadata_json)

        if not metadata or "variables" not in metadata:
            fig = go.Figure()

            fig.add_annotation(
                text="No preprocessed data found. Please upload a CSV file.",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20, color="#888888"),
            )

            fig.update_layout(**layout_theme)

            return fig

        # Handle 3D view

        if plane == "3D":
            # For 3D view, we need to use the original data

            df = dataStore.get_dataframe()

            if df is None:
                fig = go.Figure()

                fig.add_annotation(
                    text="3D view requires original data",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=20, color="#888888"),
                )

                fig.update_layout(**layout_theme)

                return fig

            # Apply range filters

            df_filtered = df[
                (df["x"] >= x_range[0])
                & (df["x"] <= x_range[1])
                & (df["y"] >= y_range[0])
                & (df["y"] <= y_range[1])
                & (df["z"] >= z_range[0])
                & (df["z"] <= z_range[1])
            ]

            fig = go.Figure()

            # Create mesh3d trace

            fig.add_trace(
                go.Mesh3d(
                    x=df_filtered["x"],
                    y=df_filtered["y"],
                    z=df_filtered["z"],
                    intensity=df_filtered[primary_var]
                    if primary_var and primary_var in df_filtered.columns
                    else df_filtered[metadata["variables"][0]],
                    colorscale=color_scale,
                    colorbar=dict(
                        title=(primary_var or metadata["variables"][0])
                        .replace("_", " ")
                        .title(),
                        tickfont=dict(color="#ffffff"),
                        bgcolor="rgba(0,0,0,0.5)",
                        bordercolor="#444444",
                        borderwidth=1,
                    ),
                    opacity=0.8,
                    name=(primary_var or metadata["variables"][0])
                    .replace("_", " ")
                    .title(),
                )
            )

            fig.update_layout(
                scene=dict(
                    xaxis=dict(
                        title="X",
                        backgroundcolor="rgba(0,0,0,0)",
                        gridcolor="#444444",
                        showbackground=True,
                        zerolinecolor="#444444",
                        range=[x_range[0], x_range[1]],
                    ),
                    yaxis=dict(
                        title="Y",
                        backgroundcolor="rgba(0,0,0,0)",
                        gridcolor="#444444",
                        showbackground=True,
                        zerolinecolor="#444444",
                        range=[y_range[0], y_range[1]],
                    ),
                    zaxis=dict(
                        title="Z",
                        backgroundcolor="rgba(0,0,0,0)",
                        gridcolor="#444444",
                        showbackground=True,
                        zerolinecolor="#444444",
                        range=[z_range[0], z_range[1]],
                    ),
                    camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
                    bgcolor="rgba(0,0,0,0)",
                ),
                title=dict(
                    text=f"3D View - {(primary_var or metadata['variables'][0]).replace('_', ' ').title()}",
                    font=dict(size=18, color="#00D9FF"),
                ),
                **layout_theme,
            )

        else:
            # Load preprocessed slice data

            num_slices = number_of_slices_per_plane  # Number of slices per plane

            slice_index = int(slice_pos * (num_slices - 1))

            slice_file = os.path.join(
                FILTERED_DATA_DIR, f"{plane}_slice_{slice_index}.pkl"
            )

            if not os.path.exists(slice_file):
                fig = go.Figure()

                fig.add_annotation(
                    text="Slice data not found. Processing may still be in progress.",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=16, color="#888888"),
                )

                fig.update_layout(**layout_theme)

                return fig

            # Load the slice data

            with open(slice_file, "rb") as f:
                slice_data = pickle.load(f)

            # Use primary variable or first available

            if not primary_var or primary_var not in metadata["variables"]:
                primary_var = metadata["variables"][0]

            # Get grid coordinates and values

            if plane == "XY":
                xi = slice_data["xi"]

                yi = slice_data["yi"]

                z_val = slice_data["z_val"]

                title = f"XY Plane at Z={z_val:.2f}"

                x_label, y_label = "X", "Y"

            elif plane == "YZ":
                xi = slice_data["yi"]

                yi = slice_data["zi"]

                x_val = slice_data["x_val"]

                title = f"YZ Plane at X={x_val:.2f}"

                x_label, y_label = "Y", "Z"

            else:  # XZ
                xi = slice_data["xi"]

                yi = slice_data["zi"]

                y_val = slice_data["y_val"]

                title = f"XZ Plane at Y={y_val:.2f}"

                x_label, y_label = "X", "Z"

            # Get the interpolated values

            grid_key = f"{primary_var}_grid"

            if grid_key in slice_data:
                # Reshape the flattened grid data

                grid_shape = slice_data["grid_shape"]

                Zi = slice_data[grid_key].reshape(grid_shape)

                # Apply range filtering by creating masks

                if plane == "XY":
                    # For XY plane, filter by x and y ranges

                    x_mask = (xi >= x_range[0]) & (xi <= x_range[1])

                    y_mask = (yi >= y_range[0]) & (yi <= y_range[1])

                    # Apply masks

                    xi_filtered = xi[x_mask]

                    yi_filtered = yi[y_mask]

                    # Create meshgrid indices for filtering Zi

                    x_indices = np.where(x_mask)[0]

                    y_indices = np.where(y_mask)[0]

                    # Filter Zi using numpy indexing

                    Zi_filtered = Zi[np.ix_(y_indices, x_indices)]

                elif plane == "YZ":
                    # For YZ plane, filter by y and z ranges

                    y_mask = (xi >= y_range[0]) & (
                        xi <= y_range[1]
                    )  # xi is actually yi for YZ

                    z_mask = (yi >= z_range[0]) & (
                        yi <= z_range[1]
                    )  # yi is actually zi for YZ

                    xi_filtered = xi[y_mask]

                    yi_filtered = yi[z_mask]

                    y_indices = np.where(y_mask)[0]

                    z_indices = np.where(z_mask)[0]

                    Zi_filtered = Zi[np.ix_(z_indices, y_indices)]

                else:  # XZ
                    # For XZ plane, filter by x and z ranges

                    x_mask = (xi >= x_range[0]) & (xi <= x_range[1])

                    z_mask = (yi >= z_range[0]) & (
                        yi <= z_range[1]
                    )  # yi is actually zi for XZ

                    xi_filtered = xi[x_mask]

                    yi_filtered = yi[z_mask]

                    x_indices = np.where(x_mask)[0]

                    z_indices = np.where(z_mask)[0]

                    Zi_filtered = Zi[np.ix_(z_indices, x_indices)]

            else:
                fig = go.Figure()

                fig.add_annotation(
                    text=f"Variable '{primary_var}' not found in preprocessed data",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=16, color="#888888"),
                )

                fig.update_layout(**layout_theme)

                return fig

            # Create contour plot

            fig = go.Figure()

            fig.add_trace(
                go.Contour(
                    x=xi_filtered,
                    y=yi_filtered,
                    z=Zi_filtered,
                    colorscale=color_scale,
                    ncontours=contour_levels,
                    contours=dict(
                        coloring="heatmap",
                        showlabels=False,
                        labelfont=dict(size=10, color="white"),
                    ),
                    line=dict(
                        color="rgba(0, 0, 0, 0.2)",
                        width=1.5,
                        smoothing=1.0,
                    ),
                    colorbar=dict(
                        title=primary_var.replace("_", " ").title(),
                        tickfont=dict(color="#ffffff"),
                        bgcolor="rgba(0,0,0,0.5)",
                        bordercolor="#444444",
                        borderwidth=1,
                    ),
                    name=primary_var.replace("_", " ").title(),
                    hovertemplate=f"{x_label}: %{{x:.3f}}<br>{y_label}: %{{y:.3f}}<br>{primary_var}: %{{z:.3f}}<extra></extra>",
                )
            )

            fig.update_layout(
                xaxis_title=x_label,
                yaxis_title=y_label,
                title=dict(
                    text=f"{title} - {primary_var.replace('_', ' ').title()}",
                    font=dict(size=18, color="#00D9FF"),
                ),
                **layout_theme,
            )

            # Update axis ranges separately to avoid conflict

            fig.update_xaxes(
                range=[xi_filtered[0], xi_filtered[-1]]
                if len(xi_filtered) > 0
                else None
            )

            fig.update_yaxes(
                range=[yi_filtered[0], yi_filtered[-1]]
                if len(yi_filtered) > 0
                else None
            )

            # Add annotations if enabled

            if (
                annotation_opts
                and "show" in annotation_opts
                and len(xi_filtered) > 0
                and len(yi_filtered) > 0
            ):
                # Find maximum value location

                max_val = np.nanmax(Zi_filtered)

                max_loc = np.where(Zi_filtered == max_val)

                if len(max_loc[0]) > 0:
                    max_x = xi_filtered[max_loc[1][0]]

                    max_y = yi_filtered[max_loc[0][0]]

                    fig.add_annotation(
                        x=max_x,
                        y=max_y,
                        text=f"Max: {max_val:.2f}",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#00D9FF",
                        font=dict(color="#00D9FF", size=12),
                        bgcolor="rgba(0,0,0,0.7)",
                        bordercolor="#00D9FF",
                    )

                min_val = np.nanmin(Zi_filtered)

                min_loc = np.where(Zi_filtered == min_val)

                if len(min_loc[0]) > 0:
                    min_x = xi_filtered[min_loc[1][0]]

                    min_y = yi_filtered[min_loc[0][0]]

                    fig.add_annotation(
                        x=min_x,
                        y=min_y,
                        text=f"Min: {min_val:.2f}",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#00D9FF",
                        font=dict(color="#00D9FF", size=12),
                        bgcolor="rgba(0,0,0,0.7)",
                        bordercolor="#00D9FF",
                    )

        fig.update_layout(height=600)

        return fig

    # -- Secondary plot (Line plot) --

    @app.callback(
        Output("secondary-plot", "figure"),
        [
            Input("metadata-store", "children"),
            Input("primary-variable", "value"),
            Input("line-axis", "value"),
            Input("x-range", "value"),
            Input("y-range", "value"),
            Input("z-range", "value"),
        ],
    )
    def update_secondary_plot(
        metadata_json, primary_var, axis, x_range, y_range, z_range
    ):
        # Dark theme layout

        layout_theme = dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff"),
            xaxis=dict(gridcolor="#444444", zerolinecolor="#444444"),
            yaxis=dict(gridcolor="#444444", zerolinecolor="#444444"),
            margin=dict(l=0, r=0, t=40, b=0),
            hovermode="x unified",
        )

        # Check if we have data

        if not metadata_json:
            return go.Figure(layout=layout_theme)

        metadata = json.loads(metadata_json)

        if not metadata or "variables" not in metadata:
            return go.Figure(layout=layout_theme)

        # Load preprocessed line data

        line_file = os.path.join(FILTERED_DATA_DIR, f"line_{axis}.pkl")

        if not os.path.exists(line_file):
            fig = go.Figure()

            fig.add_annotation(
                text="Line data not found. Processing may still be in progress.",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#888888"),
            )

            fig.update_layout(**layout_theme)

            return fig

        # Load the line data

        line_data = pd.read_pickle(line_file)

        # Use primary variable or first available

        if not primary_var or primary_var not in metadata["variables"]:
            primary_var = metadata["variables"][0]

        fig = go.Figure()

        # Check if line_data is a dict (new format) or DataFrame (old format)

        if isinstance(line_data, dict):
            # New dict format

            available_vars = [
                key for key in line_data.keys() if key not in ["position", "axis"]
            ]

            has_position = "position" in line_data

            has_primary_var = primary_var in line_data

        else:
            # Old DataFrame format

            available_vars = [
                col for col in line_data.columns if col not in ["position", "axis"]
            ]

            has_position = "position" in line_data.columns

            has_primary_var = primary_var in line_data.columns

        if has_primary_var and has_position:
            # Get position and values based on data type

            if isinstance(line_data, dict):
                positions = line_data["position"]

                values = line_data[primary_var]

            else:
                positions = line_data["position"].values

                values = line_data[primary_var].values

            # Apply range filtering based on axis

            if axis == "X":
                # Filter by X range

                mask = (positions >= x_range[0]) & (positions <= x_range[1])

            elif axis == "Y":
                # Filter by Y range

                mask = (positions >= y_range[0]) & (positions <= y_range[1])

            else:  # Z
                # Filter by Z range

                mask = (positions >= z_range[0]) & (positions <= z_range[1])

            positions = positions[mask]

            values = values[mask]

            # Filter out NaN values

            valid_mask = ~np.isnan(values)

            positions = positions[valid_mask]

            values = values[valid_mask]

            if len(positions) > 0:
                # Determine axis labels based on metadata

                if axis == "X":
                    y_mid = (metadata["y_range"][0] + metadata["y_range"][1]) / 2

                    z_mid = (metadata["z_range"][0] + metadata["z_range"][1]) / 2

                    title = f"Along X-axis (Y≈{y_mid:.2f}, Z≈{z_mid:.2f})"

                elif axis == "Y":
                    x_mid = (metadata["x_range"][0] + metadata["x_range"][1]) / 2

                    z_mid = (metadata["z_range"][0] + metadata["z_range"][1]) / 2

                    title = f"Along Y-axis (X≈{x_mid:.2f}, Z≈{z_mid:.2f})"

                else:  # Z
                    x_mid = (metadata["x_range"][0] + metadata["x_range"][1]) / 2

                    y_mid = (metadata["y_range"][0] + metadata["y_range"][1]) / 2

                    title = f"Along Z-axis (X≈{x_mid:.2f}, Y≈{y_mid:.2f})"

                fig.add_trace(
                    go.Scatter(
                        x=positions,
                        y=values,
                        mode="lines+markers",
                        name=primary_var.replace("_", " ").title(),
                        line=dict(width=3, color="#00D9FF"),
                        marker=dict(
                            size=6, color="#00D9FF", line=dict(width=1, color="#ffffff")
                        ),
                    )
                )

                # Update without conflict

                fig.update_layout(**layout_theme)

                fig.update_layout(
                    xaxis_title=f"{axis} Position",
                    yaxis_title=primary_var.replace("_", " ").title(),
                    xaxis=dict(
                        range=[positions[0], positions[-1]]
                        if len(positions) > 1
                        else None
                    ),
                    title=dict(text=title, font=dict(size=16, color="#00D9FF")),
                )

            else:
                fig.add_annotation(
                    text="No valid data points along this axis",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=14, color="#888888"),
                )

                fig.update_layout(**layout_theme)

        else:
            fig.add_annotation(
                text=f"Variable '{primary_var}' not found in line data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#888888"),
            )

            fig.update_layout(**layout_theme)

        fig.update_layout(height=300)

        return fig

    # -- Scale Toggle Buttons --

    @app.callback(
        [
            Output("linear-scale", "active"),
            Output("log-scale", "active"),
            Output("scale-type", "children"),
        ],
        [Input("linear-scale", "n_clicks"), Input("log-scale", "n_clicks")],
        [State("linear-scale", "active"), State("log-scale", "active")],
    )
    def toggle_scale_buttons(linear_clicks, log_clicks, linear_active, log_active):
        ctx = callback_context

        if not ctx.triggered:
            return True, False, "linear"

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "linear-scale":
            return True, False, "linear"

        else:
            return False, True, "log"

    # -- Statistics Display --

    @app.callback(
        Output("stats-display", "children"),
        [
            Input("metadata-store", "children"),
            Input("primary-variable", "value"),
            Input("x-range", "value"),
            Input("y-range", "value"),
            Input("z-range", "value"),
        ],
    )
    def update_stats(metadata_json, primary_var, x_range, y_range, z_range):
        # Check if we have data

        if not metadata_json:
            return dbc.Alert(
                "No data loaded", color="secondary", className="text-center"
            )

        metadata = json.loads(metadata_json)

        if not metadata or "variables" not in metadata:
            return dbc.Alert(
                "No preprocessed data found", color="secondary", className="text-center"
            )

        # Use primary variable or first available

        if not primary_var or primary_var not in metadata["variables"]:
            primary_var = metadata["variables"][0] if metadata["variables"] else None

        if not primary_var:
            return dbc.Alert(
                "No valid data column found", color="warning", className="text-center"
            )

        # For stats, we need to calculate from the original data

        df = dataStore.get_dataframe()

        if df is None or primary_var not in df.columns:
            return dbc.Alert(
                "Statistics require original data",
                color="warning",
                className="text-center",
            )

        # Apply range filters

        df_filtered = df[
            (df["x"] >= x_range[0])
            & (df["x"] <= x_range[1])
            & (df["y"] >= y_range[0])
            & (df["y"] <= y_range[1])
            & (df["z"] >= z_range[0])
            & (df["z"] <= z_range[1])
        ]

        if len(df_filtered) == 0:
            return dbc.Alert(
                "No data points in selected range",
                color="warning",
                className="text-center",
            )

        # Calculate statistics on filtered data

        min_val = df_filtered[primary_var].min()

        max_val = df_filtered[primary_var].max()

        mean_val = df_filtered[primary_var].mean()

        std_val = df_filtered[primary_var].std()

        stats = [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                primary_var.replace("_", " ").title(),
                                                className="text-warning mb-1",
                                            ),
                                            html.H4(
                                                f"{mean_val:.3f}",
                                                className="text-white mb-0",
                                            ),
                                            html.Small(
                                                "Average", className="text-muted"
                                            ),
                                        ]
                                    )
                                ],
                                className="bg-secondary text-center",
                            )
                        ],
                        width=12,
                        className="mb-2",
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.Small("Min", className="text-muted"),
                                            html.H5(
                                                f"{min_val:.3f}",
                                                className="text-info mb-0",
                                            ),
                                        ],
                                        className="p-2",
                                    )
                                ],
                                className="bg-dark",
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.Small("Max", className="text-muted"),
                                            html.H5(
                                                f"{max_val:.3f}",
                                                className="text-danger mb-0",
                                            ),
                                        ],
                                        className="p-2",
                                    )
                                ],
                                className="bg-dark",
                            )
                        ],
                        width=6,
                    ),
                ],
                className="mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.Small(
                                                "Std Dev", className="text-muted"
                                            ),
                                            html.H5(
                                                f"{std_val:.3f}",
                                                className="text-warning mb-0",
                                            ),
                                        ],
                                        className="p-2",
                                    )
                                ],
                                className="bg-dark",
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.Small(
                                                "Points", className="text-muted"
                                            ),
                                            html.H5(
                                                f"{len(df_filtered):,}",
                                                className="text-success mb-0",
                                            ),
                                        ],
                                        className="p-2",
                                    )
                                ],
                                className="bg-dark",
                            )
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            html.Hr(className="my-3"),
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H6("Selected Region", className="text-info mb-2"),
                            dbc.ListGroup(
                                [
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong(
                                                "X: ", className="text-warning"
                                            ),
                                            f"[{x_range[0]:.2f}, {x_range[1]:.2f}]",
                                        ],
                                        className="bg-dark border-secondary py-1",
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong(
                                                "Y: ", className="text-warning"
                                            ),
                                            f"[{y_range[0]:.2f}, {y_range[1]:.2f}]",
                                        ],
                                        className="bg-dark border-secondary py-1",
                                    ),
                                    dbc.ListGroupItem(
                                        [
                                            html.Strong(
                                                "Z: ", className="text-warning"
                                            ),
                                            f"[{z_range[0]:.2f}, {z_range[1]:.2f}]",
                                        ],
                                        className="bg-dark border-secondary py-1",
                                    ),
                                ],
                                flush=True,
                            ),
                        ],
                        className="p-2",
                    )
                ],
                className="bg-secondary",
            ),
        ]

        return stats
