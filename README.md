# sapysol

`sapysol` is a Solana Python wrapper. It doesn't reinvent what [solana-py](https://github.com/michaelhly/solana-py), [solders](https://github.com/kevinheavey/solders) or [AnchorPy](https://github.com/kevinheavey/anchorpy) do, but rather uses their power to create easy-to-use Python classes and wrappers to rapidly develop short and fast Python scripts to interact with Solana blockchain.

Like `@solana/web3.js` helps developers write JS code, `sapysol` will ease using blockchain technologies to more developers that prefer Python instead. More developers on board - better for the community and Solana.

`sapysol` can also serve as a base layer for other wrappers because it simplifies `Pubkey`/`Keypair` management, creating and sending transactions, tokens, instructions etc.

WARNING! `sapysol` is currently in `alpha` version, so, bugs, lack of tests and descriptions are expected. Some things may not work, future versions may bring breaking changes. It is a hard path for Python in Solana and I hope we hat a lot of friends along the way.

# Installation

```sh
pip install sapysol
```

Note: Requires Python >= 3.11.

# Usage

`sapysol` uses `Client` instead of `AsyncClient` for few reasons:
* First - without `async` you can put more logic to Python constructors and other non-async functions;
* Second - what is the point of `async` if you really use `await` in 100% of cases?

Please use `threading` if you need parallel execution.

```py
# Sending SOL to another wallet
from solana.rpc.api import Client 
from sapysol        import *

connection: Client          = Client("https://api.mainnet-beta.solana.com")
wallet:     SapysolWallet   = SapysolWallet(connection=connection, keypair="path/to/file.json")
result:     SapysolTxStatus = wallet.SendSol(destinationAddress="11111111111111111111111111111111", amountSol=0.5)
assert(result==SapysolTxStatus.SUCCESS)

# TODO - other simple use cases
```

TODO

# Contributing

All contributions are welcome! Although the devil is in the details:
* One of the main requirements is to [b]keep the same coding style[/b] for all future changes.
* `sapysol` is designed as a wrapper, one layer above `solders`/`solana-py`, don't expect it to do very narrow or specific tasks. If you need custom behavior in your case just go one level down and implement that using `solders`/`solana-py` in your local scripts.

# Tests

TODO

# Contact

[Telegram](https://t.me/sapysol)

Donations: `SAxxD7JGPQWqDihYDfD6mFp7JWz5xGrf9RXmE4BJWTS`

# Disclaimer

### Intended Purpose and Use
The Content is provided solely for educational, informational, and general purposes. It is not intended for use in making any business, investment, or legal decisions. Although every effort has been made to keep the information up-to-date and accurate, no representations or warranties, express or implied, are made regarding the completeness, accuracy, reliability, suitability, or availability of the Content.

### Opinions and Views
The views and opinions expressed herein are those of Anton Platonov and do not necessarily reflect the official policy, position, or views of any other agency, organization, employer, or company. These views are subject to change, revision, and rethinking at any time.

### Third-Party Content and Intellectual Property
Some Content may include or link to third-party materials. The User agrees to respect all applicable intellectual property laws, including copyrights and trademarks, when engaging with this Content.

### Amendments
Chintan Gurjar reserves the right to update or change this disclaimer at any time without notice. Continued use of the Content following modifications to this disclaimer will constitute acceptance of the revised terms.