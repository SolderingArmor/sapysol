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
# module: mass wallets token balance
#
# =============================================================================
# 
from   solana.rpc.api import Client, Pubkey, Keypair
from   typing         import List, Union
from   queue          import Queue, Empty
from ..helpers        import MakePubkey, SapysolPubkey
from ..token          import SapysolToken
from  .batcher        import SapysolBatcher
import time
import threading
import logging

# =============================================================================
# 
class SapysolWalletsBalance:
    def __init__(self,
                 connection:  Client,
                 pubkeysList: List[Pubkey],
                 tokenMint:   SapysolPubkey,
                 numThreads:  int  = 50):

        assert(all(isinstance(n, Pubkey) for n in pubkeysList))
        self.CONNECTION:   Client         = connection
        self.PUBKEYS_LIST: List[Pubkey]   = pubkeysList
        self.TOKEN:        SapysolToken   = SapysolToken(connection=connection, tokenMint=MakePubkey(tokenMint))
        self.SOL_MINT:     Pubkey         = MakePubkey("So11111111111111111111111111111111111111112")
        self.RESULTS:      dict           = {}
        self.MUTEX:        threading.Lock = threading.Lock()
        self.BATCHER:      SapysolBatcher = SapysolBatcher(callback    = self.CheckSingle,
                                                           entityList  = pubkeysList,
                                                           entityKwarg = "walletAddress",
                                                           numThreads  = numThreads)

    # ========================================
    #
    def CheckSingle(self, walletAddress: Pubkey):
        balance: int = self.TOKEN.GetWalletBalanceLamports(walletAddress=walletAddress)

        # Include SOL when we check WSOL
        if self.TOKEN.TOKEN_MINT == self.SOL_MINT:
            balance += self.CONNECTION.get_balance(pubkey=walletAddress).value

        with self.MUTEX:
            self.RESULTS[walletAddress] = balance

    # ========================================
    #
    def Start(self, **kwargs) -> dict:
        self.RESULTS = {}
        self.BATCHER.Start(**kwargs)
        return self.RESULTS

    # ========================================
    #
    def OutputPretty(self, 
                     ignoreEmpty:       bool = False,
                     balanceInLamports: bool = False) -> None:

        delimiter = 10**self.TOKEN.TOKEN_INFO.decimals
        # HEADER
        logging.info((2+44+3+32+2)*"-")
        logging.info(f"| {'WALLET':<44} | {'BALANCE':<32} |")
        logging.info((2+44+3+32+2)*"-")

        sum:          int = 0
        walletsFull:  int = 0
        walletsEmpty: int = 0
        for wallet, balance in self.RESULTS.items():
            sum += balance
            if balance > 0:
                walletsFull  += 1
            else:
                walletsEmpty += 1

            if balanceInLamports:
                if not ignoreEmpty or balance > 0:
                    logging.info(f"| {str(wallet):>44} | {balance:<32} |")
            else:
                if not ignoreEmpty or balance > 0:
                    logging.info(f"| {str(wallet):>44} | {balance/delimiter:<32} |")

        # FOOTER
        delimiter: int = 10**self.TOKEN.TOKEN_INFO.decimals
        logging.info((2+44+3+32+2)*"-")

        logging.info(f"Wallets with balance: {walletsFull}" )
        logging.info(f"Wallets empty:        {walletsEmpty}")
        if balanceInLamports:
            logging.info(f"TOKENS TOTAL (lamports): {sum}\n")
        else:
            logging.info(f"TOKENS TOTAL: {sum/delimiter}\n")

# =============================================================================
# 
