# Geminon v1
 Production code of Geminon Protocol V1

## Deployment addresses
The protocol is deployed on Ethereum, BNB and Avalanche networks. Always check that you are interacting with the right address before signing transactions. Unless otherwise stated, the contract deployment address is the same on all blockchains.
* Geminon Protocol Deployer: 0x88d70DEBB940E0bEE526981D99B0f3000E0a3268


### GEX token
The address of the GEX token is the same on the three chains:  
* 0x2743Bb6962fb1D7d13C056476F3Bc331D7C3E112


### Genesis Liquidity Pools
There are four pools in Ethereum, and two pools in BSC and Avalanche. The addresses of the native asset pool of each chain and the bitcoin pool are also the same:

#### Ethereum
* ETH-GEX pool: 0xA4df7a003303552AcDdF550A0A65818c4A218315
* RENBTC-GEX pool: 0x5ae76CbAedf4E0F710C2b429890B4cCC0737104D (deprecated)
* PAXG-GEX pool: 0x48A814C44beeFE3A1C7c165367c1Ea12eA599b48
* XAUT-GEX pool: 0xE7e708277A03dA75186C231b5B43FcFB34BEd29B

#### BNB Smart Chain
* BNB-GEX pool: 0xA4df7a003303552AcDdF550A0A65818c4A218315
* RENBTC-GEX pool: 0x5ae76CbAedf4E0F710C2b429890B4cCC0737104D (deprecated)

#### Avalanche
* AVAX-GEX pool: 0xA4df7a003303552AcDdF550A0A65818c4A218315
* BTC.B-GEX pool: 0x5ae76CbAedf4E0F710C2b429890B4cCC0737104D


### Collateral
GEX token is fully collateralized with gold, Bitcoin, Ethereum, BNB and AVAX. We have selected Paxos Gold and Tether Gold as providers for the tokenized gold, Ren Bitcoin for the wrapped version of Bitcoin on Ethereum and BNB, and Avalanche Bridged Bitcoin on Avalanche. The weight and address of each collateral is:  

* 20% Paxos Gold (PAXG): 0x45804880De22913dAFE09f4980848ECE6EcbAf78 (Ethereum)
* 20% Tether Gold (XAUT): 0x68749665FF8D2d112Fa859AA293F07A622782F38 (Ethereum)
* 10% ren BTC (RENBTC): 0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D (Ethereum) (deprecated)
* 10% Ethereum (ETH)  

* 10% ren BTC (RENBTC): 0xfCe146bF3146100cfe5dB4129cf6C82b0eF4Ad8c (BNB) (deprecated)
* 10% BNB (BNB)  

* 10% Bitcoin Avalanche Bridged (BTC.B): 0x152b9d0FdC40C096757F570A51E494bd4b943E50 (AVAX)
* 10% Avalanche (AVAX)  

The total weight of collateral on each network is therefore: 60% Ethereum, 20% BNB and 20% Avalanche.


### Stablecoins Minter
The SCMinter contract has the mission of minting and redeeming the stablecoins of the Geminon protocol. It also includes the swap module, which allows you to trade stablecoins without slippage.
* 0xeF0dfe8cF872B4dF3681Ad37A17Ef5e2D473B877


### Stablecoins
#### USDI
USDI is the flagship of the Geminon stablecoins. It is a dollar indexed to the inflation in the US.
* 0x4C24e67DC2a00AdA5E90C1E284d2EE4260A21E05
##### PredictIndex USDI
The index beacon contract calculates the CPI forecast for the next period and passes that value to the USDI contract so that it can calculate its peg value dynamically.
* 0x31ac1cc4f770501AdE10E252A6AE27F36D4469Fa

#### EURI
EURI is the inflation indexed Euro.
* 0xcbB00E1f27a59735f390F3263d335A112f10Db8b
##### PredictIndex EURI
Calculates the forecast of the HICP that is used by the EURI contract to calculate its peg.
* 0x842b95dc806745a2B1e0C99a39e0BcF60eC7Ecc2

#### USDG
USDG is the Geminon US Dollar stablecoin
* 0x825B116b431c441C8f5eC19abC069adbd0a169cF

#### EURG
EURG is the Geminon Euro stablecoin
* 0x38f8058b4dF45E8451d10f40343DBAaeCAE620cF

#### CNYG
CNYG is the Geminon Chinese Yuan Renminbi stablecoin
* 0x52644C661Bd2436C0a620Cf11b617276b8c7C2D1


### Oracle
The Geminon Oracle is used by other contracts for coordination, information and safety checks. It is a critical part of the protocol. Its address is the same on the three chains:
* 0x2208C74e717df65E367A7dB03B8675627D31ac31 (deprecated)  
Second version:
* 0xa7d3d2bAd28fd928b72283E8a96f6E8D5c5D94e2


### Arbitrage bridge v0
In order to keep the prices between chains coordinated, we have set up an internal bridge to perform arbitrage. This bridge is temporary, and will be deprecated as soon as the integration of a public bridge is complete.
* 0xC783565D32517DCC80d0aAA44580ef92dAd224e3

