//! Bounded exact CPU baselines on supplied lab matrices; no hashing or consensus.

use std::mem::size_of;

pub const MAX_NODES: u64 = 50_000_000;
pub const MAX_HALF_BOX: u64 = 1_000_000;
pub const MAX_TABLE: usize = 1_000_000;
pub const MAX_PAIRS: u64 = 10_000_000;
pub const MAX_PROOFS: usize = 100_000;

#[derive(Debug)]
pub struct Instance {
    q: u32,
    n: usize,
    m: usize,
    b2: u64,
    matrix: Vec<u32>,
}

impl Instance {
    /// Reuse SIS1 encoding, but require the placeholder vector to be all zero.
    pub fn decode(packet: &[u8]) -> Result<Self, &'static str> {
        if !(20..=crate::MAX_PACKET).contains(&packet.len()) || &packet[..4] != b"SIS1" {
            return Err("invalid search instance encoding");
        }
        let q = u32::from_le_bytes(packet[4..8].try_into().unwrap());
        let n = u16::from_le_bytes(packet[8..10].try_into().unwrap()) as usize;
        let m = u16::from_le_bytes(packet[10..12].try_into().unwrap()) as usize;
        let b2 = u64::from_le_bytes(packet[12..20].try_into().unwrap());
        if !crate::is_prime(q)
            || !(1..=64).contains(&n)
            || !(1..=128).contains(&m)
            || b2 == 0
            || b2 >= u64::from(q) * u64::from(q)
        {
            return Err("invalid search profile");
        }
        if packet.len() != 20 + 4 * n * m + 4 * m {
            return Err("incorrect search instance length");
        }
        let end = 20 + 4 * n * m;
        if packet[end..].iter().any(|b| *b != 0) {
            return Err("search instance must not supply a known vector");
        }
        let matrix: Vec<u32> = packet[20..end]
            .as_chunks::<4>()
            .0
            .iter()
            .map(|word| u32::from_le_bytes(*word))
            .collect();
        if matrix.iter().any(|a| *a >= q) {
            return Err("noncanonical matrix entry");
        }
        Ok(Self {
            q,
            n,
            m,
            b2,
            matrix,
        })
    }

    pub fn width(&self) -> usize {
        self.m
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Limits {
    pub nodes: u64,
    pub table: usize,
    pub pairs: u64,
    pub proofs: usize,
}

impl Limits {
    pub fn validate(self) -> Result<(), &'static str> {
        if !(1..=MAX_NODES).contains(&self.nodes)
            || !(1..=MAX_TABLE).contains(&self.table)
            || !(1..=MAX_PAIRS).contains(&self.pairs)
            || !(1..=MAX_PROOFS).contains(&self.proofs)
        {
            return Err("invalid native search limits");
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Stop {
    Exhausted = 0,
    Nodes = 1,
    Table = 2,
    Pairs = 3,
    Proofs = 4,
    HalfBox = 5,
}

#[derive(Default, Debug, PartialEq, Eq)]
pub struct Work {
    pub nodes: u64,
    pub left: u64,
    pub right: u64,
    pub norm_terms: u64,
    pub matrix_terms: u64,
    pub row_reductions: u64,
    pub leaves: u64,
    pub table_entries: u64,
    pub pairs: u64,
    pub proofs: u64,
}

impl Work {
    pub fn words(&self) -> [u64; 10] {
        [
            self.nodes,
            self.left,
            self.right,
            self.norm_terms,
            self.matrix_terms,
            self.row_reductions,
            self.leaves,
            self.table_entries,
            self.pairs,
            self.proofs,
        ]
    }
}

#[derive(Debug)]
pub struct Report {
    pub stop: Stop,
    pub work: Work,
    pub proofs: Vec<Vec<i32>>,
    /// Peak charged Vec payload capacities, not allocator/RSS/stack measurement.
    pub owned_capacity_bytes: u64,
}

impl Report {
    fn new() -> Self {
        Self {
            stop: Stop::Exhausted,
            work: Work::default(),
            proofs: Vec::new(),
            owned_capacity_bytes: 0,
        }
    }
    fn emit(&mut self, vector: Vec<i32>, limit: usize) -> bool {
        if self.proofs.len() == limit {
            self.stop = Stop::Proofs;
            return false;
        }
        self.proofs.push(vector);
        self.work.proofs += 1;
        true
    }
    fn proof_bytes(&self) -> u64 {
        (self.proofs.capacity() * size_of::<Vec<i32>>()
            + self
                .proofs
                .iter()
                .map(|x| x.capacity() * size_of::<i32>())
                .sum::<usize>()) as u64
    }
    fn charge(&mut self, base: u64) {
        self.owned_capacity_bytes = self.owned_capacity_bytes.max(base + self.proof_bytes());
    }
}

struct Ball<'a> {
    instance: &'a Instance,
    limits: Limits,
    vector: Vec<i32>,
    residues: Vec<u32>,
    report: Report,
}

impl Ball<'_> {
    fn walk(&mut self, column: usize, remaining: u64, nonzero: bool) -> bool {
        if column == self.instance.m {
            self.report.work.leaves += 1;
            if !nonzero || self.residues.iter().any(|r| *r != 0) {
                return true;
            }
            if self.report.proofs.len() == self.limits.proofs {
                self.report.stop = Stop::Proofs;
                return false;
            }
            return self.report.emit(self.vector.clone(), self.limits.proofs);
        }
        // Fixed stack snapshots avoid per-prefix heap allocation. Depth <= 128.
        let mut previous = [0_u32; 64];
        previous[..self.instance.n].copy_from_slice(&self.residues);
        let radius = remaining.isqrt() as i32;
        for value in (if nonzero { -radius } else { 0 })..=radius {
            if self.report.work.nodes == self.limits.nodes {
                self.report.stop = Stop::Nodes;
                return false;
            }
            self.report.work.nodes += 1;
            self.report.work.norm_terms += 1;
            self.vector[column] = value;
            for (row, old) in previous[..self.instance.n].iter().enumerate() {
                let a = self.instance.matrix[row * self.instance.m + column];
                self.residues[row] = (i64::from(*old) + i64::from(a) * i64::from(value))
                    .rem_euclid(i64::from(self.instance.q))
                    as u32;
            }
            self.report.work.matrix_terms += self.instance.n as u64;
            self.report.work.row_reductions += self.instance.n as u64;
            let square = (i64::from(value) * i64::from(value)) as u64;
            if !self.walk(column + 1, remaining - square, nonzero || value != 0) {
                return false;
            }
        }
        true
    }
}

pub fn ball(instance: &Instance, limits: Limits) -> Result<Report, &'static str> {
    limits.validate()?;
    let mut search = Ball {
        instance,
        limits,
        vector: vec![0; instance.m],
        residues: vec![0; instance.n],
        report: Report::new(),
    };
    search.walk(0, instance.b2, false);
    let base = ((instance.matrix.capacity() + search.residues.capacity()) * size_of::<u32>()
        + search.vector.capacity() * size_of::<i32>()) as u64;
    search.report.charge(base);
    Ok(search.report)
}

