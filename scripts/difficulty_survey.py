"""Compare bounded synthetic retarget hypotheses; no production method selected."""

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reference.difficulty import simulate
from scripts.consensus_evidence import begin_report,finish_report


def main():
    paths=begin_report('difficulty-v1'); manifest=paths[2]
    records=[simulate(seed=seed,method=method,interval=interval,capacity=capacity,reuse=reuse,attack=attack)
             for seed in (20261008124,20261008125) for method in ('fixed','window','per-block')
             for interval in (30,60,120) for capacity in (0.1,0.5,1,2,10)
             for reuse in (1,4) for attack in ('none','future','past','oscillating')]
    report={"scenarios":len(records),"events":sum(r['events'] for r in records),
            "configuration":{"events_per_scenario":128,"shock_after_events":64,"window":16,"clamp":["1/4","4"],
                             "target_bounds":[str(2**232),str(2**255)],"initial_target":str(2**252),"future_seconds":120},
            "records":[{k:v for k,v in r.items() if k!='records'} for r in records],
            "limitations":["synthetic Poisson supply of independently eligible score inputs, not measured SIS arrivals",
                           "reuse multiplier is a declared hypothetical input-supply factor, not measured cost",
                           "no production retarget, target-changing MGB1 admission or safe chainwork chosen",
                           "rounded-target exact nominal trial sums bracketed by per-event floor/ceil bounds",
                           "finite two-seed cohorts do not prove stability under arbitrary attacks"]}
    finish_report(paths,report,manifest,raw={"records":records})


if __name__=='__main__': main()
