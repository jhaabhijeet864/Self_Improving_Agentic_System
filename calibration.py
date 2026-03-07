import numpy as np
from scipy.optimize import minimize
from datetime import datetime
import aiosqlite
from jarvis_common.schemas import ConfidenceRecord, CalibrationProfile
from database import DB_PATH

class CalibrationTracker:
    def __init__(self):
        self.current_temperature = 1.0

    async def initialize(self):
        """Load the latest temperature scalar from the database."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT temperature_scalar FROM calibration_profiles ORDER BY fitted_at DESC LIMIT 1")
            row = await cursor.fetchone()
            if row:
                self.current_temperature = row["temperature_scalar"]

    async def record_prediction(self, trace_id: str, confidence: float, actual_success: bool):
        """Save a new confidence record to the database."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO confidence_records (trace_id, predicted_confidence, actual_success) VALUES (?, ?, ?)",
                (trace_id, confidence, actual_success)
            )
            await db.commit()

    async def generate_reliability_diagram(self, bins=10) -> list[dict]:
        """
        Group recent records into bins and calculate the actual success rate
        for each predicted confidence bin.
        Returns a list of dictionaries with bin ranges, average predicted, and actual success rate.
        """
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT predicted_confidence, actual_success FROM confidence_records ORDER BY recorded_at DESC LIMIT 1000")
            rows = await cursor.fetchall()
            
            if not rows:
                return []

            predictions = np.array([row[0] for row in rows])
            actuals = np.array([row[1] for row in rows])
            
            bin_edges = np.linspace(0.0, 1.0, bins + 1)
            diagram_data = []

            for i in range(bins):
                lower = bin_edges[i]
                upper = bin_edges[i+1]
                
                # Assign to bin (inclusive of lower bound, exclusive of upper, except for the last bin)
                if i == bins - 1:
                    mask = (predictions >= lower) & (predictions <= upper)
                else:
                    mask = (predictions >= lower) & (predictions < upper)
                
                bin_predictions = predictions[mask]
                bin_actuals = actuals[mask]
                
                if len(bin_predictions) > 0:
                    avg_predicted = np.mean(bin_predictions)
                    actual_success_rate = np.mean(bin_actuals)
                    samples = len(bin_predictions)
                else:
                    avg_predicted = 0.0
                    actual_success_rate = 0.0
                    samples = 0
                    
                diagram_data.append({
                    "bin_lower": float(lower),
                    "bin_upper": float(upper),
                    "avg_predicted": float(avg_predicted),
                    "actual_success_rate": float(actual_success_rate),
                    "samples": samples
                })
                
            return diagram_data

    async def fit_temperature(self, min_samples=100) -> CalibrationProfile:
        """
        Extract recent records. Use temperature scaling to find the optimal T 
        that minimizes the Negative Log Likelihood.
        """
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT predicted_confidence, actual_success FROM confidence_records ORDER BY recorded_at DESC LIMIT 1000")
            rows = await cursor.fetchall()
            
            if len(rows) < min_samples:
                print(f"Not enough samples to fit temperature. Need {min_samples}, have {len(rows)}.")
                return None

            predictions = np.array([row[0] for row in rows])
            # Prevent log(0) and log(1)
            predictions = np.clip(predictions, 1e-7, 1 - 1e-7)
            actuals = np.array([row[1] for row in rows], dtype=float)

            # Convert probabilities to logits: L = log(p / (1 - p))
            logits = np.log(predictions / (1 - predictions))

            def nll_with_temperature(t):
                """Negative Log Likelihood with temperature scaling."""
                scaled_logits = logits / t[0]
                # Convert back to scaled probabilities
                scaled_probs = 1 / (1 + np.exp(-scaled_logits))
                
                # NLL
                nll = -np.mean(actuals * np.log(scaled_probs) + (1 - actuals) * np.log(1 - scaled_probs))
                return nll

            # Optimize T starting from 1.0
            t_initial = [1.0]
            result = minimize(nll_with_temperature, t_initial, method='L-BFGS-B', bounds=[(0.1, 10.0)])
            
            optimal_t = float(result.x[0])
            brier_score = float(nll_with_temperature([optimal_t])) # Using NLL as brier proxy here for simplicity, though true brier is MSE
            
            # Save new profile to DB
            profile = CalibrationProfile(
                temperature_scalar=optimal_t,
                brier_score=brier_score,
                records_used=len(rows)
            )
            
            await db.execute(
                "INSERT INTO calibration_profiles (profile_id, temperature_scalar, brier_score, records_used) VALUES (?, ?, ?, ?)",
                (profile.profile_id, profile.temperature_scalar, profile.brier_score, profile.records_used)
            )
            await db.commit()
            
            self.current_temperature = optimal_t
            return profile

    def calibrate(self, raw_confidence: float) -> float:
        """
        Apply the current temperature scalar to the raw confidence score.
        """
        # Prevent math errors on boundaries
        raw_confidence = max(1e-7, min(1 - 1e-7, raw_confidence))
        
        # 1. Convert prob to logit
        logit = np.log(raw_confidence / (1 - raw_confidence))
        
        # 2. Scale logit
        scaled_logit = logit / self.current_temperature
        
        # 3. Convert back to prob
        calibrated_prob = 1 / (1 + np.exp(-scaled_logit))
        
        return float(calibrated_prob)
