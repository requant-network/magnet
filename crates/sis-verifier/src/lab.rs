//! Bounded local MGL1 request dispatch (spec/04); not a network service.

use crate::{
    generator::{Profile, expand_matrix},
    header::{CONTEXT_SIZE, ExpectedContext, LabHeader, verify_proof},
    rules, score, sha256, shake,
};

pub const MAX_REQUEST: usize = 9 + shake::MAX_INPUT;

pub fn respond(request: &[u8]) -> Result<Vec<u8>, &'static str> {
    if !(5..=MAX_REQUEST).contains(&request.len()) || &request[..4] != b"MGL1" {
        return Err("request length/version");
    }
    match request[4] {
        0 if request.len() >= 9 => {
            let length = u32::from_le_bytes(request[5..9].try_into().unwrap()) as usize;
            shake::shake256(&request[9..], length)
        }
        1 if request.len() == 53 => {
            let matrix = expand_matrix(Profile::decode(&request[5..21])?, &request[21..])?;
            Ok(matrix.into_iter().flat_map(u32::to_le_bytes).collect())
        }
        2 => {
            let (seed, matrix) = LabHeader::decode(&request[5..])?.derive()?;
            let mut output = seed.to_vec();
            output.extend(matrix.into_iter().flat_map(u32::to_le_bytes));
            Ok(output)
        }
        3 if request.len() >= 5 + CONTEXT_SIZE => {
            let context = ExpectedContext::decode(&request[5..5 + CONTEXT_SIZE])?;
            Ok(vec![u8::from(verify_proof(
                &request[5 + CONTEXT_SIZE..],
                &context,
            ))])
        }
        4 => Ok(sha256::digest(&request[5..])?.to_vec()),
        5 if request.len() >= 5 + CONTEXT_SIZE + 33 => {
            let context = ExpectedContext::decode(&request[5..5 + CONTEXT_SIZE])?;
            let target = score::Target::decode(&request[5 + CONTEXT_SIZE..5 + CONTEXT_SIZE + 33])?;
            Ok(vec![u8::from(score::verify_scored_proof(
                &request[5 + CONTEXT_SIZE + 33..],
                &context,
                target,
            ))])
        }
        6 if request.len() >= 7 => {
            let length = usize::from(u16::from_le_bytes(request[5..7].try_into().unwrap()));
            let wire = request.get(7..7 + length).ok_or("rules truncated")?;
            let rules = rules::LabRules::decode(wire)?;
            Ok(vec![u8::from(rules.admit(&request[7 + length..]))])
        }
        _ => Err("unknown mode or malformed request"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reject_unbounded_and_unknown_requests() {
        for request in [
            b"MGL1\x07".to_vec(),
            b"MGL1\x00".to_vec(),
            b"MGL1\x00\xff\xff\xff\xff".to_vec(),
            vec![0; MAX_REQUEST + 1],
        ] {
            assert!(respond(&request).is_err());
        }
        assert_eq!(respond(b"MGL1\x00\0\0\0\0").unwrap(), []);
    }
}
