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
# module: helpers
#
# =============================================================================
# 
from   solana.rpc.api                       import Client, Pubkey, Keypair, Commitment
from   solana.rpc.commitment                import Commitment
from   spl.token.client                     import Token
from   spl.token.constants                  import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
from   sapysol                              import *
from   solders.account                      import Account, AccountJSON
from   solders.transaction                  import VersionedTransaction, Signer
from   solders.address_lookup_table_account import  AddressLookupTableAccount
from   solders.transaction_status           import EncodedTransactionWithStatusMeta
from   typing                               import List, Any, TypedDict, Union, Optional, TypeAlias
from   solana.transaction                   import Transaction, Signature, Instruction
from   solders.message                      import to_bytes_versioned, MessageV0
from   solders.rpc.responses                import RpcBlockhash
from   dataclasses                          import dataclass, field
from   datetime                             import datetime
from   enum                                 import Enum
import json
import logging
import os

# ================================================================================
#
LAMPORTS_PER_SOL:      int    = 1_000_000_000
METADATA_PROGRAM_ID:   Pubkey = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s" )
SYSTEM_PROGRAM_ID:     Pubkey = Pubkey.from_string("11111111111111111111111111111111"            )
SYSVAR_RENT_PUBKEY:    Pubkey = Pubkey.from_string("SysvarRent111111111111111111111111111111111" )
TOKEN_2022_PROGRAM_ID: Pubkey = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb" )
# Address of the special mint for wrapped native SOL in spl-token-2022 */
NATIVE_MINT_2022:      Pubkey = Pubkey.from_string("9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP")

# ================================================================================
# Create path if it doesn't exist
#
def EnsurePathExists(path: str):
    if path == "":
        return
    if not os.path.exists(path):
        os.makedirs(path, exist_ok = True)

# ================================================================================
#
def SetupLogging(fileName: str = "log.log",
                 format:   str = "%(name)s: %(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(process)d >>> %(message)s",
                 dateFmt:  str = "%Y-%m-%dT%H:%M:%SZ",
                 logLevel: int = logging.INFO):
    EnsurePathExists(os.path.dirname(fileName))
    logging.basicConfig(filename=fileName, filemode="a", format=format, datefmt=dateFmt, level=logLevel)
    logging.getLogger().addHandler(logging.StreamHandler())

# ================================================================================
#
def NestedAttributeExists(target: object, attributePath: str) -> bool:
    parts = attributePath.split(".")
    while parts:
       next, parts = parts[0], parts[1:]
       target = getattr(target, next)
       if target is None:
           return False
    return True

# ================================================================================
# 
def GetModulePath(fileName = __file__) -> str:
    return os.path.dirname(os.path.realpath(fileName))

# ================================================================================
# 
def ListToChunks(baseList: List[Any], chunkSize: int):
    result = []
    chunks = baseList
    while chunks:
        chunk, chunks = chunks[:chunkSize], chunks[chunkSize:]
        result.append(chunk)
    return result

# ================================================================================
# Either Pubkey string or Pubkey
def MakePubkey(pubkey: Union[str, bytes, Pubkey]) -> Pubkey:
    if pubkey is None:
        return None

    if isinstance(pubkey, Pubkey):
        return pubkey
    elif isinstance(pubkey, bytes):
        return Pubkey.from_bytes(pubkey)
    elif isinstance(pubkey, str):
        try: 
            return Pubkey.from_string(pubkey)
        except:
            return Pubkey.from_json(pubkey)
    return None

# ================================================================================
# Either Keypair JSON file path or Keypair
def MakeKeypair(keypair: Union[str, bytes, Keypair]) -> Keypair:
    if keypair is None:
        return None

    if isinstance(keypair, Keypair):
        return keypair
    elif isinstance(keypair, bytes):
        return Keypair.from_bytes(keypair)
    elif isinstance(keypair, str):
        try: 
            return Keypair.from_json(keypair)
        except:
            with open(keypair) as f:
                result = json.loads(f.read())
                return Keypair.from_bytes(result)
    return None

# ================================================================================
#
def FetchAccounts(connection:    Client, 
                  pubkeys:       List[Union[str, bytes, Pubkey]],
                  chunkSize:     int = 100,
                  requiredOwner: Union[str, bytes, Pubkey] = None,
                  commitment:    Commitment = None,
                  parseToJson:   bool = False) -> Union[List[Account], List[AccountJSON]]:
    results = []
    _pubkeys: List[Pubkey]       = [MakePubkey(pk) for pk in pubkeys]
    chunks:   List[List[Pubkey]] = ListToChunks(baseList=_pubkeys, chunkSize=chunkSize)
    func = connection.get_multiple_accounts_json_parsed if parseToJson else connection.get_multiple_accounts
    for chunk in chunks:
        entries: List[Account] = func(pubkeys=chunk, commitment=commitment).value
        if requiredOwner is not None and not all(e is None or (e.owner==requiredOwner) for e in entries):
            raise ValueError("Account does not belong to this program!")
        results += entries
    return results

# ================================================================================
#
def FetchAccount(connection:    Client, 
                 pubkey:        Union[str, bytes, Pubkey],
                 requiredOwner: Union[str, bytes, Pubkey] = None,
                 commitment:    Commitment = None,
                 parseToJson:   bool = False) -> Union[Account, AccountJSON]:
    return FetchAccounts(connection    = connection,
                         pubkeys       = [pubkey],
                         requiredOwner = requiredOwner,
                         commitment    = commitment,
                         parseToJson   = parseToJson)[0]

# ================================================================================
#
# TODO: arweave https://github.com/Irys-xyz/gasless-uploader/blob/master/app/api/lazyFundSOL/route.ts