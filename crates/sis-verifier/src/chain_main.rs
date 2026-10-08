//! Bounded local stateful adapter. First frame MCP1 policy; no peer/network I/O.
use sis_verifier::{
    block::MAX_BLOCK,
    chain::{ChainPolicy, LabChain, Status},
};
use std::io::{self, Read, Write};
const MAX_COMMANDS: usize = 8192;

fn frame(input: &mut impl Read) -> io::Result<Option<Vec<u8>>> {
    let mut size = [0; 4];
    if input.read(&mut size[..1])? == 0 {
        return Ok(None);
    }
    input.read_exact(&mut size[1..])?;
    let length = u32::from_le_bytes(size) as usize;
    if length > 9 + MAX_BLOCK {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "frame bound"));
    }
    let mut bytes = vec![0; length];
    input.read_exact(&mut bytes)?;
    Ok(Some(bytes))
}
fn reply(output: &mut impl Write, chain: &LabChain, status: Status) -> io::Result<()> {
    output.write_all(&[status as u8])?;
    output.write_all(&chain.height().to_le_bytes())?;
    output.write_all(&chain.tip())?;
    output.write_all(&(chain.count() as u16).to_le_bytes())?;
    output.flush()
}
fn run() -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let Some(first) = frame(&mut input)? else {
        return Ok(());
    };
    let invalid = |e| io::Error::new(io::ErrorKind::InvalidData, e);
    let mut chain = LabChain::new(ChainPolicy::decode(&first).map_err(invalid)?);
    reply(&mut output, &chain, Status::Accepted)?;
    let mut commands = 0;
    while let Some(bytes) = frame(&mut input)? {
        if commands == MAX_COMMANDS {
            return Err(invalid("command cap"));
        }
        commands += 1;
        let status = match bytes.as_slice() {
            [3] => Status::Accepted,
            [mode @ (1 | 2), rest @ ..] if rest.len() >= 8 => {
                let now = u64::from_le_bytes(rest[..8].try_into().unwrap());
                if *mode == 1 {
                    chain.append(&rest[8..], now)
                } else {
                    chain.inspect(&rest[8..], now)
                }
            }
            _ => return Err(invalid("command shape")),
        };
        reply(&mut output, &chain, status)?;
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("magnet-chain: {e}");
        std::process::exit(1);
    }
}
