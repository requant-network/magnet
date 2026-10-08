//! Local length-framed stdin/stdout generator/binding adapter. No network I/O.

use std::io::{self, Read, Write};

fn run() -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut length = [0; 4];
        match input.read(&mut length[..1])? {
            0 => return Ok(()),
            _ => input.read_exact(&mut length[1..])?,
        }
        let length = u32::from_le_bytes(length) as usize;
        if length > sis_verifier::lab::MAX_REQUEST {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "frame too large",
            ));
        }
        let mut request = vec![0; length];
        input.read_exact(&mut request)?;
        let response = sis_verifier::lab::respond(&request)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        output.write_all(&(response.len() as u32).to_le_bytes())?;
        output.write_all(&response)?;
        output.flush()?;
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("sis-lab: {error}");
        std::process::exit(1);
    }
}
