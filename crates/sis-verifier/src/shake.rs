//! Byte-oriented SHAKE256 (FIPS 202), for bounded laboratory inputs only.
//! This implementation has not undergone cryptographic certification or audit.

pub const MAX_INPUT: usize = 2048;
pub const MAX_OUTPUT: usize = 2 * (4 * 64 * 128 + 1024);
const RATE: usize = 136;
const RC: [u64; 24] = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808a,
    0x8000000080008000,
    0x000000000000808b,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008a,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000a,
    0x000000008000808b,
    0x800000000000008b,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800a,
    0x800000008000000a,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
];
// Lane index x + 5*y; rotations reduced modulo the 64-bit lane width.
const ROT: [u32; 25] = [
    0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14,
];

fn permute(a: &mut [u64; 25]) {
    for rc in RC {
        let mut c = [0; 5];
        for x in 0..5 {
            for y in 0..5 {
                c[x] ^= a[x + 5 * y];
            }
        }
        for x in 0..5 {
            let d = c[(x + 4) % 5] ^ c[(x + 1) % 5].rotate_left(1);
            for y in 0..5 {
                a[x + 5 * y] ^= d;
            }
        }
        let mut b = [0; 25];
        for x in 0..5 {
            for y in 0..5 {
                b[y + 5 * ((2 * x + 3 * y) % 5)] = a[x + 5 * y].rotate_left(ROT[x + 5 * y]);
            }
        }
        for x in 0..5 {
            for y in 0..5 {
                a[x + 5 * y] = b[x + 5 * y] ^ ((!b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y]);
            }
        }
        a[0] ^= rc;
    }
}

fn xor_bytes(a: &mut [u64; 25], bytes: &[u8]) {
    for (i, byte) in bytes.iter().enumerate() {
        a[i / 8] ^= u64::from(*byte) << (8 * (i % 8));
    }
}

pub fn shake256(input: &[u8], length: usize) -> Result<Vec<u8>, &'static str> {
    if input.len() > MAX_INPUT || length > MAX_OUTPUT {
        return Err("SHAKE lab bound");
    }
    let mut state = [0; 25];
    let (chunks, tail) = input.as_chunks::<RATE>();
    for block in chunks {
        xor_bytes(&mut state, block);
        permute(&mut state);
    }
    xor_bytes(&mut state, tail);
    state[tail.len() / 8] ^= 0x1f_u64 << (8 * (tail.len() % 8));
    state[(RATE - 1) / 8] ^= 0x80_u64 << (8 * ((RATE - 1) % 8));
    permute(&mut state);
    let mut output = vec![0; length];
    for (i, block) in output.chunks_mut(RATE).enumerate() {
        if i != 0 {
            permute(&mut state);
        }
        for (j, byte) in block.iter_mut().enumerate() {
            *byte = (state[j / 8] >> (8 * (j % 8))) as u8;
        }
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nist_empty_message_prefix_and_bounds() {
        // NIST SHAKE256_Msg0.pdf, first 32 output bytes.
        let hex: String = shake256(b"", 32)
            .unwrap()
            .iter()
            .map(|x| format!("{x:02x}"))
            .collect();
        assert_eq!(
            hex,
            "46b9dd2b0ba88d13233b3feb743eeb243fcd52ea62b81b82b50c27646ed5762f"
        );
        assert!(shake256(&[0; MAX_INPUT + 1], 1).is_err());
        assert!(shake256(b"", MAX_OUTPUT + 1).is_err());
        assert_eq!(shake256(b"", 0).unwrap(), []);
    }
}
