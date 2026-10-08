import unittest
from reference.chain import ChainPolicy
from reference.block import MAX_BLOCK
from reference.sis import Profile
from scripts.chain_driver import command,encode_policy,exchange_chain


class ChainDriverTests(unittest.TestCase):
    def setUp(self):
        self.p=ChainPolicy(bytes(32),Profile(7,1,3,8),2**255,bytes([1])*32,anchor_time=99)

    def test_canonical_policy_and_command_bounds(self):
        wire=encode_policy(self.p)
        self.assertEqual(len(wire),135)
        self.assertEqual(wire[:4],b'MCP1')
        self.assertEqual(wire[36:52],bytes.fromhex('07000000010003000800000000000000'))
        self.assertEqual(command(b'block',now=1),b'\x01\x01'+bytes(7)+b'block')
        for packet,now in ((b'x'*(MAX_BLOCK+1),0),(bytearray(),0),(b'',True),(b'',2**64)):
            with self.assertRaises(ValueError): command(packet,now=now)

    def test_bounded_consumption_stops_before_executable_invocation(self):
        count=0
        def endless():
            nonlocal count
            while True: count+=1; yield b'\x03'
        with self.assertRaises(ValueError): exchange_chain('not-an-executable',self.p,endless())
        self.assertEqual(count,8193)


if __name__=='__main__': unittest.main()
