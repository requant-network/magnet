import hashlib
import gc
import itertools
import tracemalloc
import unittest
import weakref
from unittest.mock import patch

from reference.ball import BallSearch
from reference.budgets import BudgetExceeded, run_budgeted
from reference.mitm import MitmSearch
from reference.search import exhaustive_solutions
from reference.sis import Profile, expand_matrix, verify
from reference.strategies import _score_message


class BallTests(unittest.TestCase):
    def test_exact_sets_and_unique_outputs(self):
        for m in range(1, 7):
            p = Profile(7, 2, m, 8)
            for index in range(6):
                a = expand_matrix(p, index.to_bytes(32, "little"))
                search = BallSearch(p, a)
                proofs = list(search.solutions())
                self.assertEqual(set(proofs), set(exhaustive_solutions(p, a)))
                self.assertEqual(len(proofs), len(set(proofs)))
                self.assertEqual(search.reason, "domain-exhausted")
                self.assertTrue(all(verify(p, a, x) for x in proofs))

    def test_small_ball_with_huge_box(self):
        p = Profile(7, 1, 20, 1)
        search = BallSearch(p, [[0] * 20])
        proofs = list(search.solutions())
        expected = {tuple(int(j == i) for j in range(20)) for i in range(20)}
        self.assertEqual(set(proofs), expected)
        self.assertEqual(search.work.leaves, 21)
        self.assertNotIn((0,) * 20, proofs)

    def test_node_limit_and_close_are_not_exhaustion(self):
        search = BallSearch(Profile(7, 1, 3, 4), [[0, 0, 0]], node_limit=1)
        self.assertEqual(list(search.solutions()), [])
        self.assertEqual(search.reason, "node-limit")
        self.assertEqual(search.work.prefix_nodes, 1)
        search = BallSearch(Profile(7, 1, 2, 4), [[0, 0]])
        iterator = search.solutions()
        iterator.close()
        self.assertEqual(search.reason, "interrupted")
        with self.assertRaises(ValueError):
            search.solutions()

    def test_checkpoints_interrupt_both_solvers(self):
        for cls in (BallSearch, MitmSearch):
            def stop():
                raise BudgetExceeded("time-limit")
            search = cls(Profile(7, 1, 4, 4), [[0] * 4], checkpoint=stop)
            iterator = search.solutions()
            with self.assertRaises(BudgetExceeded):
                next(iterator)
            iterator.close()
            self.assertEqual(search.reason, "interrupted")

    def test_finished_and_closed_search_do_not_depend_on_cyclic_gc(self):
        was_enabled = gc.isenabled()
        gc.disable()
        try:
            for finish in (True, False):
                search = BallSearch(Profile(7, 1, 3, 4), [[0, 0, 0]])
                reference = weakref.ref(search)
                iterator = search.solutions()
                if finish:
                    list(iterator)
                else:
                    next(iterator)
                iterator.close()
                del iterator, search
                self.assertIsNone(reference())
        finally:
            if was_enabled:
                gc.enable()

    def test_invalid_shape_limits_and_checkpoint(self):
        p, a = Profile(7, 1, 2, 4), [[0, 0]]
        for options in ({"node_limit": 0}, {"node_limit": True}, {"node_limit": 1_000_001},
                        {"checkpoint": 3}):
            with self.assertRaises(ValueError):
                BallSearch(p, a, **options)
        for p, a in ((None, a), (p, [[7, 0]]), (p, [[0]])):
            with self.assertRaises(ValueError):
                BallSearch(p, a)


