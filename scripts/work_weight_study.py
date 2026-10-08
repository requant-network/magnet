"""Concrete paid reuse examples; inverse target remains an eligibility hypothesis."""

from collections import deque
import hashlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from reference.block import Block,commitment
from reference.chain import ChainPolicy,LabChain
from reference.grinding import SCORE_DOMAIN,score_digest
from reference.header import LabHeader
from reference.sis import Profile,verify
from scripts.native_driver import build_native,encode_request,run_requests,WORK_NAMES
from scripts.chain_driver import build_chain,command,exchange_chain
from scripts.chain_checks import snapshot
from scripts.consensus_evidence import begin_report,finish_report


def campaign(native,chain_executable,*,target,capacity):
    p=ChainPolicy(bytes([8])*32,Profile(7,1,3,8),target,bytes([4])*32,anchor_time=99)
    chain=LabChain(p); pool=deque(); blocks=[]; audits=[]
    work=dict(headers=0,matrix_entries=0,acquisitions=0,pool_checks=0,acquisition_checks=0,scores=0,score_bytes=0,evictions=0)
    native_work=dict.fromkeys(WORK_NAMES,0)
    reused=0
    for index in range(16):
        body=f'work-example/{index}'.encode(); recipient=bytes(32)
        payload=commitment(target,recipient,body)
        hit=None
        for nonce in range(256):
            h=LabHeader(p.network,chain.tip,payload,chain.height+1,100+index,nonce,p.profile)
            matrix=h.matrix(); work['headers']+=1; work['matrix_entries']+=p.profile.n*p.profile.m
            scored=set()
            def eligible(vector):
                if vector in scored: return False
                scored.add(vector); work['scores']+=1; work['score_bytes']+=len(SCORE_DOMAIN)+140+4*p.profile.m
                return int.from_bytes(score_digest(h,vector),'big')<target
            for vector in tuple(pool):
                work['pool_checks']+=1
                if verify(p.profile,matrix,vector) and eligible(vector):
                    hit=Block(h,vector,target,recipient,body); reused+=1; break
            if hit is not None: break
            if native_work['nodes']>=250000 or work['acquisitions']>=4096:
                raise RuntimeError('work campaign cumulative cap')
            request=encode_request(p.profile,matrix,'mitm-budgeted',nodes=min(5000,250000-native_work['nodes']),
                                   table=1000,pairs=10000,proofs=64)
            result=run_requests(native,[request])[0]; work['acquisitions']+=1
            for key,value in result['work'].items(): native_work[key]+=value
            vectors=[tuple(v) for v in result['proofs']]
            for vector in vectors:
                work['acquisition_checks']+=1
                if not verify(p.profile,matrix,vector): raise RuntimeError('invalid acquired vector')
                if capacity and vector not in pool:
                    if len(pool)==capacity: pool.popleft(); work['evictions']+=1
                    pool.append(vector)
            # Eager acquisition is completely charged before the first winning score.
            for vector in vectors:
                if eligible(vector): hit=Block(h,vector,target,recipient,body); break
            if hit is not None: break
        if hit is None: raise RuntimeError('work fixture nonce cap')
        if chain.append(hit.encode(),now=100+index)!='accepted': raise RuntimeError('work example admission')
        blocks.append(hit)
        audits.append({'height':index+1,'cumulative_work':dict(work),'cumulative_native':dict(native_work),
                       'cumulative_reused_hits':reused,'block_hex':hit.encode().hex()})
    model=LabChain(p); expected=[snapshot(model,'accepted')]; commands=[]
    for b in blocks:
        status=model.append(b.encode(),now=1000); expected.append(snapshot(model,status)); commands.append(command(b.encode(),now=1000))
    if exchange_chain(chain_executable,p,commands)!=expected: raise RuntimeError('work example native chain disagreement')
    return {'target':str(target),'pool_capacity':capacity,'accepted_blocks':len(blocks),'reused_hits':reused,
            'fresh_hits':len(blocks)-reused,'work':work,'native_work':native_work,'tip':chain.tip.hex(),
            'inverse_target_score_trials_per_hit':2**256//target,'records':audits}


def main():
    paths=begin_report('work-weight-v1'); manifest=paths[2]
    native=build_native(release=True); chain=build_chain()
    records=[campaign(native,chain,target=target,capacity=capacity) for target in (2**255,2**252) for capacity in (0,16)]
    report={'profile':[7,1,3,8],'campaigns':len(records),'blocks':sum(r['accepted_blocks'] for r in records),
            'configuration':{'blocks_per_campaign':16,'nonce_cap_per_block':256,'shared_node_cap':250000,
                             'shared_acquisition_cap':4096,'native_proof_cap':64,'native_nodes_per_acquisition':5000},
            'records':[{k:v for k,v in r.items() if k!='records'} for r in records],
            'native_search_release_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),
            'limitations':['tiny fixed-policy example, not production chainwork calibration',
                           'chosen proof choices change subsequent parents; not paired identical-header speed ranking',
                           'logical counters do not price process startup, setup, elapsed time or energy',
                           'headers/admission are real, repeated solutions do not prove zero-cost whole blocks',
                           'inverse-target describes score trials only under a uniform-independent eligible input assumption',
                           'no cross-profile weighting or dynamic-target fork rule selected'],
            'mismatches':0}
    finish_report(paths,report,manifest,raw={'records':records},executable=chain)


if __name__=='__main__': main()
