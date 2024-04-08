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
# module: token
#
# =============================================================================
# 
from   solders.account        import Account
from   solana.rpc.api         import Client, Pubkey, Keypair
from   spl.token.client       import Token
from   spl.token.constants    import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
from   solana.rpc.types       import TxOpts
from   solana.transaction     import Transaction, Signature, Instruction
from   sapysol.helpers        import LAMPORTS_PER_SOL, MakePubkey, MakeKeypair
from   typing                 import List, Any, TypedDict, Union, Optional
from   spl.token.instructions import get_associated_token_address
from   spl.token.core         import AccountInfo, MintInfo, _TokenCore
from  .ix                     import *
from  .tx                     import *
from  .helpers                import MakePubkey, MakeKeypair, NestedAttributeExists, ListToChunks
from  .token_cache            import TokenCacheEntry, TokenCache

import solders.system_program as sp

from solders.rpc.errors import  InvalidParamsMessage
from solders.rpc.responses import RpcKeyedAccountJsonParsed
from solders.account import AccountJSON
from spl.token._layouts import ACCOUNT_LAYOUT, MINT_LAYOUT, MULTISIG_LAYOUT  # type: ignore
import spl.token.instructions as spl_token
import os
import logging


# =============================================================================
# 
class SapysolToken:
    # ========================================
    #
    def __init__(self, connection: Client, tokenMint: SapysolPubkey):
        self.CONNECTION:    Client          = connection
        self.TOKEN_MINT:    Pubkey          = MakePubkey(tokenMint)
        self.TOKEN_INFO:    TokenCacheEntry = TokenCache.GetToken(connection=connection, tokenMint=tokenMint)
        self.TOKEN:         Token           = Token(conn=connection, pubkey=self.TOKEN_MINT, program_id=self.TOKEN_INFO.program_id, payer=None)

    # ========================================
    #
    def AccountExists(self, accountAddress: SapysolPubkey) -> bool:
        pubkey: Pubkey  = MakePubkey(accountAddress)
        result: Account = self.CONNECTION.get_account_info(pubkey=pubkey).value
        return result is not None

    # ========================================
    #
    def GetAccountBalanceLamports(self, accountAddress: SapysolPubkey):
        pubkey: Pubkey = MakePubkey(accountAddress)
        result = self.TOKEN.get_balance(pubkey=pubkey)
        if isinstance(result, InvalidParamsMessage):
            return 0
        return int(result.value.amount)

    # ========================================
    #
    def GetAccountBalance(self, accountAddress: SapysolPubkey) -> float:
        balance: int = self.GetAccountBalanceLamports(accountAddress)
        return balance / 10**self.TOKEN_INFO.decimals

    # ========================================
    #
    def GetWalletAta(self, walletAddress: SapysolPubkey) -> Pubkey:
        pubkey: Pubkey = MakePubkey(walletAddress)
        return get_associated_token_address(owner=pubkey, mint=self.TOKEN_MINT)
    
    # ========================================
    #
    def CreateWalletAtaBatch(self, walletAddresses: List[SapysolPubkey], payer: Union[str, Keypair]) -> List[Pubkey]:
        # Empty transaction is 168 bytes, each ATA creation is 138,
        # limit size is 1232 bytes, that leaves us with up to 7 ATA
        # creations per transaction.
        ixNeeded:      List[Instruction] = []
        resultPubkeys: List[Pubkey]      = []
        for walletAddress in walletAddresses:
            ataIx: AtaInstruction = GetOrCreateAtaIx(connection=self.CONNECTION, tokenMint=self.TOKEN_MINT, owner=MakePubkey(walletAddress))
            resultPubkeys.append(ataIx.pubkey)
            if ataIx.ix:
                ixNeeded.append(ataIx.ix)

        # TODO: change to dynamic size:
        # TODO: if one wallet is sending tokens to multiple wallets, each instruction takes less space

        chunks = ListToChunks(baseList=ixNeeded, chunkSize=7)
        txArray: List[SapysolTx] = []
        for chunk in chunks:
            tx: SapysolTx = SapysolTx(connection=self.CONNECTION, payer=payer)
            tx.FromInstructionsLegacy(instructions=chunk)
            tx.Sign()
        SendAndWaitBatchTx(txArray=txArray)
        return resultPubkeys
    
    # ========================================
    #
    def CreateWalletAta(self, 
                        walletAddress: SapysolPubkey, 
                        payer:         SapysolKeypair) -> Pubkey:
        ataIx: AtaInstruction = GetOrCreateAtaIx(connection=self.CONNECTION, tokenMint=self.TOKEN_MINT, owner=MakePubkey(walletAddress))
        if not ataIx.ix:
            return ataIx.pubkey
        tx: SapysolTx = SapysolTx(connection=self.CONNECTION, payer=payer)
        tx.FromInstructionsLegacy(instructions=ataIx.ix)
        tx.Sign().SendAndWait()
        return ataIx.pubkey

    # ========================================
    #
    def GetWalletAccountAddresses(self, walletAddress: SapysolPubkey) -> List[Pubkey]:
        owner: Pubkey = MakePubkey(walletAddress)
        accounts = self.TOKEN.get_accounts_by_owner_json_parsed(owner=owner)
        account: RpcKeyedAccountJsonParsed
        return [account.pubkey for account in accounts.value]

    # ========================================
    #
    def GetWalletBalanceLamports(self, walletAddress: SapysolPubkey) -> int:
        accountAddress: Pubkey = self.GetWalletAta(walletAddress)
        return self.GetAccountBalanceLamports(accountAddress=accountAddress)

    # ========================================
    #
    def GetWalletBalance(self, walletAddress: SapysolPubkey) -> float:
        accountAddress: Pubkey = self.GetWalletAta(walletAddress)
        return self.GetAccountBalance(accountAddress=accountAddress)

    # ========================================
    #
    def UpdateAuthority(self, newAuthority: Pubkey, payer: SapysolKeypair):
        pass # TODO

    def Mint(self):
        pass # TODO

    def Burn(self):
        pass # TODO

    def Freeze(self):
        pass # TODO

    def Thaw(self):
        pass # TODO

    # ========================================
    #
    def TransferBatch(self):
        pass # TODO

    def Transfer(self):
        pass # TODO

# =============================================================================
# 
