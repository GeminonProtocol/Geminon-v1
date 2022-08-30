# -*- coding: utf-8 -*-
"""
Created on Fri Jul 22 19:44:23 2022

@author: Rik
"""

from brownie import accounts, reverts, convert
from brownie import (MockV3Aggregator, 
                     GEX, 
                     MockERC20,
                     MockERC20Indexed,
                     GenesisLiquidityPool,
                     GeminonOracle,
                     SCMinter
                     )
from brownie.network.state import Chain
from brownie.test import given, strategy
from pytest import fixture

import numpy as np


chain = Chain()

ZERO_ADDRESS = convert.to_address('0x' + '0'*40)


deploy_args = {'V3Aggregator': [8, 1800*1e8],  # uint8 _decimals, int256 _initialAnswer
               'GEX': [],  #
               'Token': [1e15, 'PAX Gold', "PAXG"],  # uint64 amountMinted, string name, string symbol
               'GenLiqPool': [None, # gexToken address of the GEX token contract
                              None, # collatToken address of the collateral token contract
                              500, # poolWeight_ integer percentage 3 decimals [1, 1000] (1e3)
                              0.01 * 1e18, # initPoolPrice_ must be in 1e18 USD units
                             ],
               'V3Aggregator2': [8, 22000*1e8],  # uint8 _decimals, int256 _initialAnswer
               'Token2': [1e14, 'renBTC', "renBTC"],  # uint64 amountMinted, string name, string symbol
               'GeminonOracle': [[]], # address[] pools
               'SCMinter': [None, None, None, ZERO_ADDRESS],  # address gexToken, address usdiToken, address oracle, address pool
               'USDI': ['USDI', "USDI"],  # uint64 amountMinted, string name, string symbol
              }

initialize_args = {'GenLiqPool': [1,  # initMintShare integer percentage 3 decimals [1, 1000] (1e3)
                                  None, # oracle
                                  None, # priceFeed address of the collateral token price feed contract
                                  ZERO_ADDRESS, # scMinter_
                                  ZERO_ADDRESS, # treasuryLender_
                                  ZERO_ADDRESS, # feesCollector_
                                  ZERO_ADDRESS, # arbitrageur_
                                 ],}



@fixture(scope='module')
def contract_gex():
    
    return GEX.deploy({"from": accounts[0]})


@fixture(scope='module')
def contract_pricefeed():
    
    return MockV3Aggregator.deploy(*deploy_args['V3Aggregator'], 
                                   {"from": accounts[0]})


@fixture(scope='module')
def contract_pricefeed2():
    
    return MockV3Aggregator.deploy(*deploy_args['V3Aggregator2'], 
                                   {"from": accounts[0]})


@fixture(scope='module')
def contract_token():
    
    contract = MockERC20.deploy(*deploy_args['Token'], {"from": accounts[0]})
    for i in range(8):
        contract.transfer(accounts[i+1], 1e6*1e18, {"from": accounts[0]})
    
    return contract


@fixture(scope='module')
def contract_token2():
    
    contract = MockERC20.deploy(*deploy_args['Token2'], {"from": accounts[0]})
    for i in range(8):
        contract.transfer(accounts[i+1], 1e5*1e18, {"from": accounts[0]})
    
    return contract


@fixture(scope='module')
def contract_usdi():
    
    return MockERC20Indexed.deploy(*deploy_args['USDI'], {"from": accounts[0]})


@fixture(scope='module')
def contract_glp(contract_gex, contract_pricefeed, contract_token):
    
    owner_account = accounts[0]
    
    deploy_args['GenLiqPool'][0] = contract_gex.address
    deploy_args['GenLiqPool'][1] = contract_token.address
    
    return GenesisLiquidityPool.deploy(*deploy_args['GenLiqPool'], 
                                       {"from": owner_account})


@fixture(scope='module')
def contract_glp2(contract_glp, contract_gex, contract_pricefeed2, contract_token2):
    
    owner_account = accounts[0]
    pool_address = owner_account.get_deployment_address(nonce=owner_account.nonce + 1) 
    pools = [contract_glp.address, pool_address]
    contract_gex.initialize(pools, {"from": owner_account})
    
    deploy_args['GenLiqPool'][0] = contract_gex.address
    deploy_args['GenLiqPool'][1] = contract_token2.address
    
    return GenesisLiquidityPool.deploy(*deploy_args['GenLiqPool'], 
                                       {"from": owner_account})


@fixture(scope='module')
def contract_glp3(contract_gex, contract_pricefeed, contract_token):
    
    owner_account = accounts[0]
    
    deploy_args['GenLiqPool'][0] = contract_gex.address
    deploy_args['GenLiqPool'][1] = contract_token.address
    
    return GenesisLiquidityPool.deploy(*deploy_args['GenLiqPool'], 
                                       {"from": owner_account})


@fixture(scope='module')
def contract_oracle(contract_glp, contract_glp2):
    
    return GeminonOracle.deploy([contract_glp.address, contract_glp2.address], 
                                {"from": accounts[0]})


@fixture(scope='module')
def contract_scminter(contract_gex, contract_oracle, contract_glp, contract_usdi):
    
    deploy_args['SCMinter'][0] = contract_gex.address
    deploy_args['SCMinter'][1] = contract_usdi.address
    deploy_args['SCMinter'][2] = contract_oracle.address
    deploy_args['SCMinter'][3] = contract_glp.address
    
    return SCMinter.deploy(*deploy_args['SCMinter'], 
                           {"from": accounts[0]})
    
    




def test_constructor(contract_glp):
    
    poolWeight = deploy_args['GenLiqPool'][2]
    initPoolPrice = deploy_args['GenLiqPool'][3]
    expected_poolsupply = round(100000000 * poolWeight / 1000) * 1e18
    
    
    assert contract_glp.initPoolPrice() == initPoolPrice
    assert contract_glp.poolWeight() == poolWeight
    
    assert contract_glp.baseMintFee() == 1000
    assert contract_glp.baseRedeemFee() == 2000
    assert contract_glp.minMintRate() == int(1e6)
    assert contract_glp.minBurnRate() == int(1e6)
    
    assert contract_glp.meanPrice() == initPoolPrice
    assert contract_glp.lastPrice() == initPoolPrice
    assert contract_glp.poolSupply() == expected_poolsupply
    
    
    