struct Entry {
    syndrome: Vec<u32>,
    vector: Vec<i32>,
    norm: u64,
}

fn advance(vector: &mut [i32], radius: i32) -> bool {
    for value in vector.iter_mut().rev() {
        if *value < radius {
            *value += 1;
            return true;
        }
        *value = -radius;
    }
    false
}

fn syndrome(instance: &Instance, start: usize, vector: &[i32], work: &mut Work) -> Vec<u32> {
    let result = (0..instance.n)
        .map(|row| {
            // <= 128 terms, each absolute product < 65521^2; i64 remains bounded.
            vector
                .iter()
                .enumerate()
                .map(|(i, x)| {
                    i64::from(instance.matrix[row * instance.m + start + i]) * i64::from(*x)
                })
                .sum::<i64>()
                .rem_euclid(i64::from(instance.q)) as u32
        })
        .collect();
    work.matrix_terms += (instance.n * vector.len()) as u64;
    work.row_reductions += instance.n as u64;
    result
}

pub fn mitm(instance: &Instance, limits: Limits) -> Result<Report, &'static str> {
    mitm_inner(instance, limits, false)
}

/// Budgeted MITM: every left/right proposal and join pair shares one node cap.
/// Legacy mode keeps its frozen separate-counter semantics for old surveys.
pub fn mitm_budgeted(instance: &Instance, limits: Limits) -> Result<Report, &'static str> {
    mitm_inner(instance, limits, true)
}

fn charge_node(report: &mut Report, limit: u64) -> bool {
    if report.work.nodes == limit {
        report.stop = Stop::Nodes;
        return false;
    }
    report.work.nodes += 1;
    true
}

