
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.calculator import IndicatorCalculator

class TestCalculator:
    def setup_method(self):
        self.calc = IndicatorCalculator()

    def test_roe_slope(self):
        # Increasing trend
        roes = [0.10, 0.12, 0.14]
        slope = self.calc.calculate_roe_slope(roes)
        assert slope is not None
        assert slope > 0
        assert abs(slope - 0.02) < 0.001

        # Decreasing trend
        roes = [0.14, 0.12, 0.10]
        slope = self.calc.calculate_roe_slope(roes)
        assert slope is not None
        assert slope < 0
        assert abs(slope + 0.02) < 0.001

        # Flat
        roes = [0.10, 0.10, 0.10]
        slope = self.calc.calculate_roe_slope(roes)
        assert slope == 0

        # Insufficient data
        assert self.calc.calculate_roe_slope([0.1]) is None
        assert self.calc.calculate_roe_slope([]) is None

    def test_cagr(self):
        # Normal case: 100 -> 121 in 2 years (10% growth)
        cagr = self.calc.calculate_cagr(100, 121, 2)
        assert cagr is not None
        assert abs(cagr - 0.10) < 0.001

        # Zero start
        assert self.calc.calculate_cagr(0, 100, 3) is None
        
        # Negative start
        assert self.calc.calculate_cagr(-10, 100, 3) is None

    def test_cr3(self):
        revenues = [100, 50, 30, 20, 10] # Total 210, Top3=180
        cr3 = self.calc.calculate_cr3(revenues)
        expected = 180 / 210
        assert cr3 is not None
        assert abs(cr3 - expected) < 0.001

        # Empty
        assert self.calc.calculate_cr3([]) is None

    def test_leader_share_change(self):
        # 30% -> 35% in 1 year
        change = self.calc.calculate_leader_share_change(35, 30, 1)
        assert change == 5.0
        
    def test_gross_margin_trend(self):
        from src.utils import Trend
        # Rising: 10% -> 12% -> 14%
        # Slope = 2.0. Threshold default = 1.0. Should be RISING.
        margins = pd.Series([10.0, 12.0, 14.0])
        trend = self.calc.calculate_gross_margin_trend(margins)
        assert trend == Trend.RISING
        
        # Stable: 10% -> 10.5% -> 11%
        # Slope = 0.5. Threshold = 1.0. Should be STABLE.
        margins = pd.Series([10.0, 10.5, 11.0])
        trend = self.calc.calculate_gross_margin_trend(margins)
        assert trend == Trend.STABLE

