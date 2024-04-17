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
from   solana.rpc.api    import Client, Pubkey, Keypair
from   solana.exceptions import SolanaRpcException
from   typing            import List, Union
from   queue             import Queue, Empty
from ..helpers           import MakePubkey, SapysolPubkey
from ..token             import SapysolToken
from ..jupag             import SapysolJupagParams, SapysolJupag
from ..tx                import SapysolTxParams, SapysolTxStatus, SapysolTx, SendAndWaitBatchTx
from  .batcher           import SapysolBatcher
import logging

logger = logging.getLogger("sapysol")

# =============================================================================
# 
class SapysolTokenSelloff:
    def __init__(self,
                 connection:         Client,
                 walletsList:        List[Keypair],
                 tokenToSell:        SapysolPubkey,
                 tokenToBuy:         SapysolPubkey,
                 balanceThreshold:   int = 0,
                 txParams:           SapysolTxParams          = SapysolTxParams(),
                 swapParams:         SapysolJupagParams       = SapysolJupagParams(),
                 connectionOverride: List[Union[str, Client]] = None,
                 numThreads:         int = 10):

        assert(all(isinstance(n, Keypair) for n in walletsList))
        self.CONNECTION:          Client                   = connection
        self.TOKEN_TO_SELL:       SapysolToken             = SapysolToken(connection=connection, tokenMint=MakePubkey(tokenToSell))
        self.TOKEN_TO_BUY:        SapysolToken             = SapysolToken(connection=connection, tokenMint=MakePubkey(tokenToBuy ))
        self.BALANCE_THRESHOLD:   int                      = balanceThreshold
        self.TX_PARAMS:           SapysolTxParams          = txParams
        self.SWAP_PARAMS:         SapysolJupagParams       = swapParams
        self.CONNECTION_OVERRIDE: List[Union[str, Client]] = connectionOverride
        self.BATCHER:             SapysolBatcher           = SapysolBatcher(callback    = self.SellSingle,
                                                                            entityList  = walletsList,
                                                                            entityKwarg = "wallet",
                                                                            numThreads  = numThreads)

    # ========================================
    #
    def SellSingle(self, wallet: Keypair):
        while True:
            balance:    int = self.TOKEN_TO_SELL.GetWalletBalanceLamports(walletAddress=wallet.pubkey())
            delimiter:  int = 10**self.TOKEN_TO_SELL.TOKEN_INFO.decimals
            balanceStr: str = f"{0:>{self.TOKEN_TO_SELL.TOKEN_INFO.decimals+2}}" if balance == 0 else f"{balance / delimiter:.{self.TOKEN_TO_SELL.TOKEN_INFO.decimals}f}"
            if balance <= self.BALANCE_THRESHOLD:
                logger.info(f"Wallet: {str(wallet.pubkey()):>44}; balance: {balanceStr}, skipping...")
                break
            else:
                logger.info(f"Wallet: {str(wallet.pubkey()):>44}; balance: {balanceStr}, trying to sell all...")

            quote = SapysolJupag.GetSwapQuote(connection = self.CONNECTION,
                                              tokenFrom  = self.TOKEN_TO_SELL.TOKEN_MINT,
                                              tokenTo    = self.TOKEN_TO_BUY.TOKEN_MINT,
                                              inAmount   = balance,
                                              swapParams = self.SWAP_PARAMS)
            txb64         = SapysolJupag.GetSwapTxBase64(walletAddress=wallet.pubkey(), coinQuote=quote, swapParams=self.SWAP_PARAMS)
            tx: SapysolTx = SapysolTx(connection=self.CONNECTION, payer=wallet, txParams=self.TX_PARAMS)
            tx.FromBase64(b64=txb64)
            result: SapysolTxStatus = tx.Sign([wallet]).SendAndWait(self.CONNECTION_OVERRIDE)
            if result == SapysolTxStatus.SUCCESS:
                break

    # ========================================
    #
    def Start(self, **kwargs) -> None:
        self.BATCHER.Start(**kwargs)

# =============================================================================
# 
