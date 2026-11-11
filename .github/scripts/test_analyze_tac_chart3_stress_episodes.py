import importlib.util,unittest
from pathlib import Path
p=Path(__file__).with_name("analyze_tac_chart3_stress_episodes.py")
sp=importlib.util.spec_from_file_location("a",p);a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
class T(unittest.TestCase):
 def test_cutoff_is_strict(self):
  d={"X":{"2020-01-01":{"2020-01-01":"1","2020-01-03":"2"}}}
  self.assertEqual(a.rows(d,"X","2020-01-01","2020-01-01","2020-01-03")[0]["value"],1)
 def test_pre_observation_check_excludes_same_day(self):
  d={"X":{"2020-01-01":{"2020-01-01":"1"}}}
  self.assertEqual(a.pre_observation_vintage_count(d,"X","2020-01-01","2020-01-01"),0)
 def test_no_fill_for_missing(self):
  self.assertIsNone(a.num("."));self.assertIsNone(a.num(""))
 def test_missing_event_not_counted_as_historical_pit(self):
  d={"X":{"2020-01-01":{"2019-12-31":"."},"2020-01-02":{"2020-01-01":""},"2020-01-03":{"2020-01-01":"2.5"}}}
  self.assertEqual(a.pit_count(d,"X","2020-01-01","2020-01-03"),1)
 def test_peak(self):
  x=a.stats([{"observation_date":"a","value":1},{"observation_date":"b","value":3}])
  self.assertEqual((x["max"],x["max_date"],x["n"]),(3,"b",2))
if __name__=="__main__":unittest.main()
