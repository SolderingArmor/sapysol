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
# module: tx
#
# =============================================================================
# 
from   solana.rpc.api                       import Client, Pubkey, Keypair, Commitment
from   solana.rpc.types                     import TxOpts
from   solana.transaction                   import Transaction, Signature, Instruction
from   solders.address_lookup_table_account import AddressLookupTableAccount
from   solders.message                      import to_bytes_versioned, MessageV0
from   solders.transaction                  import VersionedTransaction, Signer
from   solders.transaction_status           import EncodedTransactionWithStatusMeta
from   typing                               import List, Any, TypedDict, Union, Optional, Literal
from   dataclasses                          import dataclass, field
from   datetime                             import datetime
from   enum                                 import Enum
from  .helpers                              import MakeKeypair, SapysolKeypair, NestedAttributeExists
import base64
import logging
import time

# ================================================================================
#
@dataclass
class SapysolTxParams:
    maxSecondsPerTx:       int        = 30          # 
    sleepBetweenRetry:     float      = 0.3         # 
    skipConfirmation:      bool       = True        # 
    skipPreFlight:         bool       = True        # 
    maxRetries:            int        = 0           # 
    blockhashCommitment:   Commitment = "finalized" # 
    transactionCommitment: Commitment = "confirmed" # 

# ================================================================================
#
class SapysolTxStatus(Enum):
    PENDING = 1 # Pending transaction is not (yet) processed
    TIMEOUT = 2 # We couldn't wait till transaction gets processed, it MAY be processed
    FAIL    = 3 # 100% Fail
    SUCCESS = 4 # 100% Success

SapysolTxImportMode = Literal["auto", "legacy", "versioned"]

