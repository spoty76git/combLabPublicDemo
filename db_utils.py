import sqlite3
import pandas as pd
from datetime import datetime
import json

# Database configuration
DB_PATH = "cfd_main_database.db"

# --- MAIN SCHEMA DEFINITION; FOLLOW _ FORMAT ---
SCHEMA = {
    "design_parameters": {
        "fuel_mass_flow_rate": {"type": "REAL", "default": 0.1, "unit": "kg/s"},
        "injection_speed_prim": {"type": "REAL", "default": 50, "unit": "m/s"},
        "injection_speed_stage": {"type": "REAL", "default": 50, "unit": "m/s"},
        "injector_width_stage": {"type": "REAL", "default": 0.1, "unit": "m"},
        "injector_primary_diam": {"type": "REAL", "default": 0.05, "unit": "m"},
        "equivalence_ratio": {"type": "REAL", "default": 0.7, "unit": "-"},
        "inlet_temperature": {"type": "REAL", "default": 600, "unit": "K"},
        "inlet_pressure": {"type": "REAL", "default": 10, "unit": "bar"},
        "combustor_length": {"type": "REAL", "default": 0.6, "unit": "-"},
    },
    "performance_metrics": {
        "nox_emissions": {"type": "REAL", "unit": "ppm"},
        "co_emissions": {"type": "REAL", "unit": "ppm"},
        "soot_formation": {"type": "REAL", "unit": "ppm"},
        "temperature_max": {"type": "REAL", "unit": "K"},
        "temperature_avg": {"type": "REAL", "unit": "K"},
        "temperature_std": {"type": "REAL", "unit": "K"},
        "pressure_drop": {"type": "REAL", "unit": "%"},
        "combustion_efficiency": {"type": "REAL", "unit": "%"},
        "mixing_time": {"type": "REAL", "unit": "ms"},
    },
}


class CFDDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.design_params = list(SCHEMA["design_parameters"].keys())
        self.performance_metrics = list(SCHEMA["performance_metrics"].keys())
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_name TEXT NOT NULL UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                status TEXT DEFAULT 'completed'
            )
        """)

        # Create design_parameters table dynamically
        design_cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "case_id INTEGER"]
        for col, config in SCHEMA["design_parameters"].items():
            design_cols.append(f"{col} {config['type']}")
        design_cols.append("FOREIGN KEY (case_id) REFERENCES run_cases (id)")

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS design_parameters (
                {", ".join(design_cols)}
            )
        """)

        # Create performance_metrics table dynamically
        perf_cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "case_id INTEGER"]
        for col, config in SCHEMA["performance_metrics"].items():
            perf_cols.append(f"{col} {config['type']}")
        perf_cols.append("FOREIGN KEY (case_id) REFERENCES run_cases (id)")

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                {", ".join(perf_cols)}
            )
        """)

        conn.commit()

        # # Insert sample data if tables are empty
        # cursor.execute("SELECT COUNT(*) FROM run_cases")
        # if cursor.fetchone()[0] == 0:
        #     self._insert_sample_data(conn)

        conn.close()

    # def _insert_sample_data(self, conn):
    #     """Insert sample data for demonstration"""
    #     cursor = conn.cursor()

    #     # Sample cases
    #     cases = [
    #         ("Baseline", "Initial design configuration", "completed"),
    #         ("Opt_InjPos_1", "Optimized injector position - iteration 1", "completed"),
    #         ("Opt_InjPos_2", "Optimized injector position - iteration 2", "completed"),
    #         ("Opt_Speed_1", "Increased injection speed", "completed"),
    #         ("Opt_Swirl_1", "Modified swirl number", "completed"),
    #         ("Opt_AFR_1", "Adjusted air-fuel ratio", "completed"),
    #         ("Combined_Opt_1", "Combined optimizations", "completed"),
    #         ("Latest_Design", "Latest design iteration", "running"),
    #     ]

    #     for case_name, desc, status in cases:
    #         cursor.execute(
    #             """
    #             INSERT INTO run_cases (case_name, description, status, timestamp)
    #             VALUES (?, ?, ?, ?)
    #         """,
    #             (
    #                 case_name,
    #                 desc,
    #                 status,
    #                 datetime.now() - timedelta(days=np.random.randint(0, 30)),
    #             ),
    #         )

    #     # Get case IDs
    #     cursor.execute("SELECT id, case_name FROM run_cases")
    #     case_ids = {name: id for id, name in cursor.fetchall()}

    #     # Sample design parameters
    #     design_params_data = {
    #         "Baseline": {
    #             "injector_x": 0.1,
    #             "injector_y": 0.05,
    #             "injector_z": 0.2,
    #             "injection_speed": 50,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 15,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.6,
    #         },
    #         "Opt_InjPos_1": {
    #             "injector_x": 0.12,
    #             "injector_y": 0.05,
    #             "injector_z": 0.2,
    #             "injection_speed": 50,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 15,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.6,
    #         },
    #         "Opt_InjPos_2": {
    #             "injector_x": 0.11,
    #             "injector_y": 0.06,
    #             "injector_z": 0.2,
    #             "injection_speed": 50,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 15,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.6,
    #         },
    #         "Opt_Speed_1": {
    #             "injector_x": 0.1,
    #             "injector_y": 0.05,
    #             "injector_z": 0.2,
    #             "injection_speed": 75,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 15,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.6,
    #         },
    #         "Opt_Swirl_1": {
    #             "injector_x": 0.1,
    #             "injector_y": 0.05,
    #             "injector_z": 0.2,
    #             "injection_speed": 50,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 15,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.8,
    #         },
    #         "Opt_AFR_1": {
    #             "injector_x": 0.1,
    #             "injector_y": 0.05,
    #             "injector_z": 0.2,
    #             "injection_speed": 50,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 18,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.6,
    #         },
    #         "Combined_Opt_1": {
    #             "injector_x": 0.11,
    #             "injector_y": 0.06,
    #             "injector_z": 0.2,
    #             "injection_speed": 65,
    #             "injection_angle": 0,
    #             "fuel_flow_rate": 0.1,
    #             "air_fuel_ratio": 17,
    #             "inlet_temperature": 600,
    #             "inlet_pressure": 15,
    #             "swirl_number": 0.7,
    #         },
    #         "Latest_Design": {
    #             "injector_x": 0.11,
    #             "injector_y": 0.06,
    #             "injector_z": 0.2,
    #             "injection_speed": 70,
    #             "injection_angle": 5,
    #             "fuel_flow_rate": 0.12,
    #             "air_fuel_ratio": 16.5,
    #             "inlet_temperature": 620,
    #             "inlet_pressure": 16,
    #             "swirl_number": 0.75,
    #         },
    #     }

    #     for case_name, params in design_params_data.items():
    #         cols = ["case_id"] + list(params.keys())
    #         vals = [case_ids[case_name]] + list(params.values())
    #         placeholders = ",".join(["?" for _ in vals])

    #         cursor.execute(
    #             f"""
    #             INSERT INTO design_parameters ({",".join(cols)})
    #             VALUES ({placeholders})
    #         """,
    #             vals,
    #         )

    #     # Sample performance metrics with correlation
    #     base_nox = 25
    #     base_co = 50
    #     base_temp = 1800

    #     for case_name, params in design_params_data.items():
    #         if case_name != "Latest_Design":  # Don't insert metrics for running case
    #             # Create realistic correlations
    #             speed_factor = params["injection_speed"] / 50
    #             afr_factor = params["air_fuel_ratio"] / 15
    #             swirl_factor = params["swirl_number"] / 0.6

    #             metrics = {
    #                 "nox_emissions": max(
    #                     5,
    #                     base_nox * (0.8 + 0.2 * speed_factor) * (0.7 + 0.3 * afr_factor)
    #                     + np.random.normal(0, 2),
    #                 ),
    #                 "co_emissions": max(
    #                     10,
    #                     base_co * (1.2 - 0.2 * speed_factor) * (1.3 - 0.3 * afr_factor)
    #                     + np.random.normal(0, 3),
    #                 ),
    #                 "temperature_max": base_temp
    #                 + 100 * speed_factor
    #                 - 50 * (afr_factor - 1)
    #                 + np.random.normal(0, 20),
    #                 "temperature_avg": (
    #                     base_temp + 100 * speed_factor - 50 * (afr_factor - 1)
    #                 )
    #                 * 0.85
    #                 + np.random.normal(0, 10),
    #                 "temperature_std": 150 * (1 - 0.2 * swirl_factor)
    #                 + np.random.normal(0, 10),
    #                 "pressure_drop": 2.5
    #                 + 0.5 * speed_factor
    #                 + np.random.normal(0, 0.1),
    #                 "combustion_efficiency": min(
    #                     99.5, 95 + 2 * afr_factor + np.random.normal(0, 0.5)
    #                 ),
    #                 "pattern_factor": max(
    #                     0.1, 0.25 - 0.05 * swirl_factor + np.random.normal(0, 0.02)
    #                 ),
    #                 "mixing_quality": min(
    #                     0.95, 0.8 + 0.1 * swirl_factor + np.random.normal(0, 0.02)
    #                 ),
    #                 "flame_length": max(
    #                     0.2, 0.5 - 0.1 * speed_factor + np.random.normal(0, 0.02)
    #                 ),
    #             }

    #             cols = ["case_id"] + list(metrics.keys())
    #             vals = [case_ids[case_name]] + list(metrics.values())
    #             placeholders = ",".join(["?" for _ in vals])

    #             cursor.execute(
    #                 f"""
    #                 INSERT INTO performance_metrics ({",".join(cols)})
    #                 VALUES ({placeholders})
    #             """,
    #                 vals,
    #             )

    #     conn.commit()

    def get_all_cases(self):
        """Fetch all cases with their parameters and metrics"""
        conn = self.get_connection()

        # Build column list dynamically
        design_cols = [f"dp.{col}" for col in self.design_params]
        perf_cols = [f"pm.{col}" for col in self.performance_metrics]

        query = f"""
            SELECT 
                rc.id, rc.case_name, rc.timestamp, rc.description, rc.status,
                {", ".join(design_cols)},
                {", ".join(perf_cols)}
            FROM run_cases rc
            LEFT JOIN design_parameters dp ON rc.id = dp.case_id
            LEFT JOIN performance_metrics pm ON rc.id = pm.case_id
            ORDER BY rc.timestamp DESC
        """

        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_case_names(self):
        """Get list of all case names"""
        conn = self.get_connection()
        query = "SELECT case_name, status FROM run_cases ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def insert_case(
        self, case_name, description, status, case_date, design_params, performance_metrics=None
    ):
        """Insert a new case with parameters and optionally metrics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Insert case
            cursor.execute(
                """
                INSERT INTO run_cases (case_name, timestamp, description, status)
                VALUES (?, ?, ?, ?)
            """,
                (case_name, case_date, description, status),
            )

            case_id = cursor.lastrowid

            # Insert design parameters
            cols = ["case_id"] + list(design_params.keys())
            vals = [case_id] + list(design_params.values())
            placeholders = ",".join(["?" for _ in vals])

            cursor.execute(
                f"""
                INSERT INTO design_parameters ({",".join(cols)})
                VALUES ({placeholders})
            """,
                vals,
            )

            # Insert performance metrics if provided and status is completed
            if performance_metrics and status == "completed":
                cols = ["case_id"] + list(performance_metrics.keys())
                vals = [case_id] + list(performance_metrics.values())
                placeholders = ",".join(["?" for _ in vals])

                cursor.execute(
                    f"""
                    INSERT INTO performance_metrics ({",".join(cols)})
                    VALUES ({placeholders})
                """,
                    vals,
                )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            conn.close()
            print(f"Error inserting case: {e}")
            return False

    def update_case_status(self, case_id, status):
        """Update case status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE run_cases 
            SET status = ? 
            WHERE id = ?
        """,
            (status, case_id),
        )

        conn.commit()
        conn.close()

    def insert_performance_metrics(self, case_id, metrics_dict):
        """Insert performance metrics for a completed simulation"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cols = ["case_id"] + list(metrics_dict.keys())
            vals = [case_id] + list(metrics_dict.values())
            placeholders = ",".join(["?" for _ in vals])

            cursor.execute(
                f"""
                INSERT INTO performance_metrics ({",".join(cols)})
                VALUES ({placeholders})
            """,
                vals,
            )

            # Update case status to completed
            cursor.execute(
                """
                UPDATE run_cases 
                SET status = 'completed' 
                WHERE id = ?
            """,
                (case_id,),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            conn.close()
            print(f"Error inserting metrics: {e}")
            return False

    def get_case_comparison(self, case_names):
        """Get detailed comparison data for specific cases"""
        if not case_names:
            return pd.DataFrame()

        placeholders = ",".join(["?" for _ in case_names])

        # Build column list dynamically
        design_cols = [f"dp.{col}" for col in self.design_params]
        perf_cols = [f"pm.{col}" for col in self.performance_metrics]

        query = f"""
            SELECT 
                rc.*,
                {", ".join(design_cols)},
                {", ".join(perf_cols)}
            FROM run_cases rc
            LEFT JOIN design_parameters dp ON rc.id = dp.case_id
            LEFT JOIN performance_metrics pm ON rc.id = pm.case_id
            WHERE rc.case_name IN ({placeholders})
        """

        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=case_names)
        conn.close()
        return df

    def get_parameter_bounds(self):
        """Get min/max bounds for all parameters"""
        conn = self.get_connection()

        bounds_queries = []
        for param in self.design_params:
            bounds_queries.append(f"MIN({param}) as min_{param}")
            bounds_queries.append(f"MAX({param}) as max_{param}")

        query = f"""
            SELECT {", ".join(bounds_queries)}
            FROM design_parameters
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df.iloc[0].to_dict() if not df.empty else {}

    # def get_optimization_suggestions(self):
    #     """Analyze data and provide optimization suggestions"""
    #     conn = self.get_connection()

    #     # Get best performing cases
    #     design_cols = [f"dp.{col}" for col in self.design_params]

    #     query = f"""
    #         SELECT 
    #             {", ".join(design_cols)},
    #             pm.nox_emissions, pm.combustion_efficiency, pm.pattern_factor # custom design suggestion criteria
    #         FROM design_parameters dp
    #         JOIN performance_metrics pm ON dp.case_id = pm.case_id
    #         WHERE pm.nox_emissions IS NOT NULL
    #         ORDER BY pm.nox_emissions ASC
    #         LIMIT 5
    #     """

    #     best_cases = pd.read_sql_query(query, conn)
    #     conn.close()

    #     if best_cases.empty:
    #         return {}

    #     # Calculate average parameters of best cases
    #     suggestions = {
    #         f"optimal_{param}": best_cases[param].mean() for param in self.design_params
    #     }

    #     suggestions.update(
    #         {
    #             "avg_nox_top5": best_cases["nox_emissions"].mean(),
    #             "avg_efficiency_top5": best_cases["combustion_efficiency"].mean(),
    #         }
    #     )

    #     return suggestions

    def export_case_data(self, case_name, filepath):
        """Export case data to JSON file"""
        df = self.get_case_comparison([case_name])

        if not df.empty:
            case_data = df.iloc[0].to_dict()

            # Convert datetime to string
            if "timestamp" in case_data:
                case_data["timestamp"] = str(case_data["timestamp"])

            # Remove NaN values
            case_data = {k: v for k, v in case_data.items() if pd.notna(v)}

            # Save to JSON
            with open(filepath, "w") as f:
                json.dump(case_data, f, indent=2)

            return True
        return False

    def import_case_data(self, filepath):
        """Import case data from JSON file"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Create new name to avoid conflicts
            original_name = data.get("case_name", "Imported_Case")
            new_name = (
                f"{original_name}_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            # Extract design parameters
            design_params = {
                param: data.get(
                    param, SCHEMA["design_parameters"][param].get("default", 0)
                )
                for param in self.design_params
            }

            # Extract performance metrics if available
            performance_metrics = None
            if data.get("status") == "completed" and any(
                data.get(metric) is not None for metric in self.performance_metrics
            ):
                performance_metrics = {
                    metric: data.get(metric)
                    for metric in self.performance_metrics
                    if data.get(metric) is not None
                }

            # Insert the case
            success = self.insert_case(
                new_name,
                data.get("description", ""),
                data.get("status", "completed"),
                design_params,
                performance_metrics,
            )

            return success, new_name if success else None

        except Exception as e:
            print(f"Error importing case: {e}")
            return False, None

    def delete_case(self, case_name):
        """Delete a case and all associated data"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get case ID
            cursor.execute("SELECT id FROM run_cases WHERE case_name = ?", (case_name,))
            result = cursor.fetchone()

            if result:
                case_id = result[0]

                # Delete in order due to foreign key constraints
                cursor.execute(
                    "DELETE FROM performance_metrics WHERE case_id = ?", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM design_parameters WHERE case_id = ?", (case_id,)
                )
                cursor.execute("DELETE FROM run_cases WHERE id = ?", (case_id,))

                conn.commit()
                conn.close()
                return True

            conn.close()
            return False

        except Exception as e:
            conn.close()
            print(f"Error deleting case: {e}")
            return False
