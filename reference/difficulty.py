"""Synthetic score-arrival/retarget hypotheses. Not MGB1 validity or priced SIS work."""

from fractions import Fraction
import math
import random

LOW_TARGET, HIGH_TARGET, INITIAL_TARGET = 2**232, 2**255, 2**252
METHODS = ("fixed", "window", "per-block")


def adjust(target, observed, expected):
    if type(target) is not int or not LOW_TARGET <= target <= HIGH_TARGET:
        raise ValueError("target outside synthetic experiment")
    if type(observed) is not int or observed < 0 or type(expected) is not int or expected <= 0:
        raise ValueError("integer nonnegative span/positive expected span required")
    ratio = min(Fraction(4), max(Fraction(1,4), Fraction(observed,expected)))
    return max(LOW_TARGET,min(HIGH_TARGET,target*ratio.numerator//ratio.denominator))


def expected_score_trials(target):
    if type(target) is not int or not 1 <= target <= 2**256:
        raise ValueError("score target outside range")
    return Fraction(2**256,target)


def simulate(*, seed, method, interval, capacity, reuse=1, attack="none", blocks=128):
    if type(seed) is not int or not 0 <= seed < 2**64 or type(method) is not str or method not in METHODS or type(interval) is not int or interval not in (30,60,120):
        raise ValueError("simulation configuration")
    if capacity not in (0.1,0.5,1,2,10) or type(capacity) not in (int,float) or type(reuse) is not int or not 1 <= reuse <= 16:
        raise ValueError("capacity/reuse outside declared cohorts")
    if type(attack) is not str or attack not in ("none","future","past","oscillating") or type(blocks) is not int or not 1 <= blocks <= 512:
        raise ValueError("attack/event cap")
    rng=random.Random(seed)
    target=INITIAL_TARGET
    clock=0.0
    timestamps=[]
    records=[]
    nominal_lower,nominal_upper=0,0
    for index in range(blocks):
        # Change score-input supply halfway through. No actual SIS solving,
        # transport or energy is simulated by this Poisson hypothesis.
        supply = 1 if index < blocks//2 else capacity*reuse
        rate = supply/interval * target/INITIAL_TARGET
        wait=rng.expovariate(rate)
        if not math.isfinite(wait) or clock+wait >= 2**64-121:
            raise RuntimeError("synthetic clock overflow")
        clock+=wait
        now=int(clock)
        median=sorted(timestamps[-11:])[len(timestamps[-11:])//2] if timestamps else 0
        stamp=max(now,median+1)
        if attack=="future" or attack=="oscillating" and index%2==0:
            stamp=now+120
        elif attack=="past" or attack=="oscillating":
            stamp=median+1
        allowed = median < stamp <= now+120
        record={"index":index,"target":str(target),"actual_interval_seconds":wait,
                "local_seconds":now,"timestamp":stamp,"accepted_time":allowed,
                "score_input_supply_multiplier":supply}
        if allowed:
            # Exact per-event rational bounds avoid an exponentially growing
            # common denominator when hundreds of rounded targets differ.
            trials=expected_score_trials(target)
            nominal_lower+=trials.numerator//trials.denominator
            nominal_upper+=(trials.numerator+trials.denominator-1)//trials.denominator
            previous=timestamps[-1] if timestamps else 0
            timestamps.append(stamp)
            if method=="per-block":
                target=adjust(target,max(0,stamp-previous),interval)
            elif method=="window" and len(timestamps)%16==0:
                start=timestamps[-17] if len(timestamps)>16 else 0
                target=adjust(target,max(0,stamp-start),16*interval)
        record["next_target"]=str(target)
        records.append(record)
    after=[r["actual_interval_seconds"] for r in records[blocks//2:]]
    return {"method":method,"seed":seed,"desired_interval":interval,"capacity":capacity,"reuse":reuse,
            "attack":attack,"events":blocks,"time_accepted":len(timestamps),
            "mean_interval_after_shock":sum(after)/len(after),"final_target":str(target),
            "inverse_target_nominal_trials_bounds":[nominal_lower,nominal_upper],"records":records,
            "scope":"synthetic independent eligible-score inputs; no SIS, network, fork choice or monetary work"}
