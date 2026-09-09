import unittest

from tensormesh.compute import (
    SurveyStation,
    compute_minimum_curvature_trajectory,
    decode_morton_3d,
    encode_morton_3d,
)


class SpatialComputeTests(unittest.TestCase):
    def test_morton_round_trip(self):
        for coordinates in ((0, 0, 0), (1, 2, 3), (17, 23, 31), (2**21 - 1, 2**21 - 1, 2**21 - 1)):
            with self.subTest(coordinates=coordinates):
                self.assertEqual(decode_morton_3d(encode_morton_3d(*coordinates)), coordinates)

    def test_minimum_curvature_trajectory(self):
        trajectory = compute_minimum_curvature_trajectory([
            SurveyStation(0.0, 0.0, 0.0),
            SurveyStation(100.0, 0.0, 0.0),
            SurveyStation(200.0, 90.0, 0.0),
        ])
        self.assertEqual(len(trajectory), 3)
        self.assertAlmostEqual(trajectory[1].true_vertical_depth_m, 100.0)
        self.assertAlmostEqual(trajectory[2].northing_m, 63.661977, places=4)


if __name__ == "__main__":
    unittest.main()