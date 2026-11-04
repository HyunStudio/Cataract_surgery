"""Revisit physical reactions after a changed accepted material iterate."""
import json
from pathlib import Path
import unittest
import numpy as np
from replay_fem_trajectory import replay
import test_fem_trajectory as trajectory
ROOT=Path(__file__).resolve().parents[2]
class PhysicalPolishFreshnessTests(unittest.TestCase):
 def test_actual156_four_layer_candidate_recomputes_physical_reactions(self):
  case=json.loads((ROOT/'docs/assets/operative-motion156-native-case-2026-11-05.json').read_text())
  seed=json.loads((ROOT/'native/tests/fixtures/operative_motion156_seed.json').read_text())
  request=dict(case['fem_request']);request['budget']-=seed['prior_iterations']
  multipliers=np.zeros(seed['dual_count'])
  for i,value in seed['dual_nonzero']:multipliers[i]=value
  motion=case['motion']
  result=replay(request,case['previous_controls'],motion['kinds'],motion['packets'],seed['times'],ROOT/'.tools/native/membrane_fem.dll',initial=seed['initial'],multiplier_seed=multipliers,penalty_seed=seed['penalty_seed'])
  self.assertEqual(result[0],0,result[4])
  trajectory.FEMTrajectoryTests().verify(request,case['previous_controls'],motion['kinds'],motion['packets'],seed['times'],result)
  self.assertLessEqual(seed['prior_iterations']+int(result[4][2]),case['fem_request']['budget'])
if __name__=='__main__':unittest.main()
