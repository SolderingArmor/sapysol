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
# module: instructions
#
# =============================================================================
# 
from   solana.rpc.api         import Client, Pubkey, Keypair
from   solana.transaction     import Instruction
from   solders.system_program import transfer
from   solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from   spl.token.constants    import WRAPPED_SOL_MINT as NATIVE_MINT, TOKEN_PROGRAM_ID
from   spl.token.instructions import get_associated_token_address, create_associated_token_account, close_account, sync_native, CloseAccountParams, SyncNativeParams
import spl.token.instructions as     splToken
from   typing                 import List, Any, TypedDict, Union, Optional, NamedTuple
from  .helpers                import MakePubkey, MakeKeypair, SapysolPubkey
from  .token_cache            import TokenCacheEntry, TokenCache

# ===============================================================================
# Creating ATA takes 138 bytes per instruction.
# If the same sender address is used, each next transfer takes 74 bytes per instruction.
# But also may vary, because it depends.
#
class AtaInstruction(NamedTuple):
    pubkey: Pubkey
    ix:     Instruction = None

def GetAta(tokenMint: SapysolPubkey, owner: SapysolPubkey) -> Pubkey:
    return get_associated_token_address(owner=MakePubkey(owner), mint=MakePubkey(tokenMint))

def CreateAtaIx(tokenMint: SapysolPubkey, owner: SapysolPubkey, payer: SapysolPubkey) -> Pubkey:
    return create_associated_token_account(payer=MakePubkey(payer), owner=MakePubkey(owner), mint=MakePubkey(tokenMint))

def GetOrCreateAtaIx(connection: Client,
                     tokenMint:  SapysolPubkey,
                     owner:      SapysolPubkey,
                     payer:      SapysolPubkey = None,
                     allowOwnerOffCurve: bool = True) -> AtaInstruction:

    if allowOwnerOffCurve == False and not owner.is_on_curve():
        raise("GetOrCreateATAInstruction(): allowOwnerOffCurve = False, but `owner` is off curve address!")

    ataAddress = GetAta(owner=owner, tokenMint=tokenMint)
    account    = connection.get_account_info(ataAddress)
    return AtaInstruction(pubkey = ataAddress,
                          ix     = None if account.value is not None else CreateAtaIx(payer=payer if payer else owner, owner=owner, tokenMint=tokenMint))

# ===============================================================================
# `transfer` is deprecated, using `transfer_checked`.
# Transfering SPL tokens takes 114 bytes per instruction.
# If the same sender address is used, each next transfer takes 50 bytes per instruction.
# But also may vary, because it depends.
#
def GetTransferTokenIxInternal(tokenProgramID: SapysolPubkey,
                               tokenMint:      SapysolPubkey,
                               decimals:       int,
                               senderWallet:   SapysolPubkey,
                               senderAta:      SapysolPubkey,
                               receiverAta:    SapysolPubkey,
                               amountLamports: int) -> Instruction:
    return splToken.transfer_checked(
        splToken.TransferCheckedParams(
            program_id = MakePubkey(tokenProgramID),
            source     = MakePubkey(senderAta),
            mint       = MakePubkey(tokenMint),
            dest       = MakePubkey(receiverAta),
            owner      = MakePubkey(senderWallet),
            amount     = amountLamports,
            decimals   = decimals,
            signers    = [MakePubkey(senderWallet)],
        )
    )

# ===============================================================================
#
def GetTransferTokenIx(connection:       Client,
                       tokenMint:        SapysolPubkey,
                       senderWallet:     SapysolPubkey,
                       receiverWallet:   SapysolPubkey,
                       amount:           int,
                       amountIsLamports: bool = True,
                       allowCreateAta:   bool = True) -> List[Instruction]:
    result: List[Instruction] = []
    if allowCreateAta:
        ataIx: AtaInstruction = GetOrCreateAtaIx(connection = connection,
                                                tokenMint  = tokenMint,
                                                owner      = receiverWallet,
                                                payer      = senderWallet)
        if ataIx.ix:
            result.append(ataIx.ix)

    tokenInfo:    TokenCacheEntry = TokenCache.GetToken(connection=connection, tokenMint=tokenMint)
    sendLamports: int             = amount if amountIsLamports else (int(amount * 10**tokenInfo.decimals))
    transferIx = GetTransferTokenIxInternal(tokenProgramID = tokenInfo.program_id,
                                            tokenMint      = tokenMint,
                                            decimals       = tokenInfo.decimals,
                                            senderWallet   = senderWallet,
                                            senderAta      = get_associated_token_address(owner=MakePubkey(senderWallet),   mint=MakePubkey(tokenMint)),
                                            receiverAta    = get_associated_token_address(owner=MakePubkey(receiverWallet), mint=MakePubkey(tokenMint)),
                                            amountLamports = sendLamports)
    result.append(transferIx)
    return result

# ===============================================================================
#
def WrapSolInstructions(connection: Client,
                        lamports:   int,
                        owner:      SapysolPubkey,
                        payer:      SapysolPubkey = None) -> List[Instruction]:

    wsolAta = GetOrCreateAtaIx(connection=connection, tokenMint=NATIVE_MINT, owner=owner, payer=payer)
    ixList: List[Instruction] = []
    if wsolAta.ix:
        ixList.append(wsolAta.ix)
    ixList.append(transfer({
        "from_pubkey": MakePubkey(owner),
        "to_pubkey":   wsolAta.pubkey,
        "lamports":    lamports
    }))
    ixList.append(sync_native(SyncNativeParams(program_id=TOKEN_PROGRAM_ID, account=wsolAta.pubkey)))
    return ixList

# ===============================================================================
# 
def UnwrapSolInstruction(owner:              SapysolPubkey,
                         allowOwnerOffCurve: bool = True) -> Instruction:

    if allowOwnerOffCurve == False and not MakePubkey(owner).is_on_curve():
        raise("UnwrapSolInstruction(): allowOwnerOffCurve = False, but `owner` is off curve address!")

    wsolAta = GetAta(tokenMint=NATIVE_MINT, owner=owner)
    return close_account(params=CloseAccountParams(program_id = TOKEN_PROGRAM_ID,
                                                   account    = wsolAta,
                                                   dest       = MakePubkey(owner),
                                                   owner      = MakePubkey(owner)))

# ===============================================================================
#
def ComputeBudgetIx(units=1_400_000) -> Instruction:
    return set_compute_unit_limit(units=units)

def ComputePriceIx(microLamports=1) -> Instruction:
    return set_compute_unit_price(micro_lamports=microLamports)

# ===============================================================================
#
