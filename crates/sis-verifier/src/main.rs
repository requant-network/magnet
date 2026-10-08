//! Local framed stdin/stdout adapter; no network listener or filesystem writes.

use std::io::{self, Read, Write};

fn run() -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut length = [0_u8; 4];
        match input.read(&mut length[..1])? {
            0 => return Ok(()),
            _ => input.read_exact(&mut length[1..])?,
        }
        let length = u32::from_le_bytes(length) as usize;
        if length > sis_verifier::MAX_PACKET {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "frame too large",
            ));
        }
        let mut packet = vec![0; length];
        input.read_exact(&mut packet)?;
        output.write_all(&[u8::from(sis_verifier::verify_packet(&packet))])?;
        output.flush()?;
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("sis-verify: {error}");
        std::process::exit(1);
    }
}
