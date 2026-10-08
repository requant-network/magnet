//! Independent SIS-LAB-v1 profile validation and bounded matrix expansion.

use crate::{is_prime, shake::shake256};
const DOMAIN: &[u8] = b"MagnetNetwork/SIS-LAB/matrix/v1\0";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Profile {
    pub q: u32,
    pub n: u16,
    pub m: u16,
    pub b2: u64,
}

impl Profile {
    pub fn validate(self) -> Result<(), &'static str> {
        if !is_prime(self.q)
            || !(1..=64).contains(&self.n)
            || !(1..=128).contains(&self.m)
            || self.b2 == 0
            || self.b2 >= u64::from(self.q) * u64::from(self.q)
        {
            return Err("invalid lab profile");
        }
        Ok(())
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, &'static str> {
        if bytes.len() != 16 {
            return Err("profile length");
        }
        let profile = Self {
            q: u32::from_le_bytes(bytes[..4].try_into().unwrap()),
            n: u16::from_le_bytes(bytes[4..6].try_into().unwrap()),
            m: u16::from_le_bytes(bytes[6..8].try_into().unwrap()),
            b2: u64::from_le_bytes(bytes[8..].try_into().unwrap()),
        };
        profile.validate()?;
        Ok(profile)
    }

    pub fn encode(self) -> Result<[u8; 16], &'static str> {
        self.validate()?;
        let mut bytes = [0; 16];
        bytes[..4].copy_from_slice(&self.q.to_le_bytes());
        bytes[4..6].copy_from_slice(&self.n.to_le_bytes());
        bytes[6..8].copy_from_slice(&self.m.to_le_bytes());
        bytes[8..].copy_from_slice(&self.b2.to_le_bytes());
        Ok(bytes)
    }
}

fn sample(profile: Profile, stream: &[u8]) -> Result<Vec<u32>, &'static str> {
    profile.validate()?;
    let count = usize::from(profile.n) * usize::from(profile.m);
    let max_draws = 4 * count + 1024;
    let cutoff = 65536 - 65536 % profile.q;
    let mut matrix = Vec::with_capacity(count);
    for word in stream.as_chunks::<2>().0.iter().take(max_draws) {
        let value = u32::from(u16::from_le_bytes(*word));
        if value < cutoff {
            matrix.push(value % profile.q);
            if matrix.len() == count {
                return Ok(matrix);
            }
        }
    }
    Err("matrix sampling budget exhausted")
}

pub fn expand_matrix(profile: Profile, seed: &[u8]) -> Result<Vec<u32>, &'static str> {
    let parameters = profile.encode()?;
    if seed.len() != 32 {
        return Err("seed length");
    }
    let mut message = DOMAIN.to_vec();
    message.extend(parameters);
    message.extend(seed);
    let count = usize::from(profile.n) * usize::from(profile.m);
    sample(profile, &shake256(&message, 2 * (4 * count + 1024))?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frozen_generator_and_rejection_budget() {
        let p = Profile {
            q: 7,
            n: 2,
            m: 3,
            b2: 5,
        };
        assert_eq!(expand_matrix(p, &[0; 32]).unwrap(), [1, 0, 6, 6, 0, 6]);
        assert!(sample(p, &vec![255; 2 * (4 * 6 + 1024)]).is_err());
        // cutoff for q=32771 is q, so 65535 must be discarded.
        let p = Profile {
            q: 32771,
            n: 1,
            m: 1,
            b2: 1,
        };
        assert_eq!(sample(p, &[255, 255, 7, 0]).unwrap(), [7]);
        let p = Profile {
            q: 2,
            n: 1,
            m: 1,
            b2: 1,
        };
        assert_eq!(sample(p, &[255, 255]).unwrap(), [1]);
    }

    #[test]
    fn malformed_profiles_and_seeds() {
        assert!(Profile::decode(&[0; 16]).is_err());
        assert!(Profile::decode(&[0; 15]).is_err());
        let p = Profile {
            q: 7,
            n: 1,
            m: 1,
            b2: 1,
        };
        assert!(expand_matrix(p, &[0; 31]).is_err());
        assert!(expand_matrix(Profile { q: 4, ..p }, &[0; 32]).is_err());
        assert!(expand_matrix(Profile { m: 129, ..p }, &[0; 32]).is_err());
    }
}
