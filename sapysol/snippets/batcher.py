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
from   typing            import List, Union, Any, Literal
from   queue             import Queue, Empty
from   threading         import Thread
from   solana.exceptions import SolanaRpcException
import copy
import time
import logging

# =============================================================================
# 
SAPYSOL_ERROR_ACTION = Literal["ignore", "print", "raise"]

# =============================================================================
# 
class SapysolBatcher:
    def __init__(self, 
                 callback:    Any,
                 entityList:  List[Any],
                 entityKwarg: str = None,
                 numThreads:  int = 10,
                 args             = (),
                 kwargs           = {}):

        self.ENTITY_LIST:  List[Any]    = entityList
        self.ENTITY_KWARG: str          = entityKwarg
        self.CALLBACK                   = callback
        self.ARGS                       = copy.deepcopy(args)
        self.KWARGS                     = copy.deepcopy(kwargs)
        self.NUM_THREADS:  int          = numThreads
        self.QUEUE:        Queue        = Queue()
        self.THREADS:      List[Thread] = []
        for entity in entityList:
            self.QUEUE.put(entity)
        self.RPC_ERROR_ACTION: SAPYSOL_ERROR_ACTION = "ignore"
        self.ALL_ERROR_ACTION: SAPYSOL_ERROR_ACTION = "ignore"

    # ========================================
    #
    def Start(self, 
              sleepTime: float = 0.1, 
              rpcErrorAction: SAPYSOL_ERROR_ACTION = "print",
              allErrorAction: SAPYSOL_ERROR_ACTION = "print") -> None:
        self.RPC_ERROR_ACTION: SAPYSOL_ERROR_ACTION = rpcErrorAction if rpcErrorAction else "print"
        self.ALL_ERROR_ACTION: SAPYSOL_ERROR_ACTION = allErrorAction if allErrorAction else "print"

        for _ in range(self.NUM_THREADS):
            thr = Thread(target=self.__ProcessSingle)
            thr.start()
            self.THREADS.append(thr)

        while not self.IsDone():
            time.sleep(sleepTime)

    # ========================================
    #
    def IsDone(self) -> bool:
        thr: Thread
        for thr in self.THREADS:
            if thr.is_alive():
                return False
        return True

    # ========================================
    #
    def __ProcessSingle(self):
        def __SingleCall(entity):
            while True:
                try:
                    # Check if entity has kwarg name
                    if self.ENTITY_KWARG:
                        self.KWARGS[self.ENTITY_KWARG] = entity
                        self.CALLBACK(*self.ARGS, **self.KWARGS)
                    else:
                        self.CALLBACK(entity, *self.ARGS, **self.KWARGS)
                    return
                except SolanaRpcException as e:
                    match self.RPC_ERROR_ACTION:
                        case "ignore":
                            pass
                        case "print":
                            logging.error(f"SapysolBatcher::__ProcessSingle(), RPC error:\n{e}")
                        case "raise":
                            raise
                except Exception as e:
                    match self.ALL_ERROR_ACTION:
                        case "ignore":
                            pass
                        case "print":
                            logging.error(f"SapysolBatcher::__ProcessSingle(), Error:\n{e}")
                        case "raise":
                            raise

        while True:
            try:
                if self.QUEUE.qsize() <= 0:
                    return
                entity = self.QUEUE.get()
                self.QUEUE.task_done()
                __SingleCall(entity=entity)
            except Empty:
                return
            except:
               raise

# =============================================================================
# 