# ================================================================================
#
class SapysolTx:
    def __init__(self, connection: Client, payer: SapysolKeypair, txParams: SapysolTxParams = SapysolTxParams()):

        self.CONNECTION:       Client                                   = connection
        self.PAYER:            Keypair                                  =  MakeKeypair(payer)
        self.SIGNERS:          List[Signer]                             = [MakeKeypair(payer)]
        self.TX_PARAMS:        SapysolTxParams                          = txParams
        self.CONFIRMED_TX:     EncodedTransactionWithStatusMeta         = None
        self.CONFIRMED_RESULT: SapysolTxStatus                          = SapysolTxStatus.PENDING
        self.RAW_TX:           Union[VersionedTransaction, Transaction] = None
        self.SENT_DT:          datetime                                 = None
        self.TXID:             Signature                                = None
        self.LAST_VALID_BLOCKHEIGHT: int                                = None

    # ========================================
    #
    def FromInstructionsLegacy(self, 
                               instructions: List[Instruction],
                               signers:      List[Signer] = None) -> "SapysolTx":
        if signers:
            self.SIGNERS = signers
        latestBlockHash = self.CONNECTION.get_latest_blockhash(commitment=self.TX_PARAMS.blockhashCommitment).value
        self.RAW_TX     = Transaction(recent_blockhash = latestBlockHash.blockhash,
                                      instructions     = instructions)

        return self

    # ========================================
    #
    def FromInstructionsVersioned(self, 
                                  instructions:        List[Instruction],
                                  signers:             List[Signer] = None,
                                  lookupTableAccounts: List[AddressLookupTableAccount] = []) -> "SapysolTx":
        if signers:
            self.SIGNERS = signers
        latestBlockHash = self.CONNECTION.get_latest_blockhash(commitment=self.TX_PARAMS.blockhashCommitment).value
        msg = MessageV0.try_compile(
            payer            = self.PAYER.pubkey(),
            instructions     = instructions,
            recent_blockhash = latestBlockHash.blockhash,
            address_lookup_table_accounts = lookupTableAccounts,
        )
        self.RAW_TX = VersionedTransaction(msg, signers if signers else [self.PAYER])
        return self

    # ========================================
    #
    def FromBytes(self, b: bytes, importMode: SapysolTxImportMode = "auto") -> "SapysolTx":
        match importMode:
            case "auto":
                try:
                    return self.FromBytes(b=b, importMode="versioned")
                except:
                    return self.FromBytes(b=b, importMode="legacy")
            case "legacy":
                self.RAW_TX = Transaction.deserialize(b)
            case "versioned":
                self.RAW_TX = VersionedTransaction.from_bytes(b)
        return self

    # ========================================
    #
    def FromBase64(self, b64: str, importMode: SapysolTxImportMode = "auto") -> "SapysolTx":
        b = base64.b64decode(b64)
        return self.FromBytes(b=b, importMode=importMode)

    # ========================================
    #
    def Encode(self) -> str:
        encodedTx: str = base64.b64encode(bytes(self.RAW_TX)).decode("utf-8")
        return encodedTx

    # ========================================
    #
    def Decode(self) -> bytes:
        if isinstance(self.RAW_TX, VersionedTransaction):
            return bytes(self.RAW_TX)
        elif isinstance(self.RAW_TX, Transaction):
            return self.RAW_TX.serialize()

    # ========================================
    #
    def SetTxParams(self, txParams: SapysolTxParams) -> bytes:
        self.TX_PARAMS: SapysolTxParams = txParams

    # ========================================
    # 
    def Sign(self, signersOverride: List[SapysolKeypair] = None) -> "SapysolTx":
        signers = self.SIGNERS if signersOverride is None else [MakeKeypair(signer) for signer in signersOverride]
        if signers is None:
            signers = [self.PAYER]
        if signers is None:
            raise(Exception(f"SapysolTx::Sign(): no signers specified!"))

        if isinstance(self.RAW_TX, VersionedTransaction):
            self.RAW_TX = VersionedTransaction(message  = self.RAW_TX.message,
                                               keypairs = signers)
        elif isinstance(self.RAW_TX, Transaction):
            self.RAW_TX.fee_payer = signers[0].pubkey()
            self.RAW_TX.sign(*signers)

        return self

    # ========================================
    #
    def __SendInternal(self, connection: Client, txParams: SapysolTxParams) -> "SapysolTx":
        if self.CONFIRMED_RESULT != SapysolTxStatus.PENDING:
            return self

        if self.SENT_DT is None:
            self.SENT_DT = datetime.now()

        if self.LAST_VALID_BLOCKHEIGHT is None:
            latestBlockHash = (connection.get_latest_blockhash(commitment=txParams.blockhashCommitment)).value
            self.LAST_VALID_BLOCKHEIGHT: int = latestBlockHash.last_valid_block_height

        if txParams.maxSecondsPerTx is not None and (datetime.now() - self.SENT_DT).seconds >= txParams.maxSecondsPerTx:
            self.CONFIRMED_RESULT = SapysolTxStatus.TIMEOUT
            logging.info(f"{self.CONFIRMED_RESULT.name}: https://solscan.io/tx/{self.TXID}")
            return self

        blockheight = (connection.get_block_height()).value
        if blockheight < self.LAST_VALID_BLOCKHEIGHT:
            logging.debug(f"SapysolTx::Send() blockheight={blockheight}; lastValidBlockHeight={self.LAST_VALID_BLOCKHEIGHT}; {self.LAST_VALID_BLOCKHEIGHT-blockheight}")

            txOpts: TxOpts = TxOpts(skip_confirmation = txParams.skipConfirmation, 
                                    skip_preflight    = txParams.skipPreFlight, 
                                    max_retries       = txParams.maxRetries)
            self.TXID: Signature = (connection.send_raw_transaction(txn=self.Decode(), opts=txOpts)).value

        return self

    # ========================================
    # Can send to one or many endpoints at the same time.
    # TODO: add description
    #
    def Send(self,
             connectionOverride: Union[str, Client, List[Client]] = None,
             txParamsOverride:   SapysolTxParams = None) -> "SapysolTx":

        useDefaultConnection:   bool = connectionOverride is None
        useSingleOverride:      bool = isinstance(connectionOverride, Client)
        useSingleOverrideStr:   bool = isinstance(connectionOverride, str)
        useMultipleOverride:    bool = isinstance(connectionOverride, list) and all(isinstance(n, Client) for n in connectionOverride)
        useMultipleOverrideStr: bool = isinstance(connectionOverride, list) and all(isinstance(n, str)    for n in connectionOverride)
        txParams: SapysolTxParams    = txParamsOverride if txParamsOverride else self.TX_PARAMS

        # None is given
        if useDefaultConnection:
            self.__SendInternal(connection=self.CONNECTION, txParams=txParams)

        # `Client` is given
        elif useSingleOverride:
            self.__SendInternal(connection=connectionOverride, txParams=txParams)

        # connection string is given
        elif useSingleOverrideStr:
            self.__SendInternal(connection=Client(connectionOverride), txParams=txParams)

        # multiple `Client`s are given
        elif useMultipleOverride:
            for connection in connectionOverride:
                self.__SendInternal(connection=connection, txParams=txParams)

        # multiple connection strings are given
        elif useMultipleOverrideStr:
            for connection in connectionOverride:
                self.__SendInternal(Client(connection), txParams=txParams)

        # ?????
        else:
            raise Exception("SapysolTx::Send() Error! `connectionOverride` has invalid type!")

        return self

    # ========================================
    #
    def __ConfirmInternal(self, connection: Client) -> SapysolTxStatus:
        if self.CONFIRMED_RESULT != SapysolTxStatus.PENDING:
            return self.CONFIRMED_RESULT

        if self.TXID is None:
            return SapysolTxStatus.PENDING

        if self.CONFIRMED_TX is not None:
            self.CONFIRMED_RESULT = SapysolTxStatus.SUCCESS if self.CONFIRMED_TX.meta.err is None \
                               else SapysolTxStatus.FAIL
            logging.info(f"{self.CONFIRMED_RESULT.name}: https://solscan.io/tx/{self.TXID}")
            return self.CONFIRMED_RESULT

        try:
            trans = connection.get_transaction(tx_sig     = self.TXID,
                                               commitment = self.TX_PARAMS.transactionCommitment,
                                               max_supported_transaction_version=0)

            if NestedAttributeExists(target=trans, attributePath="value.transaction"):
                self.CONFIRMED_TX = trans.value.transaction
                return self.Confirm() # one more pass because we need to hit `if self.CONFIRMED_TX is not None` case

        except KeyboardInterrupt as e:
            raise
        except Exception as e:
            logging.error(e, exc_info=(type(e), e, e.__traceback__))

        return self.CONFIRMED_RESULT

    # ========================================
    #
    def Confirm(self) -> SapysolTxStatus:
        return self.__ConfirmInternal(connection=self.CONNECTION)

    # ========================================
    # TODO: for connection list send all transactions threaded
    #
    def SendAndWait(self, connectionOverride: Union[Client, List[Client]] = None) -> SapysolTxStatus:
        while True:
            r: SapysolTxStatus = (self.Send(connectionOverride=connectionOverride)).Confirm()
            if r != SapysolTxStatus.PENDING:
                return r

            if self.TX_PARAMS.sleepBetweenRetry and self.TX_PARAMS.sleepBetweenRetry > 0:
                time.sleep(self.TX_PARAMS.sleepBetweenRetry)

# ================================================================================
# TODO: return not only result but full tx info
def SendAndWaitBatchTx(txArray:  List[SapysolTx],
                       txParams: SapysolTxParams = SapysolTxParams()) -> List[SapysolTxStatus]:
    while True:
        txNum = 0
        results: List[SapysolTxStatus] = []

        tx: SapysolTx
        for tx in txArray:
            r: SapysolTxStatus = tx.Send().Confirm()
            results.append(r)
            if r != SapysolTxStatus.PENDING:
                txNum += 1

        if txNum >= len(txArray):
            return results

        if txParams.sleepBetweenRetry and txParams.sleepBetweenRetry > 0:
            time.sleep(txParams.sleepBetweenRetry)

# ================================================================================
#
