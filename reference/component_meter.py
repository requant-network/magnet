"""Cooperative laboratory component model; no hardware/consensus currency."""

MODEL_VERSION = 'cooperative-components-v1'
ZERO_WEIGHT = ('matrix.shake_output_bytes',)


class ComponentStop(Exception):
    pass


class ComponentMeter:
    def __init__(self, limit):
        if type(limit) is not int or not 1 <= limit <= 1000000:
            raise ValueError('component budget outside laboratory range')
        self.limit, self.phases, self.used = limit, {}, 0
        self.first_boundary = None

    def sync(self, phase, counts):
        if type(phase) is not str or not phase or type(counts) is not dict:
            raise ValueError('invalid component snapshot')
        before = self.phases.get(phase, {})
        if any(type(k) is not str or not k for k in counts):
            raise ValueError('invalid component name')
        if any(type(v) is not int or v < before.get(k, 0) for k, v in counts.items()):
            raise ValueError('component counts must be monotonic nonnegative integers')
        if any(k not in counts for k in before):
            raise ValueError('component snapshot lost a counter')
        delta = sum(v-before.get(k, 0) for k, v in counts.items() if phase+'.'+k not in ZERO_WEIGHT)
        self.phases[phase] = dict(counts)
        self.used += delta
        if self.first_boundary is None and self.used >= self.limit:
            self.first_boundary = dict(phase=phase, used=self.used)

    def add(self, phase, **counts):
        current = dict(self.phases.get(phase, {}))
        if any(type(v) is not int or v < 0 for v in counts.values()):
            raise ValueError('invalid component increment')
        for name, value in counts.items():
            current[name] = current.get(name, 0)+value
        self.sync(phase, current)

    def check(self):
        if self.used >= self.limit:
            raise ComponentStop('component-budget')

    def report(self):
        return dict(model=MODEL_VERSION, zero_weight=list(ZERO_WEIGHT), limit=self.limit,
                    used=self.used, overshoot=max(0, self.used-self.limit),
                    first_boundary=self.first_boundary,
                    post_boundary_units=0 if self.first_boundary is None else self.used-self.first_boundary['used'],
                    phases={k: dict(v) for k, v in self.phases.items()})
