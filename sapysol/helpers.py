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
from   solana.rpc.api        import Client, Pubkey, Keypair, Commitment
from   solana.rpc.commitment import Commitment
from   solders.account       import Account, AccountJSON
from   typing                import List, Any, Union
from   pybip39               import Mnemonic, Seed
import logging
import json
import os

# ================================================================================
#
LAMPORTS_PER_SOL:          int    = 1_000_000_000
METADATA_PROGRAM_ID:       Pubkey = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s" )
SYSTEM_PROGRAM_ID:         Pubkey = Pubkey.from_string("11111111111111111111111111111111"            )
SYSVAR_RENT_PUBKEY:        Pubkey = Pubkey.from_string("SysvarRent111111111111111111111111111111111" )
SYSVAR_CLOCK_PUBKEY:       Pubkey = Pubkey.from_string("SysvarC1ock11111111111111111111111111111111" )
SYSVAR_SLOT_HASHES_PUBKEY: Pubkey = Pubkey.from_string("SysvarS1otHashes111111111111111111111111111" )
TOKEN_2022_PROGRAM_ID:     Pubkey = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb" )
# Address of the special mint for wrapped native SOL in spl-token-2022 */
NATIVE_MINT_2022:          Pubkey = Pubkey.from_string("9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP")

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
def ListToChunks(baseList: List[Any], chunkSize: int) -> List[List[Any]]:
    result = []
    chunks = baseList
    while chunks:
        chunk, chunks = chunks[:chunkSize], chunks[chunkSize:]
        result.append(chunk)
    return result

# ================================================================================
# Either Pubkey string or Pubkey or anything that can be a Pubkey
#
SapysolPubkey = Union[str, bytes, Keypair, Pubkey]
#
def MakePubkey(pubkey: SapysolPubkey) -> Pubkey:
    if pubkey is None:
        return None

    if isinstance(pubkey, Pubkey):
        return pubkey
    if isinstance(pubkey, Keypair):
        return pubkey.pubkey()
    elif isinstance(pubkey, bytes):
        return Pubkey.from_bytes(pubkey)
    elif isinstance(pubkey, str):
        try: 
            return Pubkey.from_string(pubkey)
        except:
            return Pubkey.from_json(pubkey)
    return None

# ================================================================================
# Either Keypair JSON file path or Keypair or anything that can be a Keypair
#
SapysolKeypair = Union[str, bytes, Keypair]
#
def MakeKeypair(keypair: SapysolKeypair) -> Keypair:
    if keypair is None:
        return None

    if isinstance(keypair, Keypair):
        return keypair
    elif isinstance(keypair, bytes):
        return Keypair.from_bytes(keypair)
    elif isinstance(keypair, str):
        # First try to load file
        try:
            with open(keypair) as f:
                result = json.loads(f.read())
                return Keypair.from_bytes(result)
        except:
            pass
        # Second - maybe it is a mnemonic?
        try:
            mnemonic = Mnemonic.from_phrase(keypair)
            seed     = Seed(mnemonic=mnemonic, password="")
            return Keypair.from_seed_and_derivation_path(seed=bytes(seed), dpath="m/44'/501'/0'/0'")
        except:
            pass
        # Third - maybe it is already a json?
        try: 
            return Keypair.from_json(keypair)
        except:
            pass
    return None

# ================================================================================
#
def GetFilesFromPath(path: str, endsWith: str=".json") -> List[str]:
    files = os.listdir(path)
    return [os.path.join(dir, f) for f in files if os.path.isfile(os.path.join(dir, f)) and f.lower().endswith(endsWith)]

def GetKeypairsFromPath(path: str, endsWith: str=".json") -> List[Keypair]:
    files    = GetFilesFromPath(path=path, endsWith=endsWith)
    keypairs = [MakeKeypair(f) for f in files]
    return keypairs

def GetPubkeysFromKeypairs(keypairList: List[SapysolKeypair]) -> List[Pubkey]:
    return [ MakeKeypair(x).pubkey() for x in keypairList ]

# ================================================================================
#
def FetchAccounts(connection:    Client, 
                  pubkeys:       List[SapysolPubkey],
                  chunkSize:     int           = 100,
                  requiredOwner: SapysolPubkey = None,
                  commitment:    Commitment    = None,
                  parseToJson:   bool          = False) -> Union[List[Account], List[AccountJSON]]:
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
                 pubkey:        SapysolPubkey,
                 requiredOwner: SapysolPubkey = None,
                 commitment:    Commitment    = None,
                 parseToJson:   bool          = False) -> Union[Account, AccountJSON]:
    return FetchAccounts(connection    = connection,
                         pubkeys       = [pubkey],
                         requiredOwner = requiredOwner,
                         commitment    = commitment,
                         parseToJson   = parseToJson)[0]


# ===============================================================================
# 
def DivmodJsBignumber(dividend, divisor) -> tuple[int, int]:
    """
    Performs division to replicate JavaScript's division behavior accurately,
    with quotient rounding towards zero and appropriate remainder calculation.
    
    :param dividend: The number to be divided.
    :param divisor: The number by which to divide.
    :return: A tuple (quotient, remainder) accurately mimicking JavaScript behavior.
    """
    if divisor == 0:
        raise ValueError("Divisor cannot be zero.")
    
    quotient  = dividend // divisor
    remainder = dividend %  divisor
    
    # Ensure remainder has the same sign as the divisor
    if remainder != 0 and (dividend < 0) != (divisor < 0):
        quotient += 1
        remainder = remainder - divisor

    return quotient, remainder

# ================================================================================
#
# TODO: arweave https://github.com/Irys-xyz/gasless-uploader/blob/master/app/api/lazyFundSOL/route.ts