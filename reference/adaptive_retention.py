"""Bounded single-eviction ranking for FUTURE fresh matrices, never current A."""

from reference.supply_model import pool_law, score_hit_probability, validate_pool

MAX_DECISIONS = 64


def fraction_record(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


class FutureSupplyRetainer:
    """State belongs to one campaign; construct a new object for each paired run."""
    def __init__(self, target, *, decisions=MAX_DECISIONS):
        score_hit_probability((1, 0), target)
        if type(decisions) is not int or not 1 <= decisions <= MAX_DECISIONS:
            raise ValueError('retention decision cap')
        self.target, self.limit = target, decisions
        self.records = []
        self.fallbacks = self.evaluations = self.rank_units = 0

    def __call__(self, profile, candidates, capacity):
        candidates = validate_pool(profile, candidates)
        if (profile.m > 16 or type(capacity) is not int or not 1 <= capacity <= 3
                or len(candidates) != capacity+1):
            raise ValueError('retention candidate bounds')
        if len(self.records) == self.limit:
            self.fallbacks += 1
            return candidates[1:]
        choices, probabilities = [], []
        units = 0
        for index in range(len(candidates)):
            retained = candidates[:index]+candidates[index+1:]
            law = pool_law(profile, retained)
            probabilities.append(score_hit_probability(law.histogram, self.target))
            choices.append(retained)
            units += law.rank_arithmetic_units
        # Candidate0 is FIFO. On equal maxima the first option wins; FIFO wins
        # a tie only when its own probability reaches that maximum.
        best = max(range(len(choices)), key=probabilities.__getitem__)
        self.evaluations += len(choices)
        self.rank_units += units
        self.records.append({'candidates': candidates, 'capacity': capacity, 'chosen_eviction': best,
                             'probabilities': [fraction_record(p) for p in probabilities],
                             'rank_arithmetic_units': units})
        return choices[best]

    def snapshot(self):
        return {'criterion': 'future-iid-matrix-conditional-iid-score-hypothesis',
                'decision_cap': self.limit, 'decisions': len(self.records), 'evaluations': self.evaluations,
                'rank_arithmetic_units': self.rank_units, 'fifo_fallbacks': self.fallbacks,
                'records': list(self.records)}
