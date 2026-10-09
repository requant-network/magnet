//! Independent small-coefficient search; bounded local protocol spec/23.
use sis_verifier::generator::Profile;
use std::io::{self, Read, Write};
use std::time::Instant;

const MAX_REQUEST: usize = 4128;
const MAX_RESPONSE: usize = 17764;

fn u32_at(bytes: &[u8], at: usize) -> u32 {
    u32::from_le_bytes(bytes[at..at + 4].try_into().expect("checked span"))
}

fn gcd(mut a: i32, mut b: i32) -> i32 {
    a = a.abs();
    b = b.abs();
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}

struct Pattern {
    weight: usize,
    values: [i32; 3],
    census: [u64; 3],
}

fn choose(m: usize, w: usize) -> usize {
    match w {
        1 => m,
        2 => m * (m - 1) / 2,
        3 if m >= 3 => m * (m - 1) * (m - 2) / 6,
        _ => 0,
    }
}

fn execute(bytes: &[u8]) -> Result<Vec<u8>, &'static str> {
    let begin = Instant::now();
    if bytes.len() < 32 || &bytes[..4] != b"SCP1" || bytes[21..24] != [0, 0, 0] {
        return Err("invalid SCP1 header");
    }
    let profile = Profile {
        q: u32_at(bytes, 4),
        n: u16::from_le_bytes(bytes[8..10].try_into().unwrap()),
        m: u16::from_le_bytes(bytes[10..12].try_into().unwrap()),
        b2: u64::from_le_bytes(bytes[12..20].try_into().unwrap()),
    };
    profile.validate()?;
    let (n, m, bound) = (usize::from(profile.n), usize::from(profile.m), bytes[20]);
    let (cap, proof_cap) = (u32_at(bytes, 24), u32_at(bytes, 28));
    if m > 16
        || profile.b2 > 12
        || !(1..=2).contains(&bound)
        || !(1..=20000).contains(&cap)
        || !(1..=256).contains(&proof_cap)
        || bytes.len() != 32 + 4 * n * m
    {
        return Err("SCP1 dimensions/caps/length");
    }
    // Check every residue before allocating the owned matrix.
    for offset in (32..bytes.len()).step_by(4) {
        if u32_at(bytes, offset) >= profile.q {
            return Err("noncanonical residue");
        }
    }
    let matrix: Vec<i64> = (32..bytes.len())
        .step_by(4)
        .map(|i| i64::from(u32_at(bytes, i)))
        .collect();
    let mut work = [0_u64; 13];
    work[11] = (n * m) as u64;
    work[12] = m as u64;
    let signed: Vec<i32> = (1..=i32::from(bound)).flat_map(|x| [x, -x]).collect();
    let mut patterns = Vec::new();
    let mut weights = [[0_u64; 3]; 3];
    for w in 1..=3.min(m) {
        for first in 1..=i32::from(bound) {
            let seconds: &[i32] = if w >= 2 { &signed } else { &[0] };
            let thirds: &[i32] = if w == 3 { &signed } else { &[0] };
            for &second in seconds {
                for &third in thirds {
                    work[0] += 1;
                    work[1] += w as u64;
                    let values = [first, second, third];
                    if values.iter().map(|x| i64::from(*x).pow(2)).sum::<i64>() <= profile.b2 as i64
                    {
                        let domain = choose(m, w) as u64;
                        weights[w - 1][0] += domain;
                        patterns.push(Pattern {
                            weight: w,
                            values,
                            census: [domain, 0, 0],
                        });
                    }
                }
            }
        }
    }
    let domain: u64 = weights.iter().map(|x| x[0]).sum();
    let mut proofs: Vec<Vec<i32>> = Vec::new();
    'search: for w in 1..=3.min(m) {
        for i in 0..m {
            let js: Vec<usize> = if w >= 2 {
                ((i + 1)..m).collect()
            } else {
                vec![i]
            };
            for j in js {
                let ks: Vec<usize> = if w == 3 {
                    ((j + 1)..m).collect()
                } else {
                    vec![j]
                };
                for k in ks {
                    let positions = [i, j, k];
                    for p in patterns.iter_mut().filter(|p| p.weight == w) {
                        if work[3] == u64::from(cap) {
                            break 'search;
                        }
                        work[2] += 1;
                        work[3] += 1;
                        weights[w - 1][1] += 1;
                        p.census[1] += 1;
                        let mut valid = true;
                        for row in 0..n {
                            let sum: i64 = (0..w)
                                .map(|a| matrix[row * m + positions[a]] * i64::from(p.values[a]))
                                .sum();
                            work[4] += w as u64;
                            work[5] += 1;
                            if sum % i64::from(profile.q) != 0 {
                                valid = false;
                                break;
                            }
                        }
                        if valid {
                            let mut vector = vec![0; m];
                            for a in 0..w {
                                vector[positions[a]] = p.values[a];
                            }
                            proofs.push(vector);
                            weights[w - 1][2] += 1;
                            p.census[2] += 1;
                            work[6] += 1;
                            work[7] += m as u64;
                            work[8] += w as u64;
                            let divisor = p.values[..w].iter().fold(0, |d, &x| gcd(d, x));
                            work[if divisor == 1 { 9 } else { 10 }] += 1;
                            if proofs.len() == proof_cap as usize {
                                break 'search;
                            }
                        }
                    }
                }
            }
        }
    }
    let exhausted = work[3] == domain;
    let reason = if proofs.len() == proof_cap as usize {
        1
    } else if !exhausted {
        2
    } else {
        3
    };
    let elapsed = u64::try_from(begin.elapsed().as_nanos()).map_err(|_| "timer overflow")?;
    let mut result = Vec::with_capacity(MAX_RESPONSE);
    result.extend_from_slice(b"SCR1");
    result.extend_from_slice(&[reason, u8::from(exhausted)]);
    result.extend_from_slice(&0_u16.to_le_bytes());
    result.extend_from_slice(&profile.m.to_le_bytes());
    result.extend_from_slice(&(patterns.len() as u16).to_le_bytes());
    result.extend_from_slice(&(proofs.len() as u32).to_le_bytes());
    result.extend_from_slice(&(domain as u32).to_le_bytes());
    result.extend_from_slice(&elapsed.to_le_bytes());
    for value in work {
        result.extend_from_slice(&value.to_le_bytes());
    }
    for weight in weights {
        for value in weight {
            result.extend_from_slice(&value.to_le_bytes());
        }
    }
    for pattern in patterns {
        result.push(pattern.weight as u8);
        for value in pattern.values {
            result.push(value as i8 as u8);
        }
        for value in pattern.census {
            result.extend_from_slice(&value.to_le_bytes());
        }
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
            return Err("SCP1 frame length".into());
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
        eprintln!("sis-coeff: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(m: u16, b2: u64, cap: u32, proofs: u32) -> Vec<u8> {
        let mut p = b"SCP1".to_vec();
        p.extend_from_slice(&17_u32.to_le_bytes());
        p.extend_from_slice(&1_u16.to_le_bytes());
        p.extend_from_slice(&m.to_le_bytes());
        p.extend_from_slice(&b2.to_le_bytes());
        p.extend_from_slice(&[2, 0, 0, 0]);
        p.extend_from_slice(&cap.to_le_bytes());
        p.extend_from_slice(&proofs.to_le_bytes());
        p.resize(32 + usize::from(m) * 4, 0);
        p
    }
    #[test]
    fn exact_limit_and_sequential_output_stop() {
        let r = execute(&request(1, 4, 2, 2)).unwrap();
        assert_eq!(&r[4..6], &[1, 1]);
        let r = execute(&request(16, 12, 20000, 1)).unwrap();
        assert_eq!(&r[4..6], &[1, 0]);
        assert_eq!(u32_at(&r, 16), 18912);
        assert_eq!(u64::from_le_bytes(r[52..60].try_into().unwrap()), 1);
    }
    #[test]
    fn invalid_input_and_nonunit_witness() {
        for (m, b2, cap, proofs) in [(17, 12, 1, 1), (2, 13, 1, 1), (1, 1, 0, 1), (1, 1, 1, 257)] {
            assert!(execute(&request(m, b2, cap, proofs)).is_err());
        }
        let mut p = request(2, 5, 20000, 256);
        p[32..36].copy_from_slice(&1_u32.to_le_bytes());
        p[36..40].copy_from_slice(&2_u32.to_le_bytes());
        let r = execute(&p).unwrap();
        assert_eq!(u32_at(&r, 12), 1);
        assert_eq!(&r[r.len() - 8..], &[2, 0, 0, 0, 255, 255, 255, 255]);
        p[21] = 1;
        assert!(execute(&p).is_err());
    }
}
