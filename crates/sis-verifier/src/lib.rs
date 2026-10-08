//! Independent SIS laboratory verifier, generator and research header binding.
//! Experimental fixed-policy chain validation; no calibrated work or network consensus.

pub const MAX_PACKET: usize = 20 + 4 * 64 * 128 + 4 * 128;

pub mod block;
pub mod chain;
pub mod generator;
pub mod header;
pub mod lab;
pub mod rules;
pub mod score;
pub mod search;
pub mod sha256;
pub mod shake;

fn is_prime(q: u32) -> bool {
    if !(2..=65_521).contains(&q) {
        return false;
    }
    let mut divisor = 2;
    while divisor * divisor <= q {
        if q.is_multiple_of(divisor) {
            return false;
        }
        divisor += 1;
    }
    true
}

/// Reject malformed encodings before allocating or multiplying coordinates.
pub fn verify_packet(packet: &[u8]) -> bool {
    if !(20..=MAX_PACKET).contains(&packet.len()) || &packet[..4] != b"SIS1" {
        return false;
    }
    let q = u32::from_le_bytes(packet[4..8].try_into().unwrap());
    let n = u16::from_le_bytes(packet[8..10].try_into().unwrap()) as usize;
    let m = u16::from_le_bytes(packet[10..12].try_into().unwrap()) as usize;
    let b2 = u64::from_le_bytes(packet[12..20].try_into().unwrap());
    if !is_prime(q) || !(1..=64).contains(&n) || !(1..=128).contains(&m) {
        return false;
    }
    if b2 == 0 || b2 >= u64::from(q) * u64::from(q) {
        return false;
    }
    if packet.len() != 20 + 4 * n * m + 4 * m {
        return false;
    }

    let vector_start = 20 + 4 * n * m;
    let mut vector = Vec::with_capacity(m);
    let mut norm = 0_u64;
    let mut first_nonzero = None;
    for word in packet[vector_start..].as_chunks::<4>().0 {
        let coordinate = i64::from(i32::from_le_bytes(*word));
        first_nonzero = first_nonzero.or_else(|| (coordinate != 0).then_some(coordinate));
        // One i32 square fits i64. Bound each running sum before processing more.
        let square = (coordinate * coordinate) as u64;
        if square > b2 - norm {
            return false;
        }
        norm += square;
        vector.push(coordinate);
    }
    if !first_nonzero.is_some_and(|x| x > 0) {
        return false;
    }

    for row in packet[20..vector_start].chunks_exact(4 * m) {
        let mut residue = 0_i64;
        for (word, coordinate) in row.as_chunks::<4>().0.iter().zip(&vector) {
            let entry = u32::from_le_bytes(*word);
            if entry >= q {
                return false;
            }
            // Validated norm implies |coordinate| < q <= 65521.
            residue = (residue + i64::from(entry) * coordinate).rem_euclid(i64::from(q));
        }
        if residue != 0 {
            return false;
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    fn example(x: [i32; 2], b2: u64) -> Vec<u8> {
        let mut packet = b"SIS1".to_vec();
        packet.extend(7_u32.to_le_bytes());
        packet.extend(1_u16.to_le_bytes());
        packet.extend(2_u16.to_le_bytes());
        packet.extend(b2.to_le_bytes());
        packet.extend(1_u32.to_le_bytes());
        packet.extend(2_u32.to_le_bytes());
        for coordinate in x {
            packet.extend(coordinate.to_le_bytes());
        }
        packet
    }

    #[test]
    fn arithmetic_boundaries() {
        assert!(verify_packet(&example([2, -1], 5)));
        for (x, b2) in [
            ([0, 0], 5),
            ([-2, 1], 5),
            ([2, -1], 4),
            ([1, 0], 5),
            ([7, 0], 48),
            ([i32::MIN, i32::MAX], 5),
        ] {
            assert!(!verify_packet(&example(x, b2)));
        }
    }

    #[test]
    fn malformed_encodings() {
        let valid = example([2, -1], 5);
        for length in 0..valid.len() {
            assert!(!verify_packet(&valid[..length]));
        }
        let mut extra = valid.clone();
        extra.push(0);
        assert!(!verify_packet(&extra));
        for (offset, bytes) in [(4, 4_u32.to_le_bytes()), (20, 7_u32.to_le_bytes())] {
            let mut changed = valid.clone();
            changed[offset..offset + 4].copy_from_slice(&bytes);
            assert!(!verify_packet(&changed));
        }
        assert!(!verify_packet(&vec![0; MAX_PACKET + 1]));
    }

    #[test]
    fn prime_bounds() {
        for q in [0, 1, 4, 9, 65_535, u32::MAX] {
            assert!(!is_prime(q));
        }
        for q in [2, 3, 7, 65_521] {
            assert!(is_prime(q));
        }
    }
}
