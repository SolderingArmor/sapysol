#!/usr/bin/python
# =============================================================================
#
#  ######     ###    ########  ##    ##  ######   #######  ##       
# ##    ##   ## ##   ##     ##  ##  ##  ##    ## ##     ## ##       
# ##        ##   ##  ##     ##   ####   ##       ##     ## ##       
#  ######  ##     ## ########     ##     ######  ##     ## ##       
#       ## ######### ##           ##          ## ##     ## ##       
# ##    ## ##     ## ##           ##    ##    ## ##     ## ##       
#  ######  ##     ## ##           ##     ######   #######  ########
#
# =============================================================================
#
# SuperArmor's Python Solana library.
# (c) SuperArmor
#
# module: SysvarClock
# https://docs.solanalabs.com/runtime/sysvars
#
# =============================================================================
# 
import typing
from   dataclasses           import dataclass
from   solana.rpc.api        import Client
from   solana.rpc.commitment import Commitment
import borsh_construct       as borsh
from ..helpers               import SYSVAR_CLOCK_PUBKEY, FetchAccount
#from   solders.clock  import Clock as SysvarClock
#from   solders.sysvar import CLOCK as SYSVAR_CLOCK_PUBKEY

# =============================================================================
# 
class SysvarClockJSON(typing.TypedDict):
    slot:                  int
    epoch_start_timestamp: int
    epoch:                 int
    leader_schedule_epoch: int
    unix_timestamp:        int

# =============================================================================
# 
@dataclass
class SysvarClock:
    layout: typing.ClassVar = borsh.CStruct(
        "slot"                  / borsh.U64,
        "epoch_start_timestamp" / borsh.I64,
        "epoch"                 / borsh.U64,
        "leader_schedule_epoch" / borsh.U64,
        "unix_timestamp"        / borsh.I64,
    )
    slot:                  int
    epoch_start_timestamp: int
    epoch:                 int
    leader_schedule_epoch: int
    unix_timestamp:        int

    # ========================================
    #
    @classmethod
    def fetch(cls,
              conn:       Client,
              commitment: typing.Optional[Commitment] = None) -> typing.Optional["SysvarClock"]:

        resp = FetchAccount(connection    = conn, 
                            pubkey        = SYSVAR_CLOCK_PUBKEY,
                            commitment    = commitment)
        return None if resp is None else cls.decode(resp.data)

    # ========================================
    #
    @classmethod
    def decode(cls, data: bytes) -> "SysvarClock":
        dec = SysvarClock.layout.parse(data)
        return cls(slot                  = dec.slot,
                   epoch_start_timestamp = dec.epoch_start_timestamp,
                   epoch                 = dec.epoch,
                   leader_schedule_epoch = dec.leader_schedule_epoch,
                   unix_timestamp        = dec.unix_timestamp)

    # ========================================
    #
    def to_json(self) -> SysvarClockJSON:
        return {
            "slot":                  self.slot,
            "epoch_start_timestamp": self.epoch_start_timestamp,
            "epoch":                 self.epoch,
            "leader_schedule_epoch": self.leader_schedule_epoch,
            "unix_timestamp":        self.unix_timestamp,
        }

    # ========================================
    #
    @classmethod
    def from_json(cls, obj: SysvarClockJSON) -> "SysvarClock":
        return cls(
            slot                  = obj["slot"],
            epoch_start_timestamp = obj["epoch_start_timestamp"],
            epoch                 = obj["epoch"],
            leader_schedule_epoch = obj["leader_schedule_epoch"],
            unix_timestamp        = obj["unix_timestamp"],
        )

# =============================================================================
# 
