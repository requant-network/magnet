//! Independent canonical MGB1 decoding and descriptor binding. No transaction semantics.

use crate::{
    header::ExpectedContext,
    header::{HEADER_SIZE, LabHeader, MAX_PROOF},
    score::{Target, verify_scored_proof},
    sha256,
};

pub const PREFIX: usize = 71;
pub const MAX_BODY: usize = 1024;
pub const MAX_BLOCK: usize = PREFIX + MAX_BODY + MAX_PROOF;
const BODY_DOMAIN: &[u8] = b"MagnetNetwork/block-body/v1\0";
const COMMIT_DOMAIN: &[u8] = b"MagnetNetwork/block-commit/v1\0";
const ID_DOMAIN: &[u8] = b"MagnetNetwork/block-id/v1\0";

pub struct Block {
    pub header: LabHeader,
    pub target: Target,
    packet: Vec<u8>,
    proof_offset: usize,
    identifier: [u8; 32],
}

impl Block {
    pub fn decode(packet: &[u8]) -> Result<Self, &'static str> {
        if !(PREFIX + HEADER_SIZE..=MAX_BLOCK).contains(&packet.len()) || &packet[..4] != b"MGB1" {
            return Err("block bounds/version");
        }
        let target = Target::decode(&packet[4..37])?;
        let size = usize::from(u16::from_le_bytes(packet[69..71].try_into().unwrap()));
        let offset = PREFIX + size;
        if size > MAX_BODY || offset + HEADER_SIZE > packet.len() {
            return Err("body bounds");
        }
        let header = LabHeader::decode(&packet[offset..offset + HEADER_SIZE])?;
        if packet.len() != offset + HEADER_SIZE + 4 * usize::from(header.profile.m) {
            return Err("proof/trailing length");
        }
        let mut body_input = BODY_DOMAIN.to_vec();
        body_input.extend(&packet[69..offset]);
        let root = sha256::digest(&body_input)?;
        let mut commit_input = COMMIT_DOMAIN.to_vec();
        commit_input.extend(&packet[..69]);
        commit_input.extend(root);
        if header.payload != sha256::digest(&commit_input)? {
            return Err("body commitment");
        }
        let mut id_input = ID_DOMAIN.to_vec();
        id_input.extend(packet);
        Ok(Self {
            header,
            target,
            packet: packet.to_vec(),
            proof_offset: offset,
            identifier: sha256::digest(&id_input)?,
        })
    }

    pub fn identifier(&self) -> [u8; 32] {
        self.identifier
    }
    pub fn valid_proof(&self, context: &ExpectedContext) -> bool {
        verify_scored_proof(&self.packet[self.proof_offset..], context, self.target)
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    pub(crate) fn fixture(key: &str) -> Vec<u8> {
        let text = include_str!("../../../tests/vectors/block-v1.json");
        let prefix = format!("\"{key}\": \"");
        let value = text
            .split(&prefix)
            .nth(1)
            .unwrap()
            .split('"')
            .next()
            .unwrap();
        value
            .as_bytes()
            .as_chunks::<2>()
            .0
            .iter()
            .map(|b| u8::from_str_radix(std::str::from_utf8(b).unwrap(), 16).unwrap())
            .collect()
    }

    #[test]
    fn frozen_canonical_commitment_and_rejection() {
        let packet = fixture("block_hex");
        let block = Block::decode(&packet).unwrap();
        assert_eq!(block.identifier().as_slice(), fixture("id_hex"));
        assert_eq!(block.header.payload.as_slice(), fixture("payload_hex"));
        for i in [0, 4, 37, 71] {
            let mut other = packet.clone();
            other[i] ^= 2;
            assert!(Block::decode(&other).is_err());
        }
        assert!(Block::decode(&packet[..packet.len() - 1]).is_err());
        let mut extra = packet.clone();
        extra.push(0);
        assert!(Block::decode(&extra).is_err());
        assert!(Block::decode(&vec![0; MAX_BLOCK + 1]).is_err());
    }
}
