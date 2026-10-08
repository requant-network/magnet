//! Bounded local search protocol. No network, key material or block consensus.
use sis_verifier::search::{self, Instance, Limits, Report};
use std::io::{self, Read, Write};
use std::time::Instant;

const HEADER: usize = 36;
const MAX_FRAME: usize = HEADER + sis_verifier::MAX_PACKET;

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn execute(request: &[u8]) -> io::Result<Vec<u8>> {
    if request.len() < HEADER || &request[..4] != b"NAT1" || request[5..8] != [0; 3] {
        return Err(invalid("invalid request header"));
    }
    let solve = match request[4] {
        1 => search::ball,
        2 => search::mitm,
        _ => return Err(invalid("unknown search mode")),
    };
    let limits = Limits {
        nodes: u64::from_le_bytes(request[8..16].try_into().unwrap()),
        table: u32::from_le_bytes(request[16..20].try_into().unwrap()) as usize,
        pairs: u64::from_le_bytes(request[20..28].try_into().unwrap()),
        proofs: u32::from_le_bytes(request[28..32].try_into().unwrap()) as usize,
    };
    limits.validate().map_err(invalid)?;
    let repeats = u32::from_le_bytes(request[32..36].try_into().unwrap());
    if !(1..=9).contains(&repeats) {
        return Err(invalid("repeats outside laboratory budget"));
    }
    let instance = Instance::decode(&request[HEADER..]).map_err(invalid)?;
    let mut last: Option<Report> = None;
    let mut times = Vec::new();
    for _ in 0..repeats {
        let start = Instant::now();
        let result = solve(&instance, limits).map_err(invalid)?;
        times.push(
            u64::try_from(start.elapsed().as_nanos()).map_err(|_| invalid("timer overflow"))?,
        );
        if let Some(previous) = &last
            && (previous.stop != result.stop
                || previous.work != result.work
                || previous.proofs != result.proofs)
        {
            return Err(invalid("nondeterministic search result"));
        }
        last = Some(result);
    }
    let result = last.unwrap();
    let mut response = Vec::new();
    response.extend_from_slice(b"NSR1");
    response.extend_from_slice(&[result.stop as u8, 0, 0, 0]);
    response.extend_from_slice(&(instance.width() as u16).to_le_bytes());
    response.extend_from_slice(&[0, 0]);
    response.extend_from_slice(&(result.proofs.len() as u32).to_le_bytes());
    response.extend_from_slice(&repeats.to_le_bytes());
    response.extend_from_slice(&result.owned_capacity_bytes.to_le_bytes());
    for value in result.work.words() {
        response.extend_from_slice(&value.to_le_bytes());
    }
    for value in times {
        response.extend_from_slice(&value.to_le_bytes());
    }
    for vector in result.proofs {
        for value in vector {
            response.extend_from_slice(&value.to_le_bytes());
        }
    }
    Ok(response)
}

fn run() -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut length = [0_u8; 4];
        if input.read(&mut length[..1])? == 0 {
            return Ok(());
        }
        input.read_exact(&mut length[1..])?;
        let size = u32::from_le_bytes(length) as usize;
        if size > MAX_FRAME {
            return Err(invalid("request frame exceeds laboratory budget"));
        }
        let mut request = vec![0; size];
        input.read_exact(&mut request)?;
        let response = execute(&request)?;
        output.write_all(&(response.len() as u32).to_le_bytes())?;
        output.write_all(&response)?;
        output.flush()?;
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("sis-search: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn malformed_headers_fail_before_search() {
        assert!(execute(b"").is_err());
        assert!(execute(b"NAT1").is_err());
        let mut request = vec![0; HEADER];
        request[..4].copy_from_slice(b"NAT1");
        request[4] = 3;
        assert!(execute(&request).is_err());
        request[4] = 1;
        request[8..16].copy_from_slice(&1_u64.to_le_bytes());
        request[16..20].copy_from_slice(&1_u32.to_le_bytes());
        request[20..28].copy_from_slice(&1_u64.to_le_bytes());
        request[28..32].copy_from_slice(&1_u32.to_le_bytes());
        request[32..36].copy_from_slice(&10_u32.to_le_bytes());
        assert!(execute(&request).is_err());
    }
}
