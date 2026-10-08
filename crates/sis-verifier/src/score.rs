//! Existing laboratory score and strict external target, independently implemented.

use crate::{
    header::{ExpectedContext, MAX_PROOF, verify_proof},
    sha256,
};

const DOMAIN: &[u8] = b"MagnetNetwork/SIS-LAB/grinding-score/v1\0";

#[derive(Clone, Copy)]
pub struct Target([u8; 33]);

impl Target {
    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        let value: [u8; 33] = bytes.try_into().map_err(|_| "target length")?;
        if value[0] > 1 || value[0] == 1 && value[1..].iter().any(|&x| x != 0) {
            return Err("target range");
        }
        Ok(Self(value))
    }

    pub fn is_zero(&self) -> bool {
        self.0 == [0; 33]
    }

    pub fn accepts(&self, digest: [u8; 32]) -> bool {
        let mut value = [0; 33];
        value[1..].copy_from_slice(&digest);
        value < self.0
    }
}

pub fn digest(packet: &[u8]) -> Result<[u8; 32], &'static str> {
    if packet.len() > MAX_PROOF {
        return Err("score packet bound");
    }
    let mut message = DOMAIN.to_vec();
    message.extend(packet);
    sha256::digest(&message)
}

pub fn verify_scored_proof(packet: &[u8], context: &ExpectedContext, target: Target) -> bool {
    !target.is_zero()
        && verify_proof(packet, context)
        && digest(packet).is_ok_and(|hash| target.accepts(hash))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strict_full_range_target() {
        let zero = Target::decode(&[0; 33]).unwrap();
        assert!(!zero.accepts([0; 32]));
        let mut full = [0; 33];
        full[0] = 1;
        assert!(Target::decode(&full).unwrap().accepts([255; 32]));
        full[32] = 1;
        assert!(Target::decode(&full).is_err());
        let mut threshold = [0; 33];
        threshold[32] = 1;
        let target = Target::decode(&threshold).unwrap();
        assert!(target.accepts([0; 32]));
        let mut equal = [0; 32];
        equal[31] = 1;
        assert!(!target.accepts(equal));
        assert!(Target::decode(&[0; 32]).is_err());
        assert!(digest(&vec![0; MAX_PROOF + 1]).is_err());
    }
}
