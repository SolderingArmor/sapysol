# sapysol

`sapysol` is a Solana Python wrapper. It doesn't reinvent what [solana-py](https://github.com/michaelhly/solana-py), [solders](https://github.com/kevinheavey/solders) or [AnchorPy](https://github.com/kevinheavey/anchorpy) do, but rather uses their power to create easy-to-use Python classes and wrappers to create short and fast Python scripts to interact with Solana blockchain.

Along with `@solana/web3.js` that helps developers write JS code, `sapysol` will expose blockchain technologies to more developers that prefer using Python.

Main goal of `sapysol` is an ease of Python developers onboarding to Solana.

`sapysol` can also serve as a base layer for other wrappers because it simplifies `Pubkey`/`Keypair` management, creating and sending transactions, token instructions etc.

# Installation

```sh
pip install sapysol
```

Note: Requires Python >= 3.11.

# Usage

`sapysol` uses `Client` instead of `AsyncClient` for few reasons. 
* First - without `async` you can put more logic to Python constructors and simplify class creation;
* Second - what is the point of `async` if you really use `await` in 100% of cases?

```py
from sapysol import *
```

# Contributing
TODO

# Tests
TODO

# Contact
[Telegram](https://t.me/SuperArmor)

# Disclaimer

### Intended Purpose and Use
The Content is provided solely for educational, informational, and general purposes. It is not intended for use in making any business, investment, or legal decisions. Although every effort has been made to keep the information up-to-date and accurate, no representations or warranties, express or implied, are made regarding the completeness, accuracy, reliability, suitability, or availability of the Content.

### Opinions and Views
The views and opinions expressed herein are those of Anton Platonov and do not necessarily reflect the official policy, position, or views of any other agency, organization, employer, or company. These views are subject to change, revision, and rethinking at any time.

### Third-Party Content and Intellectual Property
Some Content may include or link to third-party materials. The User agrees to respect all applicable intellectual property laws, including copyrights and trademarks, when engaging with this Content.

### Amendments
Chintan Gurjar reserves the right to update or change this disclaimer at any time without notice. Continued use of the Content following modifications to this disclaimer will constitute acceptance of the revised terms.