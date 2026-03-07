import pytest
import aiosqlite
import numpy as np
import uuid
import os
from calibration import CalibrationTracker
from jarvis_common.schemas import CalibrationProfile

TEST_DB_PATH = "test_jarvis_state.db"

# Override the DB_PATH for testing
import calibration
calibration.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
async def setup_test_db():
    # Remove old test db if it exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS confidence_records (
                trace_id TEXT PRIMARY KEY,
                predicted_confidence REAL NOT NULL,
                actual_success BOOLEAN NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calibration_profiles (
                profile_id TEXT PRIMARY KEY,
                temperature_scalar REAL NOT NULL,
                brier_score REAL,
                records_used INTEGER NOT NULL,
                fitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

@pytest.mark.asyncio
async def test_calibration_tracker_initializes_with_default_temp():
    tracker = CalibrationTracker()
    assert tracker.current_temperature == 1.0

@pytest.mark.asyncio
async def test_calibration_tracker_loads_latest_profile():
    # Insert a dummy profile
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        await db.execute(
            "INSERT INTO calibration_profiles (profile_id, temperature_scalar, brier_score, records_used) VALUES (?, ?, ?, ?)",
            ("prof_123", 2.5, 0.1, 500)
        )
        await db.commit()
        
    tracker = CalibrationTracker()
    await tracker.initialize()
    
    assert tracker.current_temperature == 2.5

@pytest.mark.asyncio
async def test_record_prediction_saves_to_db():
    tracker = CalibrationTracker()
    trace_id = str(uuid.uuid4())
    await tracker.record_prediction(trace_id, 0.85, True)
    
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM confidence_records WHERE trace_id = ?", (trace_id,))
        row = await cursor.fetchone()
        
        assert row is not None
        assert row["predicted_confidence"] == 0.85
        assert row["actual_success"] == 1

@pytest.mark.asyncio
async def test_generate_reliability_diagram_groups_bins_correctly():
    tracker = CalibrationTracker()
    
    # Insert reliable predictions
    for i in range(10):
        # bin 0.8 - 0.9. Actually successful 8/10 times (80%)
        # So it's perfectly calibrated
        success = i < 8 
        await tracker.record_prediction(str(uuid.uuid4()), 0.85, success)
        
    for i in range(10):
        # bin 0.4 - 0.5. Actually successful 2/10 times (20%)
        # So it's overconfident here
        success = i < 2
        await tracker.record_prediction(str(uuid.uuid4()), 0.45, success)
        
    diagram = await tracker.generate_reliability_diagram(bins=10)
    
    # Bins are 0.0-0.1...
    # Bin index 4 is 0.4-0.5
    bin_4 = diagram[4]
    assert bin_4["bin_lower"] == 0.4
    assert bin_4["bin_upper"] == 0.5
    assert bin_4["samples"] == 10
    assert abs(bin_4["avg_predicted"] - 0.45) < 0.01
    assert abs(bin_4["actual_success_rate"] - 0.2) < 0.01
    
    # Bin index 8 is 0.8-0.9
    bin_8 = diagram[8]
    assert bin_8["samples"] == 10
    assert abs(bin_8["avg_predicted"] - 0.85) < 0.01
    assert abs(bin_8["actual_success_rate"] - 0.8) < 0.01

@pytest.mark.asyncio
async def test_fit_temperature_handles_overconfident_models():
    tracker = CalibrationTracker()
    
    # Create OVERCONFIDENT responses. 
    # It predicts 0.9 confidence, but only succeeds 60% of the time.
    for i in range(100):
        success = i < 60
        await tracker.record_prediction(str(uuid.uuid4()), 0.90, success)
        
    profile = await tracker.fit_temperature(min_samples=50)
    
    assert profile is not None
    assert isinstance(profile, CalibrationProfile)
    # T > 1.0 "softens" probabilities (pushes them toward 0.5)
    assert profile.temperature_scalar > 1.0  
    assert profile.records_used == 100
    
    assert tracker.current_temperature == profile.temperature_scalar
    
    # Let's see the effect
    raw = 0.90
    calibrated = tracker.calibrate(raw)
    
    # A raw 0.9 should become much closer to the true 0.6 success rate
    assert calibrated < 0.90
    assert calibrated > 0.50

@pytest.mark.asyncio
async def test_fit_temperature_handles_underconfident_models():
    tracker = CalibrationTracker()
    
    # Create UNDERCONFIDENT responses. 
    # It predicts 0.6 confidence, but succeeds 90% of the time.
    for i in range(100):
        success = i < 90
        await tracker.record_prediction(str(uuid.uuid4()), 0.60, success)
        
    profile = await tracker.fit_temperature(min_samples=50)
    
    # T < 1.0 "hardens" probabilities (pushes them toward 0 or 1)
    assert profile.temperature_scalar < 1.0 
    
    calibrated = tracker.calibrate(0.60)
    # A raw 0.6 should be pushed much higher, closer to 0.9
    assert calibrated > 0.60

@pytest.mark.asyncio
async def test_fit_temperature_rejects_insufficient_samples():
    tracker = CalibrationTracker()
    for i in range(10):  # Only 10 records
        await tracker.record_prediction(str(uuid.uuid4()), 0.90, True)
        
    profile = await tracker.fit_temperature(min_samples=50)
    assert profile is None
    assert tracker.current_temperature == 1.0
