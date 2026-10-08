//! Research-only header binding. Context must come from the trusted caller.

use crate::{
    generator::{Profile, expand_matrix},
    shake::shake256,
    verify_packet,
};

pub const HEADER_SIZE: usize = 140;
pub const CONTEXT_SIZE: usize = 88;
pub const MAX_PROOF: usize = HEADER_SIZE + 4 * 128;
const DOMAIN: &[u8] = b"MagnetNetwork/SIS-LAB/header-seed/v1\0";

#[derive(Debug, PartialEq, Eq)]
pub struct LabHeader {
    pub network: [u8; 32],
    pub parent: [u8; 32],
    pub payload: [u8; 32],
    pub height: u64,
    pub timestamp: u64,
    pub nonce: u64,
    pub profile: Profile,
}

impl LabHeader {
    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        if bytes.len() != HEADER_SIZE || &bytes[..4] != b"MGH1" {
            return Err("header length/version");
        }
        Ok(Self {
            network: bytes[4..36].try_into().unwrap(),
            parent: bytes[36..68].try_into().unwrap(),
            payload: bytes[68..100].try_into().unwrap(),
            height: u64::from_le_bytes(bytes[100..108].try_into().unwrap()),
            timestamp: u64::from_le_bytes(bytes[108..116].try_into().unwrap()),
            nonce: u64::from_le_bytes(bytes[116..124].try_into().unwrap()),
            profile: Profile::decode(&bytes[124..])?,
        })
    }

    pub fn encode(&self) -> Result<[u8; HEADER_SIZE], &'static str> {
        let mut bytes = [0; HEADER_SIZE];
        bytes[..4].copy_from_slice(b"MGH1");
        bytes[4..36].copy_from_slice(&self.network);
        bytes[36..68].copy_from_slice(&self.parent);
        bytes[68..100].copy_from_slice(&self.payload);
        bytes[100..108].copy_from_slice(&self.height.to_le_bytes());
        bytes[108..116].copy_from_slice(&self.timestamp.to_le_bytes());
        bytes[116..124].copy_from_slice(&self.nonce.to_le_bytes());
        bytes[124..].copy_from_slice(&self.profile.encode()?);
        Ok(bytes)
    }

    pub fn derive(&self) -> Result<([u8; 32], Vec<u32>), &'static str> {
        let mut input = DOMAIN.to_vec();
        input.extend(self.encode()?);
        let seed: [u8; 32] = shake256(&input, 32)?.try_into().unwrap();
        Ok((seed, expand_matrix(self.profile, &seed)?))
    }
}

pub struct ExpectedContext {
    pub network: [u8; 32],
    pub parent: [u8; 32],
    pub height: u64,
    pub profile: Profile,
}

impl ExpectedContext {
    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        if bytes.len() != CONTEXT_SIZE {
            return Err("context length");
        }
        Ok(Self {
            network: bytes[..32].try_into().unwrap(),
            parent: bytes[32..64].try_into().unwrap(),
            height: u64::from_le_bytes(bytes[64..72].try_into().unwrap()),
            profile: Profile::decode(&bytes[72..])?,
        })
    }
}

pub fn verify_proof(packet: &[u8], expected: &ExpectedContext) -> bool {
    if expected.profile.validate().is_err() || !(HEADER_SIZE..=MAX_PROOF).contains(&packet.len()) {
        return false;
    }
    let Ok(header) = LabHeader::decode(&packet[..HEADER_SIZE]) else {
        return false;
    };
    let p = header.profile;
    if header.network != expected.network
        || header.parent != expected.parent
        || header.height != expected.height
        || p != expected.profile
        || packet.len() != HEADER_SIZE + 4 * usize::from(p.m)
    {
        return false;
    }
    let mut norm = 0_u64;
    let mut first = None;
    for word in packet[HEADER_SIZE..].as_chunks::<4>().0 {
        let x = i64::from(i32::from_le_bytes(*word));
        first = first.or_else(|| (x != 0).then_some(x));
        let square = (x * x) as u64;
        if square > p.b2 - norm {
            return false;
        }
        norm += square;
    }
    if !first.is_some_and(|x| x > 0) {
        return false;
    }
    let Ok((_, matrix)) = header.derive() else {
        return false;
    };
    let mut case = b"SIS1".to_vec();
    case.extend(p.encode().unwrap());
    for value in matrix {
        case.extend(value.to_le_bytes());
    }
    case.extend(&packet[HEADER_SIZE..]);
    verify_packet(&case)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_encoding_and_policy_before_derivation() {
        let h = LabHeader {
            network: [1; 32],
            parent: [2; 32],
            payload: [3; 32],
            height: 4,
            timestamp: 5,
            nonce: 6,
            profile: Profile {
                q: 7,
                n: 1,
                m: 2,
                b2: 5,
            },
        };
        let encoded = h.encode().unwrap();
        assert_eq!(LabHeader::decode(&encoded).unwrap(), h);
        assert!(LabHeader::decode(&encoded[..139]).is_err());
        let e = ExpectedContext {
            network: [9; 32],
            parent: h.parent,
            height: h.height,
            profile: h.profile,
        };
        let mut packet = encoded.to_vec();
        packet.extend(1_i32.to_le_bytes());
        packet.extend((-1_i32).to_le_bytes());
        assert!(!verify_proof(&packet, &e));
        packet.extend(0_i32.to_le_bytes());
        assert!(!verify_proof(&packet, &e));
    }
}
