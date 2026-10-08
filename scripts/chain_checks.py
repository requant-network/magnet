"""Independent full Rust/Python linear-state differential and bounded parser corpus."""

from dataclasses import replace
import random
import struct
import subprocess

from reference.block import Block, PREFIX, commitment
from reference.chain import ChainPolicy, LabChain
from reference.sis import Profile
from scripts.chain_driver import command, encode_policy, exchange_chain
from scripts.chain_fixtures import mine


def snapshot(chain,status):
    return {"status":status,"height":chain.height,"tip":chain.tip.hex(),"count":len(chain.blocks)}


def differential_chain(executable):
    rng=random.Random(20261008121)
    p=ChainPolicy(bytes([7])*32,Profile(7,1,3,8),2**255,bytes([3])*32,anchor_time=99)
    chain=LabChain(p)
    commands=[]
    expected=[snapshot(chain,"accepted")]
    def add(packet,now,append=True):
        status=chain.append(packet,now=now) if append else chain.inspect(packet,now=now)
        commands.append(command(packet,now=now,append=append)); expected.append(snapshot(chain,status))
    first=mine(p,body=b"native parser")
    frozen=first.encode()
    for i in range(2000):
        wire=bytearray(frozen)
        if i%4==0:
            for _ in range(rng.randint(1,4)): wire[rng.randrange(len(wire))]^=rng.randint(1,255)
            packet=bytes(wire)
        elif i%4==1: packet=frozen[:rng.randrange(len(frozen))]
        elif i%4==2: packet=rng.randbytes(rng.randrange(1748))
        else: packet=frozen+rng.randbytes(rng.randint(1,32))
        add(packet,100,False)
    # Commitments valid but admission fields/proofs wrong; these avoid a corpus
    # made solely of easy malformed-magic rejections.
    for field,value in (("network",bytes(32)),("parent",bytes(32)),("height",2),("timestamp",99),("timestamp",221)):
        add(replace(first,header=replace(first.header,**{field:value})).encode(),100)
    add(replace(first,vector=(0,0,0)).encode(),100)
    add(first.encode(),100,False)
    add(first.encode(),100)
    add(first.encode(),100)
    for index in range(1,64):
        b=mine(p,parent=chain.tip,height=chain.height+1,timestamp=100+index,
               body=rng.randbytes((0,1,55,56,64,127,1024)[index%7]))
        add(b.encode(),100+index,False); add(b.encode(),100+index)
    future=mine(p,parent=chain.tip,height=chain.height+1,timestamp=1000)
    add(future.encode(),200); add(future.encode(),880)
    # Timestamp is permitted below previous timestamp when above upper median.
    low=mine(p,parent=chain.tip,height=chain.height+1,timestamp=161)
    add(low.encode(),1000)
    records=exchange_chain(executable,p,commands)
    if records != expected:
        index=next(i for i,(a,b) in enumerate(zip(records,expected)) if a!=b)
        raise RuntimeError(f"native full-chain mismatch {index}: {records[index]} != {expected[index]}")
    boundary_count=0
    for height,stamp,now in ((2**64-2,2**64-1,2**64-2),(2**64-1,100,100)):
        policy=replace(p,anchor_height=height)
        if height==2**64-1:
            block=replace(first,header=replace(first.header,height=height))
        else: block=mine(policy,timestamp=stamp)
        model=LabChain(policy); status=model.append(block.encode(),now=now)
        result=exchange_chain(executable,policy,[command(block.encode(),now=now)])
        if result[-1]!=snapshot(model,status): raise RuntimeError("height/clock saturation mismatch")
        boundary_count+=1
    # Wire checks terminate without unbounded allocation; clean empty input works.
    prefix=struct.pack("<I",len(encode_policy(p)))+encode_policy(p)
    malformed=(b"\x01",struct.pack("<I",1757),struct.pack("<I",135)+b"x",prefix+struct.pack("<I",1)+b"\x04")
    for wire in malformed:
        result=subprocess.run([str(executable)],input=wire,capture_output=True,timeout=5)
        if result.returncode==0: raise RuntimeError("bad chain frame accepted")
    empty=subprocess.run([str(executable)],input=b"",capture_output=True,check=True,timeout=5)
    if empty.stdout or empty.stderr: raise RuntimeError("empty chain stream")
    full=LabChain(p)
    cap_commands=[]
    cap_expected=[snapshot(full,"accepted")]
    for index in range(4096):
        b=mine(p,parent=full.tip,height=full.height+1,timestamp=100+index,body=b"storage corpus")
        status=full.append(b.encode(),now=5000)
        cap_commands.append(command(b.encode(),now=5000)); cap_expected.append(snapshot(full,status))
    extra=mine(p,parent=full.tip,height=full.height+1,timestamp=4196,body=b"storage corpus")
    for packet in (extra.encode(),replace(extra,vector=(0,0,0)).encode()):
        status=full.append(packet,now=5000)
        cap_commands.append(command(packet,now=5000)); cap_expected.append(snapshot(full,status))
    if cap_expected[-2]['status']!='storage-limit' or cap_expected[-1]['status']!='invalid-proof':
        raise RuntimeError("reference full-chain rejection order")
    if exchange_chain(executable,p,cap_commands)!=cap_expected:
        raise RuntimeError("native storage cap/proof precedence mismatch")
    maximal_policy=replace(p,profile=Profile(65521,64,128,65521**2-1))
    payload=commitment(p.target,bytes(32),bytes(1024))
    maximal_header=replace(first.header,profile=maximal_policy.profile,payload=payload)
    maximal=Block(maximal_header,(1,)+(0,)*127,p.target,bytes(32),bytes(1024))
    maximal_model=LabChain(maximal_policy)
    maximal_status=maximal_model.append(maximal.encode(),now=100)
    if exchange_chain(executable,maximal_policy,[command(maximal.encode(),now=100)])[-1]!=snapshot(maximal_model,maximal_status):
        raise RuntimeError("maximum envelope/profile admission mismatch")
    return {"seed":20261008121,"commands":len(commands)+len(cap_commands),"accepted_blocks":len(chain.blocks),
            "storage_chain_blocks":len(full.blocks),"storage_cap_checks":2,
            "maximum_shape_blocks":1,"maximum_shape_status":maximal_status,
            "boundary_chains":boundary_count,"framing_rejections":len(malformed),"mismatches":0,
            "status_counts_main_corpus":{s:sum(r['status']==s for r in records[1:]) for s in sorted({r['status'] for r in records[1:]})},
            "scope":"independent complete MGB1 parsing, linear admission and state snapshots"}
