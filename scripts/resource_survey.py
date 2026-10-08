"""Actual bounded fork-queue/admission flood probes; no throughput benchmark."""

from dataclasses import replace
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from reference.block import MAX_BLOCK
from reference.chain import ChainPolicy
from reference.forks import ForkTree,ForkLimits,MAX_RETAINED_WIRE
from reference.sis import Profile
from scripts.chain_fixtures import mine
from scripts.consensus_evidence import begin_report,finish_report


def require(condition,message):
    if not condition: raise RuntimeError(message)


def probes():
    p=ChainPolicy(bytes(32),Profile(7,1,3,8),2**255,bytes([1])*32,anchor_time=99)
    peers=('a','b','c','d')
    tree=ForkTree(p,peers=peers)
    flood=[tree.submit(b'bad',peer='a',now=100) for _ in range(1024)]
    require(sum(r.status=='malformed' for r in flood)==16,'malformed decoding/rate accounting')
    require(sum(r.status=='submission-rate-limit' for r in flood)==1008,'rate rejection count')
    tree=ForkTree(p,peers=peers)
    b=mine(p,parent=bytes([9])*32,height=2,body=bytes(1024))
    outcomes=[]
    for peer in peers:
        for index in range(16):
            block=replace(b,header=replace(b.header,nonce=len(outcomes)))
            outcomes.append(tree.submit(block.encode(),peer=peer,now=100))
    require(tree.queued_count==32,'combined queue capacity')
    retained=tree.retained_wire_bytes
    require(retained<=MAX_RETAINED_WIRE and all(r.admission_calls==0 for r in outcomes),'orphan byte/work bound')
    require(max(tree.queue_peers().values())<=8,'peer queue capacity')
    tree.drain(now=159); require(tree.queued_count==32,'premature TTL expiry')
    tree.drain(now=160); require(tree.queued_count==0,'expired entries retained')
    capped=ForkTree(p,peers=peers,limits=ForkLimits(nodes=1))
    first=mine(p); other=mine(p,body=b'other')
    require(capped.submit(first.encode(),peer='a',now=100).status=='accepted-main','initial cap probe admission')
    rejection=capped.submit(other.encode(),peer='a',now=100)
    require(rejection.status=='node-limit' and rejection.admission_calls==0,'capacity rejection before expensive admission')
    return {'malformed_flood':{'submitted':1024,'decoded':16,'rate_rejected':1008,'admission_calls':sum(r.admission_calls for r in flood)},
            'orphan_flood':{'submitted':len(outcomes),'queued':32,'retained_wire_bytes':retained,
                            'max_peer_queued':8,'admission_calls':0,'after_ttl':tree.queued_count,
                            'status_counts':{s:sum(r.status==s for r in outcomes) for s in sorted({r.status for r in outcomes})}},
            'node_cap':{'rejection':rejection.status,'admission_calls':rejection.admission_calls,'preserved_tip':capped.tip.hex()},
            'absolute_bounds':{'validated_nodes':256,'depth':128,'pending':32,'trusted_peer_labels':16,'per_peer_queue':8,
                               'ttl_seconds':60,'per_peer_submissions_per_second':16,'drain_attempts':8,
                               'admission_calls_per_submission':129,'admission_calls_per_drain':1032,
                               'retained_wire_bytes':MAX_RETAINED_WIRE,'block_bytes':MAX_BLOCK},
            'limitations':['wire-byte ceiling excludes Python object/interpreter overhead',
                           'trusted finite labels are not Sybil-resistant peer identities',
                           'call counts are not CPU, energy or network throughput',
                           'full node requires pruning/persistence and real peer admission controls']}


def main():
    paths=begin_report('fork-resources-v1'); manifest=paths[2]
    finish_report(paths,probes(),manifest)


if __name__=='__main__': main()
