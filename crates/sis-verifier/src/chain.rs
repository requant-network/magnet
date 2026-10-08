//! Independent spec11 fixed-policy linear-chain admission, not monetary consensus.

use crate::{block::Block, generator::Profile, header::ExpectedContext, score::Target};
pub const MAX_CHAIN: usize = 4096;
pub const POLICY_SIZE: usize = 135;

pub struct ChainPolicy {
    network: [u8; 32],
    profile: Profile,
    target: Target,
    anchor: [u8; 32],
    anchor_height: u64,
    anchor_time: u64,
    future: u16,
}

impl ChainPolicy {
    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        if bytes.len() != POLICY_SIZE || &bytes[..4] != b"MCP1" {
            return Err("policy bounds/version");
        }
        let profile = Profile::decode(&bytes[36..52])?;
        let target = Target::decode(&bytes[52..85])?;
        let future = u16::from_le_bytes(bytes[133..135].try_into().unwrap());
        if profile.q == 2 || target.is_zero() || target.wire()[0] == 1 || future > 3600 {
            return Err("ineligible chain policy");
        }
        Ok(Self {
            network: bytes[4..36].try_into().unwrap(),
            profile,
            target,
            anchor: bytes[85..117].try_into().unwrap(),
            anchor_height: u64::from_le_bytes(bytes[117..125].try_into().unwrap()),
            anchor_time: u64::from_le_bytes(bytes[125..133].try_into().unwrap()),
            future,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Status {
    Accepted,
    Malformed,
    WrongPolicy,
    UnknownOrNontipParent,
    WrongHeight,
    PastTime,
    DeferFutureTime,
    InvalidProof,
    StorageLimit,
}

pub struct LabChain {
    policy: ChainPolicy,
    blocks: Vec<Block>,
}

impl LabChain {
    pub fn new(policy: ChainPolicy) -> Self {
        Self {
            policy,
            blocks: Vec::new(),
        }
    }
    pub fn count(&self) -> usize {
        self.blocks.len()
    }
    pub fn tip(&self) -> [u8; 32] {
        self.blocks
            .last()
            .map_or(self.policy.anchor, Block::identifier)
    }
    pub fn height(&self) -> u64 {
        self.policy.anchor_height + self.blocks.len() as u64
    }

    fn evaluate(&self, block: &Block, now: u64) -> Status {
        let h = &block.header;
        let p = &self.policy;
        if h.network != p.network || h.profile != p.profile || block.target != p.target {
            return Status::WrongPolicy;
        }
        if h.parent != self.tip() {
            return Status::UnknownOrNontipParent;
        }
        if self.height().checked_add(1) != Some(h.height) {
            return Status::WrongHeight;
        }
        let mut times: Vec<_> = self
            .blocks
            .iter()
            .rev()
            .take(11)
            .map(|b| b.header.timestamp)
            .collect();
        if times.is_empty() {
            times.push(p.anchor_time);
        }
        times.sort_unstable();
        if h.timestamp <= times[times.len() / 2] {
            return Status::PastTime;
        }
        if h.timestamp > now.saturating_add(u64::from(p.future)) {
            return Status::DeferFutureTime;
        }
        let context = ExpectedContext {
            network: p.network,
            parent: self.tip(),
            height: h.height,
            profile: p.profile,
        };
        if !block.valid_proof(&context) {
            return Status::InvalidProof;
        }
        if self.count() == MAX_CHAIN {
            return Status::StorageLimit;
        }
        Status::Accepted
    }

    pub fn inspect(&self, packet: &[u8], now: u64) -> Status {
        match Block::decode(packet) {
            Ok(block) => self.evaluate(&block, now),
            Err(_) => Status::Malformed,
        }
    }

    pub fn append(&mut self, packet: &[u8], now: u64) -> Status {
        let Ok(block) = Block::decode(packet) else {
            return Status::Malformed;
        };
        let status = self.evaluate(&block, now);
        if status == Status::Accepted {
            self.blocks.push(block);
        }
        status
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn policy() -> Vec<u8> {
        let mut b = b"MCP1".to_vec();
        b.extend([0; 32]);
        b.extend(
            Profile {
                q: 7,
                n: 1,
                m: 3,
                b2: 8,
            }
            .encode()
            .unwrap(),
        );
        let mut t = [0; 33];
        t[1] = 128;
        b.extend(t);
        b.extend([1; 32]);
        b.extend(0_u64.to_le_bytes());
        b.extend(99_u64.to_le_bytes());
        b.extend(120_u16.to_le_bytes());
        b
    }
    #[test]
    fn trusted_policy_and_empty_state() {
        let b = policy();
        let mut chain = LabChain::new(ChainPolicy::decode(&b).unwrap());
        assert_eq!(chain.height(), 0);
        assert_eq!(chain.tip(), [1; 32]);
        assert_eq!(chain.append(&[], 100), Status::Malformed);
        assert_eq!(chain.count(), 0);
        for i in [0, 36, 52, 134] {
            let mut bad = b.clone();
            bad[i] = 255;
            assert!(ChainPolicy::decode(&bad).is_err());
        }
        assert!(ChainPolicy::decode(&b[..134]).is_err());
    }

    #[test]
    fn frozen_block_full_admission_and_inspection() {
        let mut chain = LabChain::new(ChainPolicy::decode(&policy()).unwrap());
        let packet = crate::block::tests::fixture("block_hex");
        assert_eq!(chain.inspect(&packet, 100), Status::Accepted);
        assert_eq!(chain.count(), 0);
        assert_eq!(chain.append(&packet, 100), Status::Accepted);
        assert_eq!(
            chain.tip().as_slice(),
            crate::block::tests::fixture("id_hex")
        );
        assert_eq!(chain.append(&packet, 100), Status::UnknownOrNontipParent);
        assert_eq!(chain.count(), 1);
    }
}
