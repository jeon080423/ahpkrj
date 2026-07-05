import unittest
import yeta_utils
import math

class TestYetaMath(unittest.TestCase):
    
    def test_convert_bc_to_ahp_pairwise(self):
        # 1. B/C = 1.0 -> should yield exactly 1.0 (equal importance)
        self.assertAlmostEqual(yeta_utils.convert_bc_to_ahp_pairwise(1.0), 1.0, places=5)
        
        # 2. B/C = 2.5 -> should yield value > 1.0 and <= 9.0
        val_high = yeta_utils.convert_bc_to_ahp_pairwise(2.5)
        self.assertTrue(1.0 < val_high <= 9.0)
        
        # 3. B/C = 0.5 -> should yield value < 1.0 and >= 1/9
        val_low = yeta_utils.convert_bc_to_ahp_pairwise(0.5)
        self.assertTrue(1.0/9.0 <= val_low < 1.0)
        
        # 4. Out of bounds check
        self.assertAlmostEqual(yeta_utils.convert_bc_to_ahp_pairwise(0), 1.0/9.0, places=5)
        self.assertAlmostEqual(yeta_utils.convert_bc_to_ahp_pairwise(100.0), 9.0, places=5)

    def test_validate_yeta_level1_weights(self):
        # 1. Construction Non-capital: valid weights (Econ 35%, Policy 30%, Regional 35%)
        valid, msg = yeta_utils.validate_yeta_level1_weights("construction_non_capital", 0.35, 0.30, 0.35)
        self.assertTrue(valid)
        
        # 2. Construction Non-capital: invalid sum (80%)
        valid, msg = yeta_utils.validate_yeta_level1_weights("construction_non_capital", 0.30, 0.30, 0.20)
        self.assertFalse(valid)
        
        # 3. Construction Non-capital: invalid range (Econ 50%)
        valid, msg = yeta_utils.validate_yeta_level1_weights("construction_non_capital", 0.50, 0.25, 0.25)
        self.assertFalse(valid)
        
        # 4. Construction Capital: valid weights (Econ 65%, Policy 35%, Regional 0%)
        valid, msg = yeta_utils.validate_yeta_level1_weights("construction_capital", 0.65, 0.35, 0.0)
        self.assertTrue(valid)

    def test_aggregate_yeta_group_ahp(self):
        # 1. 5 evaluators: [0.45, 0.48, 0.52, 0.56, 0.61]
        # Sorted: 0.45 (min), 0.48, 0.52, 0.56, 0.61 (max)
        # Filtered (remove min/max): [0.48, 0.52, 0.56]
        # Geometric mean of [0.48, 0.52, 0.56] = (0.48 * 0.52 * 0.56) ** (1/3)
        expected_geom = (0.48 * 0.52 * 0.56) ** (1.0/3.0)
        scores = [0.52, 0.48, 0.56, 0.61, 0.45]
        result = yeta_utils.aggregate_yeta_group_ahp(scores)
        self.assertAlmostEqual(result, expected_geom, places=5)
        
        # 2. 2 evaluators: should not exclude outliers (n < 3)
        scores_short = [0.48, 0.52]
        expected_short_geom = (0.48 * 0.52) ** (1.0/2.0)
        result_short = yeta_utils.aggregate_yeta_group_ahp(scores_short)
        self.assertAlmostEqual(result_short, expected_short_geom, places=5)

if __name__ == '__main__':
    unittest.main()
