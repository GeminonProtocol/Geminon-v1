# -*- coding: utf-8 -*-
"""
Created on Sun Sep 11 07:08:24 2022

@author: Geminon
"""

import sys
sys.path.insert(0, 'D:/Proyectos/Geminon/solidity/dev/tests')

from brownie import accounts, reverts, convert
from brownie import (MockV3Aggregator, 
                     GEX, 
                     MockERC20,
                     GenesisLiquidityPool,
                     GeminonOracle,
                     BridgeV0
                     )
from brownie.network.state import Chain
from pytest import fixture

from test_glp import deploy_args, initialize_args, with_some_prev_mints

chain = Chain()

ZERO_ADDRESS = convert.to_address('0x' + '0'*40)


deploy_args.update({'Bridge': [None, None, None, None]})



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
def contract_glp(contract_gex, contract_pricefeed, contract_token):
    
    deploy_args['GenLiqPool'][0] = contract_gex.address
    deploy_args['GenLiqPool'][1] = contract_token.address
    
    return GenesisLiquidityPool.deploy(*deploy_args['GenLiqPool'], 
                                       {"from": accounts[0]})


@fixture(scope='module')
def contract_glp2(contract_glp, contract_gex, contract_pricefeed2, contract_token2):
    
    deploy_args['GenLiqPool'][0] = contract_gex.address
    deploy_args['GenLiqPool'][1] = contract_token2.address
    
    return GenesisLiquidityPool.deploy(*deploy_args['GenLiqPool'], 
                                       {"from": accounts[0]})



@fixture(scope='module')
def contract_oracle(contract_glp, contract_glp2):
    
    return GeminonOracle.deploy([contract_glp.address, contract_glp2.address], 
                                {"from": accounts[0]})


@fixture(scope='module')
def contract_bridge(contract_gex, contract_oracle):
    
    deploy_args['Bridge'][0] = contract_gex.address
    deploy_args['Bridge'][1] = accounts[7]  # Arbitrageur
    deploy_args['Bridge'][2] = accounts[8]  # Validator
    deploy_args['Bridge'][3] = contract_oracle.address
    
    return BridgeV0.deploy(*deploy_args['Bridge'], 
                           {"from": accounts[0]})



@fixture(scope='module')
def initialize(contract_gex, contract_glp, contract_glp2, contract_pricefeed, 
               contract_pricefeed2, contract_oracle, contract_bridge):
    
    pools = [contract_glp.address, contract_glp2.address, contract_bridge.address]
    contract_gex.initialize(pools, {"from": accounts[0]})
    
    initialize_args['GenLiqPool'][1] = contract_oracle.address
    
    initialize_args['GenLiqPool'][2] = contract_pricefeed.address
    contract_glp.initialize(*initialize_args['GenLiqPool'], 
                            {"from": accounts[0]})
    
    initialize_args['GenLiqPool'][2] = contract_pricefeed2.address
    contract_glp2.initialize(*initialize_args['GenLiqPool'], 
                             {"from": accounts[0]})
    
    contract_glp.unpauseMint({"from": accounts[0]})
    contract_glp2.unpauseMint({"from": accounts[0]})
    



def test_constructor(contract_bridge, contract_oracle, initialize):
    
    assert contract_bridge.valueLimit() == 10000 * 1e18
    assert contract_bridge.balanceVirtualGEX() == 0
    assert contract_bridge.arbitrageur() == accounts[7]
    assert contract_bridge.validator() == accounts[8]
    
    

def test_sendGEX(contract_bridge, contract_glp, contract_glp2, contract_gex, 
                 contract_token, contract_token2, contract_oracle):
    
    chain.snapshot()
    
    
    with_some_prev_mints(contract_glp, contract_token, None)
    with_some_prev_mints(contract_glp2, contract_token2, None)
    
    contract_gex.approve(contract_bridge.address, 2**256-1, {"from": accounts[0]})
    gex_available = contract_gex.balanceOf(accounts[0])
    with reverts():
        contract_bridge.sendGEX(gex_available, {"from": accounts[0]})
        
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[8]})
    contract_glp.mintSwap(10*1e18, 0, {"from": accounts[8]})
    contract_gex.approve(contract_bridge.address, 2**256-1, {"from": accounts[8]})
    gex_available = contract_gex.balanceOf(accounts[8])
    with reverts():
        contract_bridge.sendGEX(gex_available, {"from": accounts[8]})
        
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[1]})
    contract_glp.mintSwap(10*1e18, 0, {"from": accounts[1]})
    contract_gex.approve(contract_bridge.address, 2**256-1, {"from": accounts[1]})
    gex_available = contract_gex.balanceOf(accounts[1])
    with reverts():
        contract_bridge.sendGEX(gex_available, {"from": accounts[1]})
    
    
    contract_token.approve(contract_glp.address, 2**256-1, {"from": accounts[7]})
    for i in range(5):
        chain.sleep(3600*12)
        chain.mine()
        contract_glp.mintSwap(10*1e18, 0, {"from": accounts[7]})
    
    contract_gex.approve(contract_bridge.address, 2**256-1, {"from": accounts[7]})
    gex_available = contract_gex.balanceOf(accounts[7])
    contract_bridge.sendGEX(gex_available, {"from": accounts[7]})
    
    chain.revert()
    
    

def test_validateClaim(contract_bridge):
    
    chain.snapshot()
    
    with reverts():
        contract_bridge.validateClaim(accounts[7], 1e18, {"from": accounts[1]})
    
    with reverts():
        contract_bridge.validateClaim(accounts[7], 1e18, {"from": accounts[0]})
    
    with reverts():
        contract_bridge.validateClaim(accounts[0], 1e18, {"from": accounts[8]})
    
    contract_bridge.validateClaim(accounts[7], 1e18, {"from": accounts[8]})
    
    chain.revert()
    
    
    
def test_claimGEX(contract_bridge, contract_glp, contract_glp2, contract_gex, 
                 contract_token, contract_token2, contract_oracle):
    
    chain.snapshot()

    contract_bridge.validateClaim(accounts[7], 1e18, {"from": accounts[8]})
    
    with reverts():
        contract_bridge.claimGEX(1e18, {"from": accounts[0]})
        
    with reverts():
        contract_bridge.claimGEX(1e18, {"from": accounts[8]})
        
    with reverts():
        contract_bridge.claimGEX(1e18, {"from": accounts[1]})

    price = contract_oracle.getSafePrice()
    big_amount = 1 + 10000*1e36 / price
    contract_bridge.validateClaim(accounts[7], big_amount, {"from": accounts[8]})
    with reverts():
        contract_bridge.claimGEX(big_amount, {"from": accounts[7]})
    
    
    amount = contract_bridge.getMaxMintable({"from": accounts[7]})
    print(amount/1e18, price/1e18, amount * price / 1e36)
    contract_bridge.claimGEX(amount, {"from": accounts[7]})
    
    with reverts():
        contract_bridge.claimGEX(amount, {"from": accounts[7]})
    
    chain.revert()
    