def test_initialize(contract_glp, contract_glp2, contract_glp3, contract_gex,
                    contract_pricefeed, contract_pricefeed2):
    
    expected_mint = round(initialize_args['GenLiqPool'][0] * 100000000 * deploy_args['GenLiqPool'][2]) * 1e12
    
    with reverts():
        contract_glp.mintSwap(1, 0, {"from": accounts[0]})
        
    with reverts():
        contract_glp.redeemSwap(1, 0, {"from": accounts[0]})
        
    with reverts():
        initialize_args['GenLiqPool'][1] = ZERO_ADDRESS
        initialize_args['GenLiqPool'][2] = ZERO_ADDRESS
        contract_glp.initialize(*initialize_args['GenLiqPool'], 
                                {"from": accounts[0]})
        
    initialize_args['GenLiqPool'][2] = contract_pricefeed.address
    contract_glp.initialize(*initialize_args['GenLiqPool'], 
                            {"from": accounts[0]})
    
    assert contract_glp.mintedGEX() == expected_mint
    assert contract_glp.balanceGEX() == expected_mint
    assert contract_glp.meanVolume() == expected_mint
    assert contract_glp.isInitialized() == True
    
    with reverts():
        contract_glp.initialize(*initialize_args['GenLiqPool'], 
                                {"from": accounts[0]})
    
    
    initialize_args['GenLiqPool'][2] = contract_pricefeed2.address
    contract_glp2.initialize(*initialize_args['GenLiqPool'], 
                             {"from": accounts[0]})
    
    contract_glp.unpauseMint({"from": accounts[0]})
    contract_glp2.unpauseMint({"from": accounts[0]})
    
    assert contract_glp.isMintPaused() == False
    assert contract_glp2.isMintPaused() == False
    
    
    
    contract_gex.requestAddAddress(contract_glp3.address, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_gex.addMinter(contract_glp3.address, {"from": accounts[0]})
    
    initialize_args['GenLiqPool'][0] = 0
    initialize_args['GenLiqPool'][2] = contract_pricefeed.address
    contract_glp3.initialize(*initialize_args['GenLiqPool'], 
                              {"from": accounts[0]})
    
    
    
def test_pricefeed(contract_pricefeed):
    
    data = contract_pricefeed.latestRoundData()
    
    assert data[1] == deploy_args['V3Aggregator'][1]
    
    
def test_pricefeed2(contract_pricefeed2):
    
    data = contract_pricefeed2.latestRoundData()
    
    assert data[1] == deploy_args['V3Aggregator2'][1]
    


def test_setSCMinter(contract_glp, contract_scminter):
    
    chain.snapshot()
    
    contract_glp.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    
    with reverts('dev: already set'):
        contract_glp.setSCMinter(contract_scminter.address, {"from": accounts[0]})
        
    assert contract_glp.scMinter() == contract_scminter.address
    
    chain.revert()
        
        
def test_setOracle(contract_glp, contract_oracle):
    
    chain.snapshot()
    
    contract_glp.setOracle(contract_oracle.address, {"from": accounts[0]})
    
    with reverts('dev: already set'):
        contract_glp.setOracle(contract_oracle.address, {"from": accounts[0]})
        
    chain.revert()
                
        
def test_setLender(contract_glp):
    
    chain.snapshot()
    
    contract_glp.setLender(accounts[5], {"from": accounts[0]})
    
    with reverts('dev: already set'):
        contract_glp.setLender(accounts[5], {"from": accounts[0]})
        
    assert contract_glp.treasuryLender() == accounts[5]
    
    chain.revert()
        
        
def test_setCollector(contract_glp):
    
    chain.snapshot()
    
    contract_glp.setCollector(accounts[7], {"from": accounts[0]})
    contract_glp.setCollector(accounts[6], {"from": accounts[0]})
    
    chain.revert()
    
    
def test_setArbitrageur(contract_glp):
    
    chain.snapshot()
    
    contract_glp.setArbitrageur(accounts[8], {"from": accounts[0]})
    contract_glp.setArbitrageur(accounts[7], {"from": accounts[0]})
    
    assert contract_glp.arbitrageur() == accounts[7]
    
    chain.revert()
    


def test_setMintFee(contract_glp):
    
    contract_glp.setMintFee(0, {"from": accounts[0]})
    contract_glp.setMintFee(5000, {"from": accounts[0]})
    contract_glp.setMintFee(1000, {"from": accounts[0]})
    
    with reverts():
        contract_glp.setMintFee(5001, {"from": accounts[0]})
        
        
def test_setRedeemFee(contract_glp):
    
    contract_glp.setRedeemFee(0, {"from": accounts[0]})
    contract_glp.setRedeemFee(5000, {"from": accounts[0]})
    contract_glp.setRedeemFee(2000, {"from": accounts[0]})
    
    with reverts():
        contract_glp.setRedeemFee(5001, {"from": accounts[0]})



def test_setPoolWeight(contract_glp, contract_glp2, 
                        contract_token, contract_token2, contract_oracle):
    
    chain.snapshot()
    with_setOracle(contract_glp, contract_oracle)
    with_setOracle(contract_glp2, contract_oracle)
    arb_addr = with_setArbitrageur(contract_glp)
    arb_addr2 = with_setArbitrageur(contract_glp2)
    
    
    prev_weight = contract_glp.poolWeight()
    
    with reverts('dev: invalid weight value'):
        contract_glp.setPoolWeight(0, {"from": accounts[0]})
        
    with reverts('dev: weight is the same'):
        contract_glp.setPoolWeight(prev_weight, {"from": accounts[0]})
    
    with reverts('dev: weight change too big'):
        contract_glp.setPoolWeight(prev_weight + 51, {"from": accounts[0]})
        
    with reverts('dev: weight change too big'):
        contract_glp.setPoolWeight(prev_weight - 51, {"from": accounts[0]})
        
    
    contract_token.approve(contract_glp.address, 2**256-1, {"from": arb_addr})
    contract_glp.mintSwap(1*1e18, 0, {"from": arb_addr})
    oracle_pool_weight1 = contract_oracle.getPoolCollatWeight(contract_glp.address)
    
    assert contract_glp.balanceCollateral() > 0
    assert oracle_pool_weight1 != 0
    
    
    contract_token2.approve(contract_glp2.address, 2**256-1, {"from": arb_addr2})
    contract_glp2.mintSwap(0.1*1e18, 0, {"from": arb_addr2})
    oracle_pool_weight2 = contract_oracle.getPoolCollatWeight(contract_glp2.address)
    
    assert contract_glp2.balanceCollateral() > 0
    assert oracle_pool_weight2 != 0
    
    new_weight = prev_weight - 50
    contract_glp.setPoolWeight(new_weight, {"from": accounts[0]})
    
    expected_poolsupply = round(100000000 * new_weight / 1000) * int(1e18)
    
    assert contract_glp.poolSupply() == expected_poolsupply
    
    
    contract_glp.setPoolWeight(contract_glp.poolWeight() - 50, {"from": accounts[0]})
    contract_glp.setPoolWeight(contract_glp.poolWeight() - 50, {"from": accounts[0]})
    with reverts('dev: oracle weight change too big'):
        contract_glp.setPoolWeight(contract_glp.poolWeight() - 50, {"from": accounts[0]})
    
    chain.revert()


def test_setMintRates(contract_glp):
    
    chain.snapshot()
    
    
    with reverts('dev: mintRate too high'):
        contract_glp.setMintRates(1.01*1e6, 1e6, {"from": accounts[0]})
        
    with reverts('dev: mintRate too low'):
        contract_glp.setMintRates(0.94*1e6, 1e6, {"from": accounts[0]})
    
    with reverts('dev: burnRate too low'):
        contract_glp.setMintRates(1e6, 0.99*1e6, {"from": accounts[0]})
        
    with reverts('dev: burnRate too high'):
        contract_glp.setMintRates(1e6, 1.06*1e6, {"from": accounts[0]})
        
    
    contract_glp.setMintRates(int(0.95*1e6), int(1.05*1e6), {"from": accounts[0]})
    
    assert contract_glp.minMintRate() == int(0.95*1e6)
    assert contract_glp.minBurnRate() == int(1.05*1e6)
    
    chain.revert()
    
    


def test_requestAddAddress(contract_glp, contract_scminter):
    
    chain.snapshot()
    
    lender_address = with_setLender(contract_glp)
    
    
    with reverts(): 
        contract_glp.requestAddAddress(ZERO_ADDRESS, {"from": accounts[0]})
        
    with reverts():
        contract_glp.requestAddAddress(accounts[2], {"from": accounts[1]})
    
    contract_glp.requestAddAddress(accounts[2], {"from": accounts[0]})
    
    assert contract_glp.changeRequests(ZERO_ADDRESS)[0] == True
    assert abs(contract_glp.changeRequests(ZERO_ADDRESS)[1] - chain.time()) <= 1
    assert contract_glp.changeRequests(ZERO_ADDRESS)[2] == accounts[2]
    
    
    with reverts('dev: Not requested'): 
        contract_glp.applyPriceFeedChange({"from": accounts[0]})
        
    
    contract_glp.requestAddAddress(contract_scminter.address, {"from": accounts[0]})
    with reverts(): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
        
    
    contract_glp.requestAddAddress(lender_address, {"from": accounts[0]})
    with reverts(): 
        contract_glp.applyLenderChange({"from": accounts[0]})
    
    chain.revert()


def test_requestRemoveAddress(contract_glp, contract_scminter):
    
    chain.snapshot()
    
    with_setSCMinter(contract_glp, contract_scminter)
    lender_address = with_setLender(contract_glp)
    
    
    with reverts(): 
        contract_glp.requestRemoveAddress(ZERO_ADDRESS, {"from": accounts[0]})
        
    with reverts():
        contract_glp.requestRemoveAddress(accounts[2], {"from": accounts[1]})
    
    
    contract_glp.requestRemoveAddress(accounts[2], {"from": accounts[0]})
    
    assert contract_glp.changeRequests(accounts[2])[0] == True
    assert abs(contract_glp.changeRequests(accounts[2])[1] - chain.time()) <= 1
    assert contract_glp.changeRequests(accounts[2])[2] == ZERO_ADDRESS
    
    with reverts('dev: Not requested'): 
        contract_glp.applyPriceFeedChange({"from": accounts[0]})
        
    
    contract_glp.requestRemoveAddress(contract_scminter.address, {"from": accounts[0]})
    
    # with reverts('dev: Time elapsed'): 
    with reverts(): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
    
    chain.sleep(3600*24*31)
    chain.mine()
    with reverts('dev: Address zero'): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
        
    
    contract_glp.requestRemoveAddress(lender_address, {"from": accounts[0]})
    with reverts('dev: Time elapsed'): 
        contract_glp.applyLenderChange({"from": accounts[0]})
    
    chain.revert()
        

def test_requestAddressChange(contract_glp):
    
    chain.snapshot()
    
    old_contract = with_setArbitrageur(contract_glp)
    new_contract = accounts[3]
    
    assert contract_glp.changeRequests(old_contract)[0] == False
    
    with reverts(): 
        contract_glp.requestAddressChange(old_contract, ZERO_ADDRESS, 
                                          {"from": accounts[0]})
        
    with reverts():
        contract_glp.requestAddressChange(old_contract, new_contract, 
                                          {"from": accounts[1]})
    
    
    contract_glp.requestAddressChange(old_contract, new_contract, 
                                      {"from": accounts[0]})
    
    assert abs(contract_glp.changeRequests(old_contract)[1] - chain.time()) <= 1
    assert contract_glp.changeRequests(old_contract)[0] == True
    assert contract_glp.changeRequests(old_contract)[2] == new_contract
    
    with reverts('dev: Not requested'): 
        contract_glp.applyPriceFeedChange({"from": accounts[0]})
        
    with reverts(): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
        
    with reverts('dev: Not requested'): 
        contract_glp.applyOracleChange({"from": accounts[0]})
        
    with reverts('dev: Not requested'): 
        contract_glp.applyLenderChange({"from": accounts[0]})
    
    chain.revert()
    


def test_applyPriceFeedChange(contract_glp, contract_pricefeed):
    
    chain.snapshot()
    
    old_contract = contract_pricefeed.address
    new_contract = accounts[4]
    
    
    contract_glp.requestAddressChange(old_contract, new_contract, 
                                      {"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == True
    assert contract_glp.changeRequests(old_contract)[2] == new_contract
    
    with reverts('dev: Time elapsed'): 
        contract_glp.applyPriceFeedChange({"from": accounts[0]})
    
    chain.sleep(3600*24*8)
    chain.mine()
    
    contract_glp.applyPriceFeedChange({"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == False
    assert contract_glp.changeRequests(new_contract)[0] == False
    
    with reverts('dev: Not requested'): 
        contract_glp.applyPriceFeedChange({"from": accounts[0]})
        
    chain.revert()
    
    
    
def test_applySCMinterChange(contract_glp, contract_scminter):
    
    chain.snapshot()
    
    old_contract = with_setSCMinter(contract_glp, contract_scminter)
    new_contract = accounts[4]
    
    
    contract_glp.requestAddressChange(old_contract, new_contract, 
                                      {"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == True
    assert contract_glp.changeRequests(old_contract)[2] == new_contract
    
    # with reverts('dev: Time elapsed'): 
    with reverts(): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    contract_glp.applySCMinterChange({"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == False
    assert contract_glp.changeRequests(new_contract)[0] == False
    
    with reverts(): 
        contract_glp.applySCMinterChange({"from": accounts[0]})
        
    chain.revert()


def test_applyOracleChange(contract_glp, contract_oracle):
    
    chain.snapshot()
    
    old_contract = with_setOracle(contract_glp, contract_oracle)
    new_contract = accounts[4]
    
    
    contract_glp.requestAddressChange(old_contract, new_contract, 
                                      {"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == True
    assert contract_glp.changeRequests(old_contract)[2] == new_contract
    
    with reverts('dev: Time elapsed'): 
        contract_glp.applyOracleChange({"from": accounts[0]})
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    contract_glp.applyOracleChange({"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == False
    assert contract_glp.changeRequests(new_contract)[0] == False
    
    with reverts('dev: Not requested'): 
        contract_glp.applyOracleChange({"from": accounts[0]})
        
    chain.revert()
    
    
def test_applyLenderChange(contract_glp):
    
    chain.snapshot()
    
    old_contract = with_setLender(contract_glp)
    new_contract = accounts[4]
    
    
    contract_glp.requestAddressChange(old_contract, new_contract, 
                                      {"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == True
    assert contract_glp.changeRequests(old_contract)[2] == new_contract
    
    with reverts('dev: Time elapsed'): 
        contract_glp.applyLenderChange({"from": accounts[0]})
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    contract_glp.applyLenderChange({"from": accounts[0]})
    
    assert contract_glp.changeRequests(old_contract)[0] == False
    assert contract_glp.changeRequests(new_contract)[0] == False
    
    with reverts('dev: Not requested'): 
        contract_glp.applyLenderChange({"from": accounts[0]})
        
    chain.revert()
    
    
    
def test_cancelChangeRequests(contract_glp, contract_pricefeed, contract_oracle, contract_scminter):
    
    chain.snapshot()
    
    pricefeed_addr = contract_pricefeed.address
    oracle_addr = with_setOracle(contract_glp, contract_oracle)
    scminter_addr = with_setSCMinter(contract_glp, contract_scminter)
    lender_addr = with_setLender(contract_glp)
    
    
    with reverts():
        contract_glp.cancelChangeRequests({"from": accounts[1]})
        
    
    contract_glp.requestAddAddress(accounts[1], {"from": accounts[0]})
    
    assert contract_glp.changeRequests(ZERO_ADDRESS)[0] == True
    
    contract_glp.cancelChangeRequests({"from": accounts[0]})
    
    assert contract_glp.changeRequests(ZERO_ADDRESS)[0] == False
    
    
    contract_glp.requestRemoveAddress(pricefeed_addr, {"from": accounts[0]})
    contract_glp.requestRemoveAddress(oracle_addr, {"from": accounts[0]})
    contract_glp.requestRemoveAddress(scminter_addr, {"from": accounts[0]})
    contract_glp.requestRemoveAddress(lender_addr, {"from": accounts[0]})
    
    assert contract_glp.changeRequests(pricefeed_addr)[0] == True
    assert contract_glp.changeRequests(oracle_addr)[0] == True
    assert contract_glp.changeRequests(scminter_addr)[0] == True
    assert contract_glp.changeRequests(lender_addr)[0] == True
    
    contract_glp.cancelChangeRequests({"from": accounts[0]})
    
    assert contract_glp.changeRequests(pricefeed_addr)[0] == False
    assert contract_glp.changeRequests(oracle_addr)[0] == False
    assert contract_glp.changeRequests(scminter_addr)[0] == False
    assert contract_glp.changeRequests(lender_addr)[0] == False
    
    
    contract_glp.requestAddressChange(pricefeed_addr, accounts[2], {"from": accounts[0]})
    contract_glp.requestAddressChange(oracle_addr, accounts[2], {"from": accounts[0]})
    contract_glp.requestAddressChange(scminter_addr, accounts[2], {"from": accounts[0]})
    contract_glp.requestAddressChange(lender_addr, accounts[2], {"from": accounts[0]})
    
    assert contract_glp.changeRequests(pricefeed_addr)[0] == True
    assert contract_glp.changeRequests(oracle_addr)[0] == True
    assert contract_glp.changeRequests(scminter_addr)[0] == True
    assert contract_glp.changeRequests(lender_addr)[0] == True
    
    contract_glp.cancelChangeRequests({"from": accounts[0]})
    
    assert contract_glp.changeRequests(pricefeed_addr)[0] == False
    assert contract_glp.changeRequests(oracle_addr)[0] == False
    assert contract_glp.changeRequests(scminter_addr)[0] == False
    assert contract_glp.changeRequests(lender_addr)[0] == False
    
    chain.revert()




@given(amount = strategy('uint64', min_value=1, max_value=1000000000))
def test_variableFee(contract_glp, amount):
    
    baseFee = 1000
    
    fee = contract_glp.variableFee(amount*int(1e18), baseFee)
    
    assert fee - expected_fee(amount, baseFee) < 2
    
    
@given(amount = strategy('uint64', min_value=1, max_value=1000000000))
def test_amountFeeMint(contract_glp, amount):
    
    baseFee = 1000
    fee = expected_fee(amount, baseFee)
    expected_amount = amount*int(1e12) * fee
    
    fee_amount = contract_glp.amountFeeMint(amount*int(1e18))
    
    assert fee_amount - expected_amount < 10
    
    
@given(amount = strategy('uint64', min_value=1, max_value=1000000000))
def test_amountFeeRedeem(contract_glp, amount):
    
    baseFee = 2000
    fee = expected_fee(amount, baseFee)
    expected_amount = amount*int(1e12) * fee
    
    fee_amount = contract_glp.amountFeeRedeem(amount*int(1e18))
    
    assert fee_amount - expected_amount < 10
    
    


    
# Math of this function is fully tested on python simulations
@given(amount = strategy('uint128'))
def test_amountOutGEX(contract_glp, contract_token, contract_oracle, amount):
    
    chain.snapshot()
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    assert contract_glp.amountMint(amount) >= 0
    assert contract_glp.amountBurn(amount) >= 0
    
    assert contract_glp.amountOutGEX(amount) >= 0
    
    chain.revert()
    
    
# Math of this function is fully tested on python simulations
@given(amount = strategy('uint128'))
def test_amountOutCollateral(contract_glp, contract_token, contract_oracle, amount):
    
    chain.snapshot()
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    assert contract_glp.amountMint(amount) >= 0
    assert contract_glp.amountBurn(amount) >= 0
    
    assert contract_glp.amountOutCollateral(amount) >= 0
    
    chain.revert()


def test_mint_limits(contract_glp, contract_gex, contract_token, contract_oracle):
    
    chain.snapshot()
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    amount = 1*1e15
    for i in range(400):
        chain.sleep(300*i)
        chain.mine()
        contract_glp.mintSwap(amount, 0, {"from": accounts[0]})
        amount *= 1.1
        
    chain.revert()


        
def test_mintSwap_redeemSwap(contract_glp, contract_gex, contract_token, contract_oracle):
    
    chain.snapshot()
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(50):
        chain.sleep(3600*3)
        chain.mine()
        contract_glp.mintSwap(10*1e18, 0, {"from": accounts[0]})
        
    
    balanceGEX = contract_gex.balanceOf(accounts[0])
    amount = int(balanceGEX / 51)
    
    for i in range(50):
        chain.sleep(600)
        chain.mine()
        contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
        
    chain.revert()
        
        
    
    
def test_mintRedeem_alt(contract_glp, contract_gex, contract_token, contract_oracle):
    
    chain.snapshot()
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(100):
        contract_glp.mintSwap(10*1e18, 0, {"from": accounts[0]})
        chain.sleep(3600)
        chain.mine()
        
        amount = contract_gex.balanceOf(accounts[0])
        contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
            
    chain.revert()
            
            
def test_mintRedeem_rand(contract_glp, contract_gex, contract_token, contract_oracle):
    
    chain.snapshot()
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(100):
        op = np.random.choice([0,1])
        
        if op > 0:
            amount = np.random.randint(0, 100) * int(1e18)
            contract_glp.mintSwap(amount, 0, {"from": accounts[0]})
        
        else:
            balance = int(contract_gex.balanceOf(accounts[0]) / 1e18)
            amount = np.random.randint(0, balance) * int(1e18)
            contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
        
        chain.sleep(np.random.randint(1, 10000))
        chain.mine()
            
    chain.revert()
            
            
            
def test_multiPool_rand(contract_glp, contract_glp2, contract_gex, 
                        contract_token, contract_token2, contract_oracle):
    
    chain.snapshot()
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_gex.approve(contract_glp2.address, 2**256-1, {"from": accounts[0]})
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_token2.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(500):
        op = np.random.choice([0,1])
        pool = np.random.choice([0,1])
        
        if op > 0:
            value = np.random.randint(0, 10000) * int(1e18) 
            
            if pool > 0:
                amount1 = value * 1e18 / contract_glp.collateralPrice()
                contract_glp.mintSwap(amount1, 0, {"from": accounts[0]})
            
            else:
                amount2 = value * 1e18 / contract_glp2.collateralPrice()
                contract_glp2.mintSwap(amount2, 0, {"from": accounts[0]})
        
        else:
            balance = int(contract_gex.balanceOf(accounts[0]) / 1e18)
            amount = np.random.randint(0, balance) * int(1e18)
            
            if pool > 0:
                contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
            else:
                contract_glp2.redeemSwap(amount, 0, {"from": accounts[0]})
        
        
        chain.sleep(3600*6)
        chain.mine()
        
    chain.revert()



def test_pauseMint(contract_glp):
    
    assert contract_glp.isMintPaused() == False
    
    with reverts():
        contract_glp.pauseMint({"from": accounts[1]})
    
    contract_glp.pauseMint({"from": accounts[0]})
    
    assert contract_glp.isMintPaused() == True
    
    
def test_unpauseMint(contract_glp):
    
    assert contract_glp.isMintPaused() == True
    assert contract_glp.isMigrationRequested() == False
    assert contract_glp.isRemoveRequested() == False
    
    with reverts():
        contract_glp.pauseMint({"from": accounts[1]})
    
    contract_glp.unpauseMint({"from": accounts[0]})
    
    assert contract_glp.isMintPaused() == False
    
    
def test_matchBalances(contract_glp, contract_gex, contract_token):
    
    with reverts():
        contract_glp.matchBalances({"from": accounts[1]})
    
    with reverts('dev: Balances match'):
        contract_glp.matchBalances({"from": accounts[0]})
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_token.balanceOf(contract_glp.address)    
    


def test_bailoutMinter(contract_glp, contract_scminter, contract_oracle, contract_gex):
    
    chain.snapshot()
    
    initial_gex_balance = contract_glp.balanceGEX()
    
    # with reverts('dev: scminter not set'):
    with reverts():
        contract_glp.bailoutMinter({"from": accounts[0]})
        
    with_setSCMinter(contract_glp, contract_scminter)
    
    # with reverts('dev: oracle not set'):
    with reverts():
        contract_glp.bailoutMinter({"from": accounts[0]})
        
    with_setOracle(contract_glp, contract_oracle)
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    
    with reverts('dev: scminter too new'):
        contract_glp.bailoutMinter({"from": accounts[0]})
    
    chain.sleep(3600*24*8)
    chain.mine()
    
    with reverts('dev: oracle too new'):
        contract_glp.bailoutMinter({"from": accounts[0]})
    
    chain.sleep(3600*24*24)
    chain.mine()
    
    with reverts('dev: invalid caller address'):
        contract_glp.bailoutMinter({"from": accounts[1]})
    
    
    tx = contract_glp.bailoutMinter({"from": accounts[0]})
    
    assert tx.return_value <= initial_gex_balance/100
    assert tx.return_value <= 5*initial_gex_balance/100
    assert contract_gex.allowance(contract_glp.address, contract_scminter.address) > 0
    
    
    contract_gex.transferFrom(contract_glp.address, contract_scminter.address, 
                              tx.return_value, {"from": contract_scminter.address})
    
    assert contract_gex.balanceOf(contract_scminter.address) >= tx.return_value
    assert initial_gex_balance - tx.return_value == contract_glp.balanceGEX()
    
    chain.revert()
    
    

def test_lendCollateral(contract_glp, contract_token, contract_scminter, 
                        contract_oracle, contract_gex, contract_usdi):
    
    chain.snapshot()
    
    
    with reverts('dev: null amount'):
        contract_glp.lendCollateral(0, {"from": accounts[0]})
        
    with reverts('dev: pool empty'):
        contract_glp.lendCollateral(1e18, {"from": accounts[0]})
        
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    with reverts('dev: lender not set'):
        contract_glp.lendCollateral(1e18, {"from": accounts[0]})
        
    
    lender_addr = with_setLender(contract_glp)
    contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
    
    with reverts('dev: lender too new'):
        contract_glp.lendCollateral(1e18, {"from": lender_addr})
    
    chain.sleep(3600*24*8)
    chain.mine()
    
    with reverts('dev: oracle too new'):
        contract_glp.lendCollateral(1e18, {"from": lender_addr})
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    with reverts('dev: scMinter not set'):
        contract_glp.lendCollateral(1e18, {"from": lender_addr})
    
    
    with_setSCMinter(contract_glp, contract_scminter)
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    
    with reverts('dev: invalid caller address'):
        contract_glp.lendCollateral(1e18, {"from": accounts[0]})
        
    with reverts('dev: null amount locked on scminter'):
        contract_glp.lendCollateral(1e18, {"from": lender_addr})
        
    chain.revert()
    
    
    chain.snapshot()
    
    lender_addr = with_setLender(contract_glp)
    contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
    with_setSCMinter(contract_glp, contract_scminter)
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    with_some_usdi_minted(contract_scminter, contract_glp, contract_token, 
                          contract_oracle, contract_gex, contract_usdi)
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    balance_collat = contract_glp.balanceCollateral()
    
    tx = contract_glp.lendCollateral(balance_collat, {"from": lender_addr})
    
    assert tx.return_value == contract_glp.balanceLent()
    assert contract_token.allowance(contract_glp.address, lender_addr) == contract_glp.balanceLent()
    
    
    contract_token.transferFrom(contract_glp.address, lender_addr, tx.return_value, 
                                {"from": lender_addr})
    
    assert contract_token.balanceOf(lender_addr) >= contract_glp.balanceLent()
    
    chain.revert()


def test_repayCollateral(contract_glp, contract_token, contract_scminter, 
                          contract_oracle, contract_gex, contract_usdi):
    
    chain.snapshot()
    
    # with reverts('dev: Nothing to repay'):
    with reverts():
        contract_glp.repayCollateral(0, {"from": accounts[0]})
        
    
    lender_addr = with_setLender(contract_glp)
    contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
    with_setSCMinter(contract_glp, contract_scminter)
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    with_some_usdi_minted(contract_scminter, contract_glp, contract_token, 
                          contract_oracle, contract_gex, contract_usdi)
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    balance_collat = contract_glp.balanceCollateral()
    
    contract_glp.lendCollateral(balance_collat, {"from": lender_addr})
    
    
    with reverts('dev: invalid caller address'):
        contract_glp.repayCollateral(1e18, {"from": accounts[0]})
        
    amount = contract_glp.balanceLent()
    contract_token.approve(contract_glp.address, amount, {"from": lender_addr})
    tx = contract_glp.repayCollateral(amount, {"from": lender_addr})
    
    assert tx.return_value == amount
    assert contract_glp.balanceLent() == 0
    assert contract_token.allowance(contract_glp.address, lender_addr) == 0
        
    chain.revert()



def test_collectFees(contract_glp, contract_token, contract_oracle, contract_gex):
    
    chain.snapshot()
    
    # with reverts('dev: Nothing to collect'):
    with reverts():
        contract_glp.collectFees({"from": accounts[0]})
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    with reverts('dev: collector not set'):
        contract_glp.collectFees({"from": accounts[0]})
        
    collector_addr = with_setCollector(contract_glp)
    
    with reverts('dev: collector not set in oracle'):
        contract_glp.collectFees({"from": accounts[0]})
        
    contract_oracle.setCollector(accounts[6], {"from": accounts[0]})
        
    with reverts('dev: collector too new'):
        contract_glp.collectFees({"from": accounts[0]})
        
    chain.sleep(3600*24*8)
    chain.mine()
    
    with reverts('dev: oracle too new'):
        contract_glp.collectFees({"from": accounts[0]})
        
    chain.sleep(3600*24*31)
    chain.mine()
    
    with reverts('dev: invalid caller address'):
        contract_glp.collectFees({"from": accounts[1]})
        
    prev_balance = contract_gex.balanceOf(collector_addr)
    
    tx = contract_glp.collectFees({"from": collector_addr})
    
    assert tx.return_value > 0
    assert prev_balance < contract_gex.balanceOf(collector_addr)
    
    with reverts('dev: Nothing to collect'):
        contract_glp.collectFees({"from": accounts[0]})
        
    chain.revert()
    

def test_getMintInfo(contract_glp, contract_token, contract_oracle):
    
    chain.snapshot()
    
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    baseMintFee = 1000
    inCollatAmount = int(1e18)
    
    collateralPriceUSD = contract_glp.collateralPrice()
    initGEXPriceUSD = contract_glp.GEXPrice()
    collatQuote = contract_glp.collateralQuote()
    gexQuote = contract_glp.GEXQuote()
    
    outGEXAmount = contract_glp.amountOutGEX(inCollatAmount)
    fee = contract_glp.variableFee(outGEXAmount, baseMintFee)
    feeAmount = contract_glp.amountFeeMint(outGEXAmount)
    outGEXAmount -= feeAmount
    finalGEXPriceUSD = int((collateralPriceUSD*inCollatAmount) / outGEXAmount)
    
    priceImpact = int((abs(finalGEXPriceUSD - initGEXPriceUSD) * int(1e6)) / initGEXPriceUSD)
    
    values = contract_glp.getMintInfo(inCollatAmount)
     
    
    assert values[0] == collateralPriceUSD
    assert values[1] == initGEXPriceUSD
    assert values[2] == collatQuote
    assert values[3] == gexQuote
    
    assert values[4] == fee
    assert values[5] == feeAmount
    assert values[6] == outGEXAmount
    assert abs(values[7] - finalGEXPriceUSD) < 10
    
    assert abs(values[8] - priceImpact) <= 1
    
    chain.revert()


def test_getRedeemInfo(contract_glp, contract_token, contract_oracle):
    
    chain.snapshot()
    
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    
    baseRedeemFee = 2000
    inGEXAmount = int(1e18)
    
    collateralPriceUSD = contract_glp.collateralPrice()
    initGEXPriceUSD = contract_glp.GEXPrice()
    collatQuote = contract_glp.collateralQuote()
    gexQuote = contract_glp.GEXQuote()
    
    fee = contract_glp.variableFee(inGEXAmount, baseRedeemFee)
    feeAmount = contract_glp.amountFeeRedeem(inGEXAmount)
    outCollatAmount = contract_glp.amountOutCollateral(inGEXAmount - feeAmount)
    finalGEXPriceUSD = int((collateralPriceUSD*outCollatAmount) / inGEXAmount)
    
    priceImpact = int((abs(finalGEXPriceUSD - initGEXPriceUSD) * int(1e6)) / initGEXPriceUSD)
    
    values = contract_glp.getRedeemInfo(inGEXAmount)
     
    
    assert values[0] == collateralPriceUSD
    assert values[1] == initGEXPriceUSD
    assert values[2] == collatQuote
    assert values[3] == gexQuote
    
    assert values[4] == fee
    assert values[5] == feeAmount
    assert values[6] == outCollatAmount
    assert abs(values[7] - finalGEXPriceUSD) < 10
    
    assert abs(values[8] - priceImpact) <= 1
    
    chain.revert()




def test_Migration(contract_glp, contract_glp2, contract_glp3, contract_oracle, 
                    contract_token, contract_token2, contract_gex):
    
    chain.snapshot()
    
    new_addr = contract_glp3.address
    assert contract_glp3.collateralPrice()
    assert contract_glp3.balanceGEX() == 0
    assert contract_glp3.balanceCollateral() == 0
    assert contract_glp3.getCollateralValue() == 0
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_token.balanceOf(contract_glp.address)
    
    with reverts():
        contract_glp.requestMigration(new_addr, {"from": accounts[0]})
        
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
    with_reduce_pool_weight(49, contract_glp, contract_glp2, contract_oracle)
    
    with_setOracle(contract_glp3, contract_oracle)
    contract_oracle.addPool(contract_glp3.address, {"from": accounts[0]})
    chain.sleep(3600*24*31)
    chain.mine()
    
    assert contract_glp.poolWeight() < 50
    
    
    contract_glp.requestMigration(new_addr, {"from": accounts[0]})
    
    with reverts("Mint paused"):
        contract_glp.mintSwap(1e18, 0, {"from": accounts[0]})
    
    assert contract_glp.isMigrationRequested() == True
    assert abs(contract_glp.timestampMigrationRequest() - chain.time()) <= 2
    assert contract_glp.migrationPool() == contract_glp3.address
    assert contract_glp.isMintPaused() == True
    assert contract_oracle.isAnyPoolMigrating() == True
    assert contract_oracle.isMigratingPool(contract_glp.address) == True
    
    
    with reverts():
        contract_glp.migratePool({"from": accounts[0]})
        
    with_reduce_pool_weight(19, contract_glp, contract_glp2, contract_oracle)
    chain.sleep(3600*24*31)
    chain.mine()
    
    transfer_balance_gex = contract_glp.balanceGEX()
    transfer_balance_collat = contract_glp.balanceCollateral()
    init_minted_amount = contract_glp.initMintedAmount()
    
    
    contract_glp.migratePool({"from": accounts[0]})

    
    assert contract_glp.isMigrationRequested() == False
    assert contract_glp.balanceGEX() == 0
    assert contract_glp.balanceCollateral() == 0
    assert contract_gex.balanceOf(contract_glp.address) >= 0
    assert contract_token.balanceOf(contract_glp.address) == 0
    
    assert contract_glp3.balanceGEX() == transfer_balance_gex
    assert contract_glp3.balanceCollateral() == transfer_balance_collat
    assert contract_glp3.initMintedAmount() == init_minted_amount
    assert contract_gex.balanceOf(contract_glp3.address) == transfer_balance_gex
    assert contract_token.balanceOf(contract_glp3.address) == transfer_balance_collat
    
    
    assert contract_oracle.isAnyPoolMigrating() == False
    assert contract_oracle.isMigratingPool(contract_glp.address) == False
    assert contract_oracle.isPool(contract_glp.address) == False
    
    
    chain.revert()




def test_removePool(contract_glp, contract_glp2, contract_glp3, contract_oracle, 
                    contract_token, contract_token2, contract_gex):
    
    chain.snapshot()
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_token.balanceOf(contract_glp.address)
    
    
    with reverts():
        contract_glp.requestRemove({"from": accounts[0]})
        
    
    with_some_prev_mints(contract_glp, contract_token, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
    with_reduce_pool_weight(45, contract_glp, contract_glp2, contract_oracle)
    
    assert contract_glp.poolWeight() < 50
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    contract_glp.requestRemove({"from": accounts[0]})
    
    with reverts("Mint paused"):
        contract_glp.mintSwap(1e18, 0, {"from": accounts[0]})
    
    assert contract_glp.isRemoveRequested() == True
    assert abs(contract_glp.timestampMigrationRequest() - chain.time()) <= 1
    assert contract_glp.isMintPaused() == True
    assert contract_oracle.isAnyPoolRemoving() == True
    assert contract_oracle.isRemovingPool(contract_glp.address) == True
    
    
    with reverts():
        contract_glp.removePool({"from": accounts[0]})
        
    with_reduce_pool_weight(9, contract_glp, contract_glp2, contract_oracle)
    chain.sleep(3600*24*31)
    chain.mine()
    
    init_owner_gex_balance = contract_gex.balanceOf(accounts[0])
    init_owner_collat_balance = contract_token.balanceOf(accounts[0])
    remove_balance_gex = contract_gex.balanceOf(contract_glp.address)
    remove_balance_collat = contract_token.balanceOf(contract_glp.address)
    
    
    contract_glp.removePool({"from": accounts[0]})

    
    assert contract_glp.isRemoveRequested() == False
    assert contract_glp.balanceGEX() == 0
    assert contract_glp.balanceCollateral() == 0
    assert contract_gex.balanceOf(contract_glp.address) == 0
    assert contract_token.balanceOf(contract_glp.address) == 0
    
    assert contract_gex.balanceOf(accounts[0]) == init_owner_gex_balance + remove_balance_gex
    assert contract_token.balanceOf(accounts[0]) == init_owner_collat_balance + remove_balance_collat
    
    assert contract_oracle.isAnyPoolRemoving() == False
    assert contract_oracle.isRemovingPool(contract_glp.address) == False
    assert contract_oracle.isPool(contract_glp.address) == False
    
    
    chain.sleep(3600)
    chain.mine()
    chain.revert()


def test_pass(contract_glp): pass



"""
PRIVATE FUNCTIONS TESTS
"""

# def test_pre_updateOracle(contract_glp, contract_token, contract_oracle):
    
#     with_many_prev_mints(contract_glp, contract_token, contract_oracle)

# @given(amount = strategy('uint128'))
# def test_updateOracle(contract_glp, amount):
    
#     contract_glp._updateOracle(amount)



# def test_pre_initOutGEXAmount(contract_glp):
    
#     contract_glp.setArbitrageur(accounts[7], {"from": accounts[0]})

# # Math of this function is fully tested on python simulations
# @given(amount = strategy('uint128'))
# def test_initOutGEXAmount(contract_glp, amount):
    
#     contract_glp._initOutGEXAmount(amount, {"from": accounts[7]})
    
    

"""
AD HOC TEST
"""

# @given(amount = strategy('uint64', min_value=1), 
#        balanceGEX = strategy('uint128', min_value=1), 
#        balanceCollateral = strategy('uint128'), 
#        mintRatio = strategy('uint32', min_value=0, max_value=2e6))
# def test_amountOutGEX(contract_glp, contract_token, contract_oracle, 
#                       amount, balanceGEX, balanceCollateral, mintRatio):
    
#     contract_glp.amountOutGEX(amount, balanceGEX, balanceCollateral, mintRatio)
    

    
    
# @given(amount = strategy('uint128', min_value=1), 
#        balanceGEX = strategy('uint128', min_value=1), 
#        balanceCollateral = strategy('uint128', min_value=1), 
#        burnRatio = strategy('uint32', min_value=0, max_value=2e6))
# def test_amountOutCollateral(contract_glp, contract_token, contract_oracle, 
#                       amount, balanceGEX, balanceCollateral, burnRatio):
    
#     contract_glp.amountOutCollateral(amount, balanceGEX, balanceCollateral, burnRatio)




"""
CONTEXT FUNCTIONS
"""
# chain revert should be used if this approach is used for test isolation

def with_setSCMinter(contract_glp, contract_scminter):
    
    if contract_glp.scMinter() != contract_scminter.address:
        contract_glp.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    
    return contract_scminter.address
    

def with_setOracle(contract_glp, contract_oracle):
    
    contract_glp.setOracle(contract_oracle.address, {"from": accounts[0]})
    
    return contract_oracle.address
    

def with_setArbitrageur(contract_glp):
    
    contract_glp.setArbitrageur(accounts[7], {"from": accounts[0]})
    
    return accounts[7]


def with_setLender(contract_glp):
    
    if contract_glp.treasuryLender() != accounts[5]:
        contract_glp.setLender(accounts[5], {"from": accounts[0]})
    
    return accounts[5]


def with_setCollector(contract_glp):
    
    contract_glp.setCollector(accounts[6], {"from": accounts[0]})
    
    return accounts[6]


def with_tradeInit(contract_glp, contract_token, contract_oracle):
    
    with_setOracle(contract_glp, contract_oracle)
    arb_address = with_setArbitrageur(contract_glp)
    contract_token.approve(contract_glp.address, 2**256-1, {"from": arb_address})
    
    amount = 1000 * int(1e36) / contract_glp.collateralPrice()
    contract_glp.mintSwap(amount, 0, {"from": arb_address})
    
    chain.sleep(3600)
    chain.mine()


def with_some_prev_mints(contract_glp, contract_token, contract_oracle):
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    amount = 1000 * int(1e36) / contract_glp.collateralPrice()
    
    for i in range(5):
        print(i)
        chain.sleep(3600)
        chain.mine()
        contract_glp.mintSwap(amount, 0, {"from": accounts[0]})
        
    chain.sleep(3600)
    chain.mine()
    
    
    
def with_many_prev_mints(contract_glp, contract_token, contract_oracle):
    
    with_tradeInit(contract_glp, contract_token, contract_oracle)
    
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    amount = 1000 * int(1e36) / contract_glp.collateralPrice()
    
    for i in range(20):
        print(i)
        chain.sleep(i*3600)
        chain.mine()
        contract_glp.mintSwap(i*amount, 0, {"from": accounts[0]})
        
    chain.sleep(3600)
    chain.mine()
    
        

def with_some_usdi_minted(contract_scminter, contract_glp, contract_token, 
                          contract_oracle, contract_gex, contract_usdi):
    
    with_many_prev_mints(contract_glp, contract_token, contract_oracle)

    contract_gex.approve(contract_scminter.address, 2**256-1, {"from": accounts[0]})
    amount = contract_glp.balanceGEX() / 50
    contract_scminter.mintStablecoin(contract_usdi.address, amount, {"from": accounts[0]})



def with_reduce_pool_weight(target_weight, contract_glp, contract_glp2, contract_oracle): 
    
    actual_weight = contract_oracle.getPoolCollatWeight(contract_glp.address)
    
    while actual_weight > target_weight:
    
        print(f'Actual weight pool 1: {actual_weight}')
        print(f'Weight pool 1: {contract_glp.poolWeight()}')
        local_target_weight = max(contract_glp.poolWeight() - 49, target_weight)
        contract_glp.setPoolWeight(local_target_weight, {"from": accounts[0]})
        contract_glp2.setPoolWeight(contract_glp2.poolWeight() + 50, {"from": accounts[0]})
        
        i = 0
        while actual_weight > local_target_weight:
            i+=1
            print(i)
            chain.sleep(2*i*3600)
            chain.mine()
            tx = contract_glp2.mintSwap(i*int(1e17), 0, {"from": accounts[0]})
            contract_glp.redeemSwap(tx.return_value, 0, {"from": accounts[0]})
            actual_weight = contract_oracle.getPoolCollatWeight(contract_glp.address)
    
    print('End reduce weight')
    print(f'Actual weight pool 1: {actual_weight}')
    print(f'Weight pool 1: {contract_glp.poolWeight()}')
            


"""
AUXILIARY FUNCTIONS
"""

def expected_fee(amount, baseMintFee):
    
    usdAmount = amount * 0.01
    
    if usdAmount < 1000:
        fee = baseMintFee
    
    elif usdAmount < 10000:
        fee = baseMintFee + int(500 * (usdAmount - 1000) / 9000)
    
    elif usdAmount < 100000:
        fee = baseMintFee + 500 + int(500 * (usdAmount - 10000) / 90000)
    
    elif usdAmount < 1000000:
        fee = baseMintFee + 1000 + int(1000 * (usdAmount - 100000) / 900000)
    
    else:
        fee = baseMintFee + 2000
        
    return fee












