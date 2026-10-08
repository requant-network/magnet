"""Real-block fixed-policy delivery/partition experiments with native replay audits."""

import heapq
import random
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from reference.chain import ChainPolicy,LabChain
from reference.forks import ForkTree
from reference.sis import Profile
from scripts.chain_driver import build_chain,command,exchange_chain
from scripts.chain_fixtures import mine
from scripts.chain_checks import snapshot
from scripts.consensus_evidence import begin_report,finish_report

NAMES=("a","b","relay")


def scenario(*,delay,partition,seed,executable):
    rng=random.Random(seed)
    p=ChainPolicy(bytes([6])*32,Profile(7,1,3,8),2**255,bytes([5])*32,anchor_time=99)
    nodes={name:ForkTree(p,peers=NAMES) for name in NAMES}
    events=[]; sequence=0; all_blocks={}; trace=[]; reorgs=0; calls=0
    def schedule(time,kind,destination,source,packet=b""):
        nonlocal sequence
        sequence+=1
        heapq.heappush(events,(time,sequence,kind,destination,source,packet))
    for index in range(6):
        schedule(100+index*10,"mine","a","a")
        schedule(105+index*10,"mine","b","b")
    schedule(210,"mine","a","a")
    while events:
        now,_,kind,dest,source,packet=heapq.heappop(events)
        tree=nodes[dest]
        if kind=="mine":
            height=p.anchor_height+len(tree.canonical)+1
            block=mine(p,parent=tree.tip,height=height,timestamp=now,body=f'{dest}/{now}'.encode())
            all_blocks[block.identifier()]=block
            packet=block.encode()
            for receiver in NAMES:
                if receiver==dest: continue
                arrival=now+rng.randint(0,delay)
                if partition and now<180: arrival=max(arrival,180+rng.randint(0,delay))
                schedule(arrival,"deliver",receiver,dest,packet)
        result=tree.submit(packet,peer=source,now=now)
        results=(result,)+tree.drain(now=now)
        reorgs+=sum(bool(r.detached) for r in results)
        calls+=sum(r.admission_calls for r in results)
        trace.append({"time":now,"kind":kind,"node":dest,"source":source,"statuses":[r.status for r in results],
                      "tip":tree.tip.hex(),"height":len(tree.canonical),"queued":tree.queued_count})
        if len(trace)>512: raise RuntimeError("event cap")
    # Explicit reliable post-heal reconciliation, not silent queue/cap bypass.
    # Relay may have expired early orphans; peers retry every known block in
    # parent-first order, then bounded drains run under the same tree API.
    now=max(1000,max(record['time'] for record in trace))
    for name,tree in nodes.items():
        for block in sorted(all_blocks.values(),key=lambda b:(b.header.height,b.identifier())):
            result=tree.submit(block.encode(),peer="relay",now=now)
            drained=tree.drain(now=now)
            reorgs+=bool(result.detached)+sum(bool(r.detached) for r in drained)
            calls+=result.admission_calls+sum(r.admission_calls for r in drained)
        if tree.queued_count: raise RuntimeError("post-heal queue unresolved")
    audits=[]
    for name,tree in nodes.items():
        # Audit every retained branch, not only the preferred tip. Node path
        # snapshots are internal to this experiment and never trust peer work.
        for tip in all_blocks:
            path=tree.path(tip)
            model=LabChain(p); commands=[]; expected=[snapshot(model,"accepted")]
            for key in path:
                packet=all_blocks[key].encode()
                status=model.append(packet,now=now)
                if status!='accepted': raise RuntimeError("retained branch replay rejected")
                commands.append(command(packet,now=now)); expected.append(snapshot(model,status))
            if exchange_chain(executable,p,commands)!=expected: raise RuntimeError("native branch replay mismatch")
            audits.append({"node":name,"tip":tip.hex(),"blocks":len(path)})
    tips={name:tree.tip.hex() for name,tree in nodes.items()}
    heights={name:len(tree.canonical) for name,tree in nodes.items()}
    max_depth=max(heights.values())
    competing={b.identifier() for b in all_blocks.values() if b.header.height==p.anchor_height+max_depth}
    unique_best=len(competing)==1
    if unique_best and len(set(tips.values()))!=1: raise RuntimeError("unique longest branch failed to converge")
    return {"delay_seconds":delay,"partition_until":180 if partition else None,"seed":seed,"mined_blocks":len(all_blocks),
            "delivery_events":len(trace),"reorgs":reorgs,"admission_calls":calls,"tips":tips,"heights":heights,
            "unique_best":unique_best,"converged":len(set(tips.values()))==1,"native_branch_audits":len(audits),
            "audited_blocks":sum(a['blocks'] for a in audits),"trace":trace,
            "blocks":[b.encode().hex() for b in all_blocks.values()],"audits":audits}


def main():
    paths=begin_report('forks-v1'); manifest=paths[2]
    executable=build_chain()
    records=[scenario(delay=delay,partition=partition,seed=seed,executable=executable)
             for delay in (0,1,10,60) for partition in (False,True) for seed in (20261008122,20261008123)]
    compact=[{k:v for k,v in r.items() if k not in ('trace','blocks','audits')} for r in records]
    report={"scenarios":len(records),"configuration":{"nodes":3,"miners":2,"fixed_target":str(2**255),
             "profile":[7,1,3,8],"events_cap":512,"reconciliation":"explicit parent-first reliable retry after heal"},
            "records":compact,"native_branch_audits":sum(r['native_branch_audits'] for r in records),
            "audited_blocks":sum(r['audited_blocks'] for r in records),"mismatches":0,
            "limitations":["nominal fixed-profile depth only; not adversarial chainwork",
                           "local deterministic processes, not independent operators or production networking",
                           "equal-depth tips retain first arrival and can differ until a strictly longer branch arrives"]}
    finish_report(paths,report,manifest,raw={"records":records},executable=executable)


if __name__=='__main__': main()
