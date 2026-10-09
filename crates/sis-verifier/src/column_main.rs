//! Bounded, safe native column search. Wire contract: spec/19.
use sis_verifier::generator::Profile;
use std::io::{self, Read, Write};
use std::time::Instant;

const MAX_REQUEST: usize = 32 + 4 * 64 * 128;

fn u32_at(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(
        bytes[offset..offset + 4]
            .try_into()
            .expect("checked packet"),
    )
}

fn execute(bytes: &[u8]) -> Result<Vec<u8>, &'static str> {
    let begin = Instant::now();
    if bytes.len() < 32 || &bytes[..4] != b"CPS1" {
        return Err("bad CPS1 header");
    }
    let profile = Profile {
        q: u32_at(bytes, 4),
        n: u16::from_le_bytes(bytes[8..10].try_into().unwrap()),
        m: u16::from_le_bytes(bytes[10..12].try_into().unwrap()),
        b2: u64::from_le_bytes(bytes[12..20].try_into().unwrap()),
    };
    profile.validate()?;
    let (n, m) = (usize::from(profile.n), usize::from(profile.m));
    let (cap, proof_cap, width) = (u32_at(bytes, 20), u32_at(bytes, 24), u32_at(bytes, 28));
    if !(1..=16384).contains(&cap)
        || !(1..=256).contains(&proof_cap)
        || !(1..=4096).contains(&width)
    {
        return Err("column caps outside laboratory range");
    }
    if bytes.len() != 32 + 4 * n * m {
        return Err("CPS1 length mismatch");
    }
    let mut columns = vec![0_i64; n * m];
    for row in 0..n {
        for col in 0..m {
            let residue = u32_at(bytes, 32 + 4 * (row * m + col));
            if residue >= profile.q {
                return Err("noncanonical matrix residue");
            }
            columns[col * n + row] = i64::from(residue);
        }
    }
    let singles = (0..m).map(|i| (i, i, 0_i32));
    let pairs = (0..m).flat_map(|i| ((i + 1)..m).flat_map(move |j| [(i, j, 1), (i, j, -1)]));
    let mut supports = singles.chain(pairs);
    let domain = if profile.b2 == 1 { m } else { m * m };
    let end = domain.min(cap as usize);
    let mut proofs: Vec<Vec<i32>> = Vec::new();
    let (mut checked, mut batches, mut accepted, mut rows) = (0_u64, 0_u64, 0_u64, 0_u64);
    let mut reason = 3_u8;
    while (checked as usize) < end {
        let count = (width as usize).min(end - checked as usize);
        for (first, second, sign) in supports.by_ref().take(count) {
            let mut valid = true;
            for row in 0..n {
                rows += 1;
                if (columns[first * n + row] + i64::from(sign) * columns[second * n + row])
                    % i64::from(profile.q)
                    != 0
                {
                    valid = false;
                    break;
                }
            }
            if valid {
                accepted += 1;
                if proofs.len() < proof_cap as usize {
                    let mut vector = vec![0; m];
                    vector[first] = 1;
                    if sign != 0 {
                        vector[second] = sign;
                    }
                    proofs.push(vector);
                }
            }
        }
        checked += count as u64;
        batches += 1;
        if proofs.len() == proof_cap as usize {
            reason = 1;
            break;
        }
    }
    let exhausted = checked == domain as u64;
    if reason != 1 && !exhausted {
        reason = 2;
    }
    let elapsed = u64::try_from(begin.elapsed().as_nanos()).map_err(|_| "timer overflow")?;
    let mut result = Vec::with_capacity(60 + proofs.len() * m * 4);
    result.extend_from_slice(b"CSR1");
    result.extend_from_slice(&[
        reason,
        u8::from(exhausted),
        u8::from(exhausted && accepted == proofs.len() as u64),
        0,
    ]);
    result.extend_from_slice(&profile.m.to_le_bytes());
    result.extend_from_slice(&0_u16.to_le_bytes());
    result.extend_from_slice(&(proofs.len() as u32).to_le_bytes());
    result.extend_from_slice(&(domain as u32).to_le_bytes());
    for value in [elapsed, checked, batches, accepted, rows] {
        result.extend_from_slice(&value.to_le_bytes());
    }
    for vector in proofs {
        for value in vector {
            result.extend_from_slice(&value.to_le_bytes());
        }
    }
    Ok(result)
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut input = io::stdin().lock();
    let mut output = io::BufWriter::new(io::stdout().lock());
    loop {
        let mut size = [0_u8; 4];
        if input.read(&mut size[..1])? == 0 {
            return Ok(());
        }
        input.read_exact(&mut size[1..])?;
        let length = u32::from_le_bytes(size) as usize;
        if !(32..=MAX_REQUEST).contains(&length) {
            return Err("CPS1 frame length".into());
        }
        let mut bytes = vec![0; length];
        input.read_exact(&mut bytes)?;
        let result = execute(&bytes)?;
        output.write_all(&(result.len() as u32).to_le_bytes())?;
        output.write_all(&result)?;
        output.flush()?;
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("sis-column: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(m: u16, b2: u64, cap: u32, proofs: u32, width: u32) -> Vec<u8> {
        let mut bytes = b"CPS1".to_vec();
        bytes.extend_from_slice(&7_u32.to_le_bytes());
        bytes.extend_from_slice(&1_u16.to_le_bytes());
        bytes.extend_from_slice(&m.to_le_bytes());
        bytes.extend_from_slice(&b2.to_le_bytes());
        for v in [cap, proofs, width] {
            bytes.extend_from_slice(&v.to_le_bytes());
        }
        bytes.resize(32 + usize::from(m) * 4, 0);
        bytes
    }
    #[test]
    fn paid_tail_and_reason_precedence() {
        let out = execute(&request(3, 2, 9, 1, 9)).unwrap();
        assert_eq!(&out[4..8], &[1, 1, 0, 0]);
        assert_eq!(u64::from_le_bytes(out[28..36].try_into().unwrap()), 9);
        assert_eq!(u64::from_le_bytes(out[44..52].try_into().unwrap()), 9);
        let complete = execute(&request(3, 1, 3, 3, 2)).unwrap();
        assert_eq!(&complete[4..8], &[1, 1, 1, 0]);
    }
    #[test]
    fn reject_noncanonical_and_trailing() {
        let mut packet = request(1, 1, 1, 1, 1);
        packet[32..36].copy_from_slice(&7_u32.to_le_bytes());
        assert!(execute(&packet).is_err());
        packet[32] = 0;
        packet.push(0);
        assert!(execute(&packet).is_err());
        assert!(execute(&request(129, 2, 1, 1, 1)).is_err());
        assert!(execute(&request(1, 1, 0, 1, 1)).is_err());
    }
}
