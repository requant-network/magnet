"""Research-only header-score repair; existing proof-bound B is unchanged."""

from fractions import Fraction
import hashlib

from reference.header import LabHeader

DOMAIN = b'MagnetNetwork/SIS-LAB/header-gate/v1\0'


def header_digest(header):
    if not isinstance(header, LabHeader):
        raise ValueError('expected research header')
    return hashlib.sha256(DOMAIN+header.encode()).digest()


def passes(header, target):
    if type(target) is not int or not 0 <= target <= 2**256:
        raise ValueError('header target bounds')
    return int.from_bytes(header_digest(header), 'big') < target


def renewal_costs(target, success, gate_cost, solve_cost):
    """Conditional iid model, NOT a cost fitted to bounded integration batches.

    Header scores must be uniform and independent of the entire target-independent
    SIS attempt transcript. Attempts have success probability s>0 and mean cost C;
    cycles are iid, G includes header/score generation. Cost can correlate with
    attempt success. Scores have probability p=T/2^256. No supply or cost guarantee
    is implied for the actual deterministic generator/optimized miner.
    """
    if type(target) is not int or not 1 <= target <= 2**256:
        raise ValueError('positive finite header target required')
    if (type(success) not in (int, Fraction) or not 0 < success <= 1
            or max(success.numerator.bit_length(), success.denominator.bit_length()) > 256):
        raise ValueError('positive bounded exact success probability')
    if (type(gate_cost) is not int or not 1 <= gate_cost <= 1_000_000
            or type(solve_cost) is not int or not 0 <= solve_cost <= 1_000_000):
        raise ValueError('illustrative cost bounds')
    p = Fraction(target, 2**256)
    return (Fraction(gate_cost+solve_cost)/(p*success),
            Fraction(gate_cost)/(p*success)+Fraction(solve_cost)/success)
