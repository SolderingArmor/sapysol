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
# module: mass token sell (dump) via Jupiter
#
# =============================================================================
# 
from   solana.rpc.api import Client, Pubkey, Keypair
from   typing         import List, Union
from   queue          import Queue, Empty
from ..helpers        import MakePubkey
from ..token          import SapysolToken
from ..jupag          import SapysolJupagParams, SapysolJupag
from ..tx             import SapysolTxParams, SapysolTxStatus, SapysolTx, WaitForBatchTx
from  .batcher        import SapysolBatcher
import logging

# =============================================================================
# 
class SapysolTokenSelloff:
    def __init__(self,
                 connection:  Client,
                 walletsList: List[Keypair],
                 tokenToSell: Union[str, Pubkey],
                 tokenToBuy:  Union[str, Pubkey],
                 txParams:    SapysolTxParams    = SapysolTxParams(),
                 swapParams:  SapysolJupagParams = SapysolJupagParams(),
                 numThreads:  int                = 10):

        assert(all(isinstance(n, Keypair) for n in walletsList))

        self.CONNECTION:    Client             = connection
        self.TOKEN_TO_SELL: SapysolToken       = SapysolToken(connection=connection, tokenMint=MakePubkey(tokenToSell))
        self.TOKEN_TO_BUY:  SapysolToken       = SapysolToken(connection=connection, tokenMint=MakePubkey(tokenToBuy ))
        self.TX_PARAMS:     SapysolTxParams    = txParams
        self.SWAP_PARAMS:   SapysolJupagParams = swapParams
        self.BATCHER:       SapysolBatcher     = SapysolBatcher(callback    = self.SellSingle,
                                                                entityList  = walletsList,
                                                                entityKwarg = "wallet",
                                                                numThreads  = numThreads)

    # ========================================
    #
    def SellSingle(self, wallet: Keypair):
        assert(isinstance(wallet, Keypair))
        while True:
            balance   = self.TOKEN_TO_SELL.GetWalletBalanceLamports(walletAddress=wallet.pubkey())
            delimiter = 10**self.TOKEN_TO_SELL.TOKEN_INFO.decimals
            if balance <= 0:
                logging.info(f"Wallet: {str(wallet.pubkey()):>44}; balance: 0, skipping...")
                break
            else:
                logging.info(f"Wallet: {str(wallet.pubkey()):>44}; balance: {balance / delimiter}, trying to sell all...")

            quote = SapysolJupag.GetSwapQuote(connection = self.CONNECTION,
                                              tokenFrom  = self.TOKEN_TO_SELL.TOKEN_MINT,
                                              tokenTo    = self.TOKEN_TO_BUY.TOKEN_MINT,
                                              inAmount   = balance,
                                              swapParams = self.SWAP_PARAMS)
            txb64         = SapysolJupag.GetSwapTxBase64(walletAddress=wallet.pubkey(), coinQuote=quote, swapParams=self.SWAP_PARAMS)
            tx: SapysolTx = SapysolTx(connection=self.CONNECTION, payer=wallet, txParams=self.TX_PARAMS)
            tx.FromBase64(b64=txb64)
            result: SapysolTxStatus = tx.Sign([wallet]).WaitForTx()
            if result == SapysolTxStatus.SUCCESS:
                break

    # ========================================
    #
    def Start(self) -> None:
        self.BATCHER.Start()

    # ========================================
    #
    def IsDone(self) -> bool:
        return self.BATCHER.IsDone()

# =============================================================================
# 