fn mitm_inner(instance: &Instance, limits: Limits, bounded: bool) -> Result<Report, &'static str> {
    limits.validate()?;
    let mut report = Report::new();
    report.charge((instance.matrix.capacity() * size_of::<u32>()) as u64);
    let split = instance.m / 2;
    let radius = instance.b2.isqrt() as i32;
    for width in [split, instance.m - split] {
        let mut count = 1_u64;
        for _ in 0..width {
            count = count.saturating_mul((2 * radius + 1) as u64);
            if count > MAX_HALF_BOX {
                report.stop = Stop::HalfBox;
                return Ok(report);
            }
        }
    }
    let mut table = Vec::<Entry>::new();
    let mut children_bytes = 0_usize;
    let mut left = vec![-radius; split];
    loop {
        if bounded && !charge_node(&mut report, limits.nodes) {
            break;
        }
        report.work.left += 1;
        report.work.norm_terms += split as u64;
        let norm = left
            .iter()
            .map(|x| (i64::from(*x) * i64::from(*x)) as u64)
            .sum::<u64>();
        if norm <= instance.b2 && left.iter().find(|x| **x != 0).is_none_or(|x| *x > 0) {
            if table.len() == limits.table {
                report.stop = Stop::Table;
                break;
            }
            let entry = Entry {
                syndrome: syndrome(instance, 0, &left, &mut report.work),
                vector: left.clone(),
                norm,
            };
            children_bytes += entry.syndrome.capacity() * size_of::<u32>()
                + entry.vector.capacity() * size_of::<i32>();
            table.push(entry);
            report.work.table_entries += 1;
        }
        if !advance(&mut left, radius) {
            break;
        }
    }
    let build_bytes = instance.matrix.capacity() * size_of::<u32>()
        + left.capacity() * size_of::<i32>()
        + table.capacity() * size_of::<Entry>()
        + children_bytes;
    report.charge(build_bytes as u64);
    if report.stop != Stop::Exhausted {
        return Ok(report);
    }
    drop(left);
    table.sort_unstable_by(|a, b| a.syndrome.cmp(&b.syndrome));
    let mut right = vec![-radius; instance.m - split];
    let base = instance.matrix.capacity() * size_of::<u32>()
        + table.capacity() * size_of::<Entry>()
        + children_bytes
        + right.capacity() * size_of::<i32>()
        + instance.n * size_of::<u32>();
    'search: loop {
        if bounded && !charge_node(&mut report, limits.nodes) {
            break;
        }
        report.work.right += 1;
        report.work.norm_terms += right.len() as u64;
        let norm = right
            .iter()
            .map(|x| (i64::from(*x) * i64::from(*x)) as u64)
            .sum::<u64>();
        if norm <= instance.b2 {
            let mut opposite = syndrome(instance, split, &right, &mut report.work);
            for value in &mut opposite {
                *value = (instance.q - *value) % instance.q;
            }
            let begin = table.partition_point(|entry| entry.syndrome < opposite);
            for entry in table[begin..]
                .iter()
                .take_while(|entry| entry.syndrome == opposite)
            {
                if report.work.pairs == limits.pairs {
                    report.stop = Stop::Pairs;
                    break 'search;
                }
                if bounded && !charge_node(&mut report, limits.nodes) {
                    break 'search;
                }
                report.work.pairs += 1;
                if norm + entry.norm == 0 || norm + entry.norm > instance.b2 {
                    continue;
                }
                if entry
                    .vector
                    .iter()
                    .chain(&right)
                    .find(|x| **x != 0)
                    .is_some_and(|x| *x > 0)
                {
                    if report.proofs.len() == limits.proofs {
                        report.stop = Stop::Proofs;
                        break 'search;
                    }
                    let vector = entry.vector.iter().chain(&right).copied().collect();
                    report.emit(vector, limits.proofs);
                }
            }
        }
        if !advance(&mut right, radius) {
            break;
        }
    }
    report.charge(base as u64);
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn instance(q: u32, n: usize, m: usize, b2: u64, matrix: Vec<u32>) -> Instance {
        Instance {
            q,
            n,
            m,
            b2,
            matrix,
        }
    }
    fn limits() -> Limits {
        Limits {
            nodes: MAX_NODES,
            table: MAX_TABLE,
            pairs: MAX_PAIRS,
            proofs: MAX_PROOFS,
        }
    }

    #[test]
    fn mitm_shared_proposal_pair_budget_and_exact_completion() {
        let a = instance(7, 1, 4, 5, vec![0; 4]);
        let legacy = mitm(&a, limits()).unwrap();
        let full = mitm_budgeted(&a, limits()).unwrap();
        assert_eq!(full.stop, Stop::Exhausted);
        assert_eq!(full.proofs, legacy.proofs);
        assert_eq!(legacy.work.nodes, 0);
        assert_eq!(
            full.work.nodes,
            full.work.left + full.work.right + full.work.pairs
        );
        for ceiling in [1, full.work.left, full.work.left + 1, full.work.nodes - 1] {
            let partial = mitm_budgeted(
                &a,
                Limits {
                    nodes: ceiling,
                    ..limits()
                },
            )
            .unwrap();
            assert_eq!(partial.stop, Stop::Nodes);
            assert_eq!(partial.work.nodes, ceiling);
            assert_eq!(
                partial.work.nodes,
                partial.work.left + partial.work.right + partial.work.pairs
            );
        }
        let exact = mitm_budgeted(
            &a,
            Limits {
                nodes: full.work.nodes,
                ..limits()
            },
        )
        .unwrap();
        assert_eq!(exact.stop, Stop::Exhausted);
        assert_eq!(exact.proofs, full.proofs);
    }

    #[test]
    fn maximum_modulus_and_norm() {
        let q = 65521_u32;
        let a = instance(q, 1, 1, u64::from(q) * u64::from(q) - 1, vec![q - 1]);
        let b = ball(&a, limits()).unwrap();
        let s = mitm(&a, limits()).unwrap();
        assert_eq!(b.stop, Stop::Exhausted);
        assert_eq!(s.stop, Stop::Exhausted);
        assert!(b.proofs.is_empty());
        assert!(s.proofs.is_empty());
        assert_eq!(b.work.nodes, u64::from(q));
        assert_eq!(s.work.right, 2 * u64::from(q) - 1);
        let zero = instance(q, 1, 1, a.b2, vec![0]);
        let report = ball(&zero, limits()).unwrap();
        assert_eq!(report.proofs.len(), (q - 1) as usize);
        assert_eq!(report.proofs.last().unwrap(), &vec![65520]);
    }

    #[test]
    fn exactly_sufficient_caps_still_exhaust() {
        let a = instance(7, 1, 4, 5, vec![0; 4]);
        let b = ball(&a, limits()).unwrap();
        let s = mitm(&a, limits()).unwrap();
        let bounded_ball = ball(
            &a,
            Limits {
                nodes: b.work.nodes,
                proofs: b.proofs.len(),
                ..limits()
            },
        )
        .unwrap();
        let bounded_mitm = mitm(
            &a,
            Limits {
                table: s.work.table_entries as usize,
                pairs: s.work.pairs,
                proofs: s.proofs.len(),
                ..limits()
            },
        )
        .unwrap();
        assert_eq!(bounded_ball.stop, Stop::Exhausted);
        assert_eq!(bounded_mitm.stop, Stop::Exhausted);
        assert_eq!(bounded_ball.proofs, b.proofs);
        assert_eq!(bounded_mitm.proofs, s.proofs);
    }

    #[test]
    fn zero_columns_collisions_and_odd_width() {
        for m in 1..=5 {
            let a = instance(7, 2, m, 4, vec![0; 2 * m]);
            let mut b = ball(&a, limits()).unwrap().proofs;
            let mut s = mitm(&a, limits()).unwrap().proofs;
            b.sort();
            s.sort();
            assert_eq!(b, s);
            assert!(!b.contains(&vec![0; m]));
        }
    }
    #[test]
    fn wrap_norm_and_limits() {
        let a = instance(7, 1, 3, 5, vec![1, 2, 3]);
        for solve in [ball, mitm] {
            let r = solve(&a, limits()).unwrap();
            assert!(r.proofs.contains(&vec![2, -1, 0]));
            assert!(r.proofs.contains(&vec![1, 0, 2]));
            assert_eq!(r.stop, Stop::Exhausted);
            assert_eq!(
                solve(
                    &a,
                    Limits {
                        proofs: 1,
                        ..limits()
                    }
                )
                .unwrap()
                .stop,
                Stop::Proofs
            );
        }
        assert_eq!(
            ball(
                &a,
                Limits {
                    nodes: 1,
                    ..limits()
                }
            )
            .unwrap()
            .stop,
            Stop::Nodes
        );
        assert_eq!(
            mitm(
                &a,
                Limits {
                    table: 1,
                    ..limits()
                }
            )
            .unwrap()
            .stop,
            Stop::Table
        );
        assert_eq!(
            mitm(
                &instance(7, 1, 4, 4, vec![0; 4]),
                Limits {
                    pairs: 1,
                    ..limits()
                }
            )
            .unwrap()
            .stop,
            Stop::Pairs
        );
        assert_eq!(
            mitm(&instance(7, 1, 128, 4, vec![0; 128]), limits())
                .unwrap()
                .stop,
            Stop::HalfBox
        );
        assert!(
            ball(
                &a,
                Limits {
                    nodes: 0,
                    ..limits()
                }
            )
            .is_err()
        );
    }
}
