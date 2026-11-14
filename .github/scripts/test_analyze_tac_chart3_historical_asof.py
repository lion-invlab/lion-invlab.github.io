import unittest
import analyze_tac_chart3_historical_asof as m

class HistoricalAsOfTests(unittest.TestCase):
    def test_same_day_vintage_is_excluded(self):
        d={"X":{"2020-01-01":{"2020-01-01":"4.0"}}}
        self.assertIsNone(m.asof_latest(d,"X","2020-01-01"))
        self.assertEqual(m.asof_latest(d,"X","2020-01-02")["value"],4.0)

    def test_future_observation_is_excluded(self):
        d={"X":{"2020-01-06":{"2020-01-07":"5.0"}}}
        self.assertIsNone(m.asof_latest(d,"X","2020-01-05"))

    def test_latest_missing_vintage_is_not_replaced_by_older_vintage(self):
        d={"X":{"2020-01-01":{"2020-01-02":"3.0","2020-01-04":"."}}}
        self.assertIsNone(m.asof_latest(d,"X","2020-01-05"))

    def test_latest_observation_known_as_of(self):
        d={"X":{"2020-01-01":{"2020-01-02":"3.0"},"2020-01-08":{"2020-01-10":"6.0"},"2020-01-15":{"2020-01-20":"9.0"}}}
        got=m.asof_latest(d,"X","2020-01-12")
        self.assertEqual((got["observation_date"],got["vintage_date"],got["value"]),("2020-01-08","2020-01-10",6.0))

    def test_pre_archive_observation_is_left_censored_not_false_initial_release(self):
        d={"X":{"2007-07-01":{"2010-11-22":"20.0"},"2010-11-23":{"2010-11-24":"21.0"}}}
        got=m.release_summary(d,"X","2007-07-01","2009-06-30")
        self.assertEqual(got["event_observations_left_censored_before_archive_start"],1)
        self.assertEqual(got["event_observations_with_any_numeric_vintage"],0)
        self.assertIsNone(got["median_initial_release_lag_calendar_days"])

    def test_release_lag_and_by_end(self):
        d={"X":{"2020-01-01":{"2020-01-03":"1.0"},"2020-01-08":{"2020-01-12":"2.0"}}}
        got=m.release_summary(d,"X","2020-01-01","2020-01-15")
        self.assertEqual(got["median_initial_release_lag_calendar_days"],4.0)
        self.assertEqual(got["event_observations_left_censored_before_archive_start"],1)
        self.assertEqual(got["event_observations_first_released_strictly_before_episode_end"],1)

if __name__ == "__main__":
    unittest.main()
