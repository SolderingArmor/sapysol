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
# module: cache
#
# =============================================================================
# 
from   solders.account        import Account, AccountJSON
from   solders.rpc.errors     import InvalidParamsMessage
from   solders.rpc.responses  import RpcKeyedAccountJsonParsed
from   spl.token.client       import Token
from   spl.token.core         import AccountInfo, MintInfo, _TokenCore
from   solana.rpc.api         import Client, Pubkey, Keypair
from   solana.rpc.types       import TxOpts
from   solana.transaction     import Transaction, Signature, Instruction
from   typing                 import List, Any, TypedDict, Union, Optional
from  .tx                     import *
from  .helpers                import *
from  .ix                     import *
import os
import logging

# =============================================================================
# 
SAPYSOL_TOKEN_VERSION: int = 1

# =============================================================================
# 
class TokenCacheEntry(NamedTuple):
    SAPYSOL_TOKEN_VERSION:  int    #
    token_mint:             Pubkey #
    mint_authority:         Pubkey #
    supply:                 int    #
    decimals:               int    #
    is_initialized:         bool   #
    freeze_authority:       Pubkey #
    program_id:             Pubkey #

class TokenCache:
    # ========================================
    #
    @staticmethod
    def __TokenCachePath() -> str:
        path = os.path.join(os.getenv("HOME"), ".sapysol", "tokens")
        EnsurePathExists(path)
        return path

    @staticmethod
    def __TokenFilename(tokenMint: SapysolPubkey) -> str:
        return os.path.join(TokenCache.__TokenCachePath(), f"{MakePubkey(tokenMint)}.json")

    # ========================================
    #
    @staticmethod
    def __LoadFromFile(tokenMint: SapysolPubkey) -> TokenCacheEntry:
        try:
            tokenCachePath: str = TokenCache.__TokenCachePath()
            tokenInfoFile:  str = TokenCache.__TokenFilename(tokenMint=tokenMint)
            logging.debug(f"Loading token info from file: {tokenInfoFile}")
            if not os.path.isfile(tokenInfoFile):
                return None
            with open(tokenInfoFile) as f:
                tokenInfoJson = json.load(f)
                if "SAPYSOL_TOKEN_VERSION" not in tokenInfoJson:
                    return None
                if tokenInfoJson["SAPYSOL_TOKEN_VERSION"] < SAPYSOL_TOKEN_VERSION:
                    return None

                tokenEntry = TokenCacheEntry(SAPYSOL_TOKEN_VERSION =            tokenInfoJson["SAPYSOL_TOKEN_VERSION"],
                                             token_mint            = MakePubkey(tokenInfoJson["token_mint"]),
                                             mint_authority        = MakePubkey(tokenInfoJson["mint_authority"]),
                                             supply                =            tokenInfoJson["supply"],
                                             decimals              =            tokenInfoJson["decimals"],
                                             is_initialized        =            tokenInfoJson["is_initialized"],
                                             freeze_authority      = MakePubkey(tokenInfoJson["freeze_authority"]),
                                             program_id            = MakePubkey(tokenInfoJson["program_id"]))
                return tokenEntry
        except:
            return None

    # ========================================
    #
    @staticmethod
    def __LoadFromBlockchain(connection: Client, tokenMint: SapysolPubkey) -> TokenCacheEntry:
        tokenCachePath: str = TokenCache.__TokenCachePath()
        tokenInfoFile:  str = TokenCache.__TokenFilename(tokenMint=tokenMint)

        logging.debug(f"Loading token info from Solana Node for token: {str(tokenMint)}")
        accountInfo: Account  = connection.get_account_info(pubkey=MakePubkey(tokenMint)).value
        mintInfo:    MintInfo = Token(conn       = connection, 
                                      pubkey     = MakePubkey(tokenMint),
                                      program_id = accountInfo.owner, 
                                      payer      = None).get_mint_info()
        
        with open(tokenInfoFile, "w") as f:
            tokenMint:   str = str(tokenMint)                  if tokenMint                 else None
            mintAuthStr: str = str(mintInfo.mint_authority)    if mintInfo.mint_authority   else None
            freezeStr:   str = str(mintInfo.freeze_authority)  if mintInfo.freeze_authority else None
            ownerStr:    str = str(accountInfo.owner)          if accountInfo.owner         else None
            json.dump({
                "SAPYSOL_TOKEN_VERSION": SAPYSOL_TOKEN_VERSION,   #
                "token_mint":            str(tokenMint),          #
                "mint_authority":        mintAuthStr,             #
                "supply":                mintInfo.supply,         #
                "decimals":              mintInfo.decimals,       #
                "is_initialized":        mintInfo.is_initialized, #
                "freeze_authority":      freezeStr,               #
                "program_id":            ownerStr,                #
            }, f)
        return TokenCacheEntry(SAPYSOL_TOKEN_VERSION = SAPYSOL_TOKEN_VERSION,
                               token_mint            = tokenMint,
                               mint_authority        = mintInfo.mint_authority,
                               supply                = mintInfo.supply,
                               decimals              = mintInfo.decimals,
                               is_initialized        = mintInfo.is_initialized,
                               freeze_authority      = mintInfo.freeze_authority,
                               program_id            = accountInfo.owner)

    # ========================================
    #
    @staticmethod
    def UpdateTokenCache(connection: Client, tokenMint: SapysolPubkey) -> TokenCacheEntry:
        return TokenCache.__LoadFromBlockchain(connection=connection, tokenMint=tokenMint)

    @staticmethod
    def GetToken(connection: Client, tokenMint: SapysolPubkey) -> TokenCacheEntry:
        tokenInfo = TokenCache.__LoadFromFile(tokenMint=tokenMint)
        return tokenInfo if tokenInfo else TokenCache.__LoadFromBlockchain(connection=connection, tokenMint=tokenMint)

# =============================================================================
# 
