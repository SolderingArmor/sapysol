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
# module: wallet
#
# =============================================================================
# 
from   solana.rpc.api         import Client, Pubkey, Keypair, Commitment
from   solana.rpc.types       import TxOpts
from   solders.system_program import TransferParams, transfer
from   typing                 import List, Any, TypedDict, Union, Optional
from   dataclasses            import dataclass, field
from   datetime               import datetime
from   enum                   import Enum
from  .helpers                import MakePubkey, MakeKeypair, LAMPORTS_PER_SOL, ListToChunks
from  .tx                     import SapysolTxParams, SapysolTxStatus, SapysolTx, WaitForBatchTx
import base64
import logging
import time

# =============================================================================
#
class SapysolWalletReadonly:
    # ========================================
    #
    def __init__(self, connection: Client, pubkey: Union[str, bytes, Pubkey]):
        self.CONNECTION: Client  = connection
        self.PUBKEY:     Pubkey  = MakePubkey(pubkey)

    # ========================================
    #
    def GetBalanceLamports(self) -> int:
        balance = 0
        try: 
            balance = self.CONNECTION.get_balance(self.PUBKEY).value
        except KeyboardInterrupt as e:
            raise
        except:
            pass
        return balance

    # ========================================
    #
    def GetBalanceSol(self) -> float:
        return self.GetBalanceLamports() / LAMPORTS_PER_SOL

    # ========================================
    #


# =============================================================================
#
class SapysolWallet(SapysolWalletReadonly):
    def __init__(self, connection: Client, keypair: Union[str, Keypair]):
        self.CONNECTION: Client  = connection
        self.KEYPAIR:    Keypair = MakeKeypair(keypair)
        self.PUBKEY:     Pubkey  = self.KEYPAIR.pubkey()

    # ========================================
    #
    def SendLamportsBatch(self, destinationAddresses: List[str], lamports: int) -> List[SapysolTxStatus]:
        instructions = []
        txArray      = []
        for address in destinationAddresses:
            transferInstruction = transfer(params=TransferParams(from_pubkey=self.KEYPAIR.pubkey(), to_pubkey=MakePubkey(address), lamports=lamports))
            instructions.append(transferInstruction)

        # Empty transaction is 168 bytes, each SOL transfer is 49,
        # limit size is 1232 bytes, that leaves us with up to 21 SOL 
        # transfers per transaction.
        instructionsChunked = ListToChunks(baseList=instructions, chunkSize=20)
        for chunk in instructionsChunked:
            tx = SapysolTx(connection=self.CONNECTION, payer=self.KEYPAIR)
            tx.FromInstructionsLegacy(chunk)
            tx.Sign()
            txArray.append(tx)
        return WaitForBatchTx(txArray=txArray)

    # ========================================
    #
    def SendLamports(self, destinationAddress: str, lamports: int) -> SapysolTxStatus:
        return self.SendLamportsBatch(destinationAddresses=[destinationAddress], lamports=lamports)[0]

    # ========================================
    #
    def SendLamportsAll(self, destinationAddress: str) -> SapysolTxStatus:
        feeLamports:     int = 5000
        balanceLamports: int = self.GetBalanceLamports()
        if balanceLamports <= feeLamports:
            return SapysolTxStatus.SUCCESS

        return self.SendLamports(destinationAddress=destinationAddress, lamports=balanceLamports-feeLamports)

    # ========================================
    #
    def SendSolBatch(self, destinationAddresses: List[str], amountSol) -> List[SapysolTxStatus]:
        return self.SendLamportsBatch(destinationAddresses=destinationAddresses, lamports=int(amountSol*LAMPORTS_PER_SOL))

    def SendSol(self, destinationAddress, amountSol) -> SapysolTxStatus:
        return self.SendLamportsBatch(destinationAddresses=[destinationAddress], lamports=int(amountSol*LAMPORTS_PER_SOL))[0]

# =============================================================================
#
