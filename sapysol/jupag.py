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
# module: jupag
#
# =============================================================================
# 
from  .helpers        import *
from  .token_cache    import TokenCacheEntry, TokenCache
from   solana.rpc.api import Client, Pubkey, Keypair
from   typing         import List, Any, TypedDict, Union, Literal
from   dataclasses    import dataclass
import logging
import requests

# =============================================================================
# 
@dataclass
class SapysolJupagParams:
    # Quote
    swapMode:                Literal["ExactIn", "ExactOut"] = "ExactIn"
    slippageBps:             int  = 50 # 50 = 0.5%
    onlyDirectRoutes:        bool = False
    asLegacyTransaction:     bool = False
    # Tx
    quoteAutoMultiplier:     int  = 1
    quotePrioFeeLamports:    str  = "auto"
    wrapAndUnwrapSol:        bool = True
    dynamicComputeUnitLimit: bool = True

# =============================================================================
# 
class SapysolJupag:
    # ========================================
    # 
    @staticmethod
    def GetSwapQuote(connection:          Client,
                     tokenFrom:           str, 
                     tokenTo:             str, 
                     inAmount:            float, 
                     desiredOutAmount:    float = None,
                     inAmountInLamports:  bool  = True, 
                     outAmountInLamports: bool  = True, 
                     swapParams:          SapysolJupagParams = SapysolJupagParams()
                    ) -> dict:
        FROM: TokenCacheEntry = TokenCache.GetToken(connection=connection, tokenMint=tokenFrom)
        TO:   TokenCacheEntry = TokenCache.GetToken(connection=connection, tokenMint=tokenTo  )

        finalInAmount = int(inAmount) if inAmountInLamports else int(inAmount * 10**FROM.decimals)
        paramsQuote = {
            "inputMint":           str(FROM.token_mint),
            "outputMint":          str(TO.token_mint),
            "amount":              finalInAmount,
            "swapMode":            swapParams.swapMode,
            "slippageBps":         swapParams.slippageBps,
            "onlyDirectRoutes":    "true" if swapParams.onlyDirectRoutes    else "false", # For some weird reason Python's `bool` can't be parsed here correctly, looks like JupAg parses it as str
            "asLegacyTransaction": "true" if swapParams.asLegacyTransaction else "false", # For some weird reason Python's `bool` can't be parsed here correctly, looks like JupAg parses it as str
        }
        coinQuote = requests.get(url="https://quote-api.jup.ag/v6/quote", params=paramsQuote).json()

        if "error" in coinQuote:
            if coinQuote["error"] in ["Could not find any route", "The route plan does not consume all the amount, please lower your amount"]:
                logging.warning(f"Swap {str(tokenFrom)} to {str(tokenTo)}: NO ROUTES; bailing...")
                return None
            else:
                logging.warning(f"Swap {str(tokenFrom)} to {str(tokenTo)}: UNKNOWN ERROR; bailing...")
                logging.warning(coinQuote["error"])
                return None

        outLamports = int(coinQuote["outAmount"])
        outAmount   = outLamports / 10**(TO.decimals)

        # Check desired amount, should be at least that
        if desiredOutAmount:
            finalDesiredOutAmountLamports = int(desiredOutAmount) if outAmountInLamports else int(desiredOutAmount * 10**TO.decimals)
            finalDesiredOutAmount         = int(desiredOutAmount) if outAmountInLamports else int(desiredOutAmount * 10**TO.decimals)
            if outLamports < finalDesiredOutAmountLamports:
                logging.warning(f"{tokenTo} desiredOutAmount: {round(finalDesiredOutAmount, 4):.4f} and outAmount: {round(outAmount, 4):.4f}! bailing...")
                return None

        logging.debug(f"Selling {inAmount} of {tokenFrom} for {outAmount} of {tokenTo}...")
        return coinQuote

    # ========================================
    # 
    @staticmethod
    def GetSwapTxBase64(walletAddress: SapysolPubkey,
                        coinQuote:     dict,
                        swapParams:    SapysolJupagParams = SapysolJupagParams()
                       ) -> str:
        paramsSwap = {
            "quoteResponse":             coinQuote,
            "userPublicKey":             str(walletAddress),
            "wrapAndUnwrapSol":          swapParams.wrapAndUnwrapSol,
            "autoMultiplier":            swapParams.quoteAutoMultiplier,     # will 2x of the auto fees
            "dynamicComputeUnitLimit":   swapParams.dynamicComputeUnitLimit, # allow dynamic compute limit instead of max 1,400,000
            "prioritizationFeeLamports": swapParams.quotePrioFeeLamports     # or custom lamports: 1000
        }
        tx = requests.post(url = "https://quote-api.jup.ag/v6/swap", json=paramsSwap).json()
        if not "swapTransaction" in tx:
            logging.warning(f"tx: {tx}")
            logging.warning(f"No swapTransaction in tx! bailing...")
            return None
        return tx["swapTransaction"]

# =============================================================================
# 
