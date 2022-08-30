# Geminon v1
 Production code of Geminon Protocol V1

## Deployment addresses
The protocol is deployed on Ethereum, BNB and Avalanche networks. Always check that you are interacting with the right address before signing transactions.


### GEX token
The address of the GEX token is the same on the three chains:
0x2743Bb6962fb1D7d13C056476F3Bc331D7C3E112


### Genesis Liquidity Pools
There are four pools in Ethereum, and two pools in BSC and Avalanche. The addresses of the native asset pool of each chain and the bitcoin pool are also the same:

#### Ethereum network
* ETH-GEX pool: 0xE38D693A1AE6CE36625191ca6F225615da589529
* RENBTC-GEX pool: 0x4ACad9691D43DBAf0bBA5A8d2E668e39910015De
* PAXG-GEX pool: 0x239A9157b3Ed91BF4467D707473E194920A2C21D
* XAUT-GEX pool: 0xc8024fB5C7beD98CcE0e498E54B7D89816B3521B

#### BNB chain
* BNB-GEX pool: 0xE38D693A1AE6CE36625191ca6F225615da589529
* RENBTC-GEX pool: 0x4ACad9691D43DBAf0bBA5A8d2E668e39910015De

#### Avalanche
* AVAX-GEX pool: 0xE38D693A1AE6CE36625191ca6F225615da589529
* BTC.B-GEX pool: 0x4ACad9691D43DBAf0bBA5A8d2E668e39910015De


### Collateral
GEX token is fully collateralized with gold, Bitcoin, Ethereum, BNB and AVAX. We have selected Paxos Gold and Tether Gold as providers for the tokenized gold, Ren Bitcoin for the wrapped version of Bitcoin on Ethereum and BNB, and Avalanche Bridged Bitcoin on Avalanche. The weight and address of each collateral is:

* 20% Paxos Gold (PAXG): 0x45804880De22913dAFE09f4980848ECE6EcbAf78 (Ethereum)
* 20% Tether Gold (XAUT): 0x68749665FF8D2d112Fa859AA293F07A622782F38 (Ethereum)
* 10% ren BTC (RENBTC): 0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D (Ethereum)
* 10% Ethereum (ETH)

* 10% ren BTC (RENBTC): 0xfCe146bF3146100cfe5dB4129cf6C82b0eF4Ad8c (BNB)
* 10% BNB (BNB)

* 10% Bitcoin Avalanche Bridged (BTC.B): 0x152b9d0FdC40C096757F570A51E494bd4b943E50 (AVAX)
* 10% Avalanche (AVAX)

The total weight of collateral on each network is: 60% Ethereum, 20% BNB and 20% Avalanche.