class BudgetTests(unittest.TestCase):
    def test_full_budgeted_instance_has_exact_proof_transcript(self):
        p, root = Profile(7, 1, 3, 5), bytes(32)
        seed = hashlib.sha256(b"MagnetNetwork/SIS-LAB/budget-seed/v1\x00" + root + bytes(4)).digest()
        a = expand_matrix(p, seed)
        expected = set(exhaustive_solutions(p, a))
        for name, cls in (("ball", BallSearch), ("mitm", MitmSearch)):
            search = cls(p, a)
            proofs = list(search.solutions())
            transcript = hashlib.sha256()
            for x in proofs:
                transcript.update(_score_message(p, seed, x))
            result = run_budgeted(p, root, name, "continue", target=0, max_instances=1,
                                  time_limit_ns=1_000_000_000, memory_limit_bytes=16 * 1024 * 1024)
            self.assertEqual(result["reason"], "instance-limit")
            self.assertEqual(result["work"].get("score_hashes", 0), len(expected))
            self.assertEqual(result["transcript_sha256"], transcript.hexdigest())
            self.assertEqual(result["instance_stops"], {"domain-exhausted": 1})
            self.assertFalse(tracemalloc.is_tracing())

    def test_hits_move_to_new_seed_for_all_policies(self):
        p, root = Profile(101, 1, 2, 80), bytes(32)
        for algorithm in ("ball", "mitm"):
            for policy in ("continue", "restart", "reuse"):
                ticks = itertools.count()
                with patch("reference.budgets.expand_matrix", return_value=((1, 2),)):
                    result = run_budgeted(p, root, algorithm, policy, target=2**256,
                                          max_instances=2, clock=lambda: next(ticks))
                self.assertEqual(result["reason"], "instance-limit")
                self.assertEqual(result["work"]["hits"], 2)
                self.assertEqual(result["work"]["score_hashes"], 2)
                self.assertEqual(len({s["seed"] for s in result["hit_samples"]}), 2)

    def test_reuse_does_not_score_the_original_twice(self):
        p, root = Profile(101, 1, 2, 80), bytes(32)
        seed = hashlib.sha256(b"MagnetNetwork/SIS-LAB/budget-seed/v1\x00" + root + bytes(4)).digest()
        expected = {(2, -1), (4, -2), (6, -3), (8, -4)}
        for algorithm in ("ball", "mitm"):
            with patch("reference.budgets.expand_matrix", return_value=((1, 2),)):
                reused = run_budgeted(p, root, algorithm, "reuse", target=0, max_instances=1,
                                      time_limit_ns=1_000_000_000, memory_limit_bytes=16 * 1024 * 1024)
                first = run_budgeted(p, root, algorithm, "restart", target=0, max_instances=1,
                                     time_limit_ns=1_000_000_000, memory_limit_bytes=16 * 1024 * 1024)
            self.assertEqual(reused["work"]["score_hashes"], 4)
            self.assertEqual(first["work"]["score_hashes"], 1)
            self.assertEqual(reused["instance_stops"], {"policy-restart": 1})
            ordered = list((BallSearch if algorithm == "ball" else MitmSearch)(p, ((1, 2),)).solutions())
            initial = ordered[0]
            transcript = hashlib.sha256(_score_message(p, seed, initial))
            for x in sorted(expected, key=lambda x: x[0]):
                if x != initial:
                    transcript.update(_score_message(p, seed, x))
            self.assertEqual(reused["transcript_sha256"], transcript.hexdigest())

    def test_time_and_memory_caps_cleanup_tracing(self):
        p, root = Profile(7, 1, 2, 4), bytes(32)
        ticks = itertools.count()
        timed = run_budgeted(p, root, "ball", "continue", time_limit_ns=1, clock=lambda: next(ticks))
        self.assertEqual(timed["reason"], "time-limit")
        self.assertEqual(timed["work"], {})
        self.assertFalse(tracemalloc.is_tracing())
        with patch("reference.budgets.tracemalloc.get_traced_memory", return_value=(2, 2)):
            memory = run_budgeted(p, root, "mitm", "continue", memory_limit_bytes=1)
        self.assertEqual(memory["reason"], "memory-limit")
        self.assertEqual(memory["peak_traced_bytes"], 2)
        self.assertFalse(tracemalloc.is_tracing())

    def test_invalid_budgets_and_existing_trace(self):
        p, root = Profile(7, 1, 2, 4), bytes(32)
        for options in ({"time_limit_ns": 0}, {"time_limit_ns": True}, {"time_limit_ns": 2_000_000_001},
                        {"memory_limit_bytes": 0}, {"memory_limit_bytes": 64 * 1024 * 1024 + 1},
                        {"max_instances": 4097}, {"target": True}):
            with self.assertRaises(ValueError):
                run_budgeted(p, root, "ball", "continue", **options)
        tracemalloc.start()
        try:
            with self.assertRaises(ValueError):
                run_budgeted(p, root, "ball", "continue")
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()

    def test_clock_failures_do_not_leave_global_tracing_enabled(self):
        p, root = Profile(7, 1, 2, 4), bytes(32)
        def broken():
            raise RuntimeError("clock failed")
        with self.assertRaisesRegex(RuntimeError, "clock failed"):
            run_budgeted(p, root, "ball", "continue", clock=broken)
        self.assertFalse(tracemalloc.is_tracing())
        ticks = iter((0, 1))
        def breaks_on_final_measurement():
            try:
                return next(ticks)
            except StopIteration:
                return broken()
        with self.assertRaisesRegex(RuntimeError, "clock failed"):
            run_budgeted(p, root, "ball", "continue", time_limit_ns=1,
                         clock=breaks_on_final_measurement)
        self.assertFalse(tracemalloc.is_tracing())


if __name__ == "__main__":
    unittest.main()
