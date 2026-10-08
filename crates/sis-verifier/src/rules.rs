//! Trusted local admission rules; no parent-chain or payload-body validation.

use crate::{
    header::{ExpectedContext, HEADER_SIZE, LabHeader, MAX_PROOF},
    score::{Target, verify_scored_proof},
};

pub const MIN_RULES: usize = 170;
pub const MAX_RULES: usize = 394;

pub struct LabRules {
    context: ExpectedContext,
    target: Target,
    earliest: u64,
    latest: u64,
    payloads: Vec<[u8; 32]>,
}

impl LabRules {
    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        if !(MIN_RULES..=MAX_RULES).contains(&bytes.len()) {
            return Err("rules length");
        }
        let context = ExpectedContext::decode(&bytes[..88])?;
        let target = Target::decode(&bytes[88..121])?;
        let earliest = u64::from_le_bytes(bytes[121..129].try_into().unwrap());
        let latest = u64::from_le_bytes(bytes[129..137].try_into().unwrap());
        let count = usize::from(bytes[137]);
        if earliest > latest || !(1..=8).contains(&count) || bytes.len() != 138 + 32 * count {
            return Err("rules interval/payload count");
        }
        let mut payloads = Vec::with_capacity(count);
        for payload in bytes[138..].as_chunks::<32>().0 {
            if payloads.contains(payload) {
                return Err("duplicate allowed payload");
            }
            payloads.push(*payload);
        }
        Ok(Self {
            context,
            target,
            earliest,
            latest,
            payloads,
        })
    }

    pub fn admit(&self, packet: &[u8]) -> bool {
        if self.target.is_zero() || !(HEADER_SIZE..=MAX_PROOF).contains(&packet.len()) {
            return false;
        }
        let Ok(header) = LabHeader::decode(&packet[..HEADER_SIZE]) else {
            return false;
        };
        if header.timestamp < self.earliest
            || header.timestamp > self.latest
            || !self.payloads.contains(&header.payload)
        {
            return false;
        }
        verify_scored_proof(packet, &self.context, self.target)
    }
}
