# -*- coding: utf-8 -*-
"""
Created on Fri Jul 22 19:44:23 2022

@author: Geminon
"""

from inspect import getsourcefile
import os
import sys
# Insert this folder into the python path to allow imports from other test scripts
sys.path.insert(0, os.path.dirname(getsourcefile(lambda:0)))

from brownie import accounts, reverts, convert
from brownie import (MockV3Aggregator, 
                     GEX, 
                     MockERC20,
                     MockERC20Indexed,
                     GenesisLiquidityPool,
                     GenesisLiquidityPoolNative,
                     GeminonOracle,
                     SCMinter
                     )
from brownie.network.state import Chain
from brownie.test import given, strategy
from pytest import fixture

import numpy as np

from test_glp import deploy_args
from test_glp import with_setSCMinter, with_setOracle, with_setArbitrageur, with_setLender, with_setCollector
from test_glp import with_some_prev_mints, with_reduce_pool_weight

chain = Chain()

ZERO_ADDRESS = convert.to_address('0x' + '0'*40)


deploy_args['GenLiqPoolNat'] = [None, # gexToken address of the GEX token contract
                                500, # poolWeight_ integer percentage 3 decimals [1, 1000] (1e3)
                                0.001 * 1e18, # initPoolPrice_ must be in 1e18 USD units
                                ]


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
def contract_token2():
    
    contract = MockERC20.deploy(*deploy_args['Token2'], {"from": accounts[0]})
    decimals = deploy_args['Token2'][3]
    for i in range(8):
        contract.transfer(accounts[i+1], 1e6 * 10**decimals, {"from": accounts[0]})
    
    return contract


@fixture(scope='module')
def contract_usdi():
    
    return MockERC20Indexed.deploy(*deploy_args['USDI'], {"from": accounts[0]})


@fixture(scope='module')
def contract_glp(contract_gex, contract_pricefeed):
    
    owner_account = accounts[0]
    
    deploy_args['GenLiqPoolNat'][0] = contract_gex.address
    
    return GenesisLiquidityPoolNative.deploy(*deploy_args['GenLiqPoolNat'], 
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
def contract_glp3(contract_gex, contract_pricefeed):
    
    owner_account = accounts[0]
    
    deploy_args['GenLiqPoolNat'][0] = contract_gex.address
    
    return GenesisLiquidityPoolNative.deploy(*deploy_args['GenLiqPoolNat'], 
                                              {"from": owner_account})


@fixture(scope='module')
def contract_oracle(contract_glp, contract_glp2):
    
    return GeminonOracle.deploy([contract_glp.address, contract_glp2.address], 
                                {"from": accounts[0]})


@fixture(scope='module')
def contract_scminter(contract_gex, contract_oracle, contract_usdi):
    
    deploy_args['SCMinter'][0] = contract_gex.address
    deploy_args['SCMinter'][1] = contract_usdi.address
    deploy_args['SCMinter'][2] = contract_oracle.address
    
    return SCMinter.deploy(*deploy_args['SCMinter'], 
                            {"from": accounts[0]})
    
    




def test_constructor(contract_glp):
    
    poolWeight = deploy_args['GenLiqPoolNat'][1]
    initPoolPrice = deploy_args['GenLiqPoolNat'][2]
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
    
    
    
from test_glp import test_initialize, test_pricefeed, test_pricefeed2        
from test_glp import test_setSCMinter, test_setOracle, test_setLender, test_setCollector, test_setArbitrageur
from test_glp import test_setMintFee, test_setRedeemFee, test_setMintRates
from test_glp import test_requestAddAddress, test_requestRemoveAddress, test_requestAddressChange
from test_glp import test_applyPriceFeedChange, test_applyPriceFeedChange, test_applySCMinterChange
from test_glp import test_applyOracleChange, test_applyLenderChange, test_cancelChangeRequests
from test_glp import test_variableFee, test_amountFeeMint, test_amountFeeRedeem
from test_glp import test_pauseMint, test_unpauseMint, test_bailoutMinter





def test_setPoolWeight(contract_glp, contract_glp2, contract_token2, contract_oracle):
    
    chain.snapshot()
    with_setOracle(contract_glp, contract_oracle)
    with_setOracle(contract_glp2, contract_oracle)
    arb_addr = with_setArbitrageur(contract_glp)
    arb_addr2 = with_setArbitrageur(contract_glp2)
    
    
    prev_weight = contract_glp.poolWeight()
    
    assert prev_weight == deploy_args['GenLiqPoolNat'][1]
    
    
    with reverts('dev: invalid weight value'):
        contract_glp.setPoolWeight(0, {"from": accounts[0]})
        
    with reverts('dev: weight is the same'):
        contract_glp.setPoolWeight(prev_weight, {"from": accounts[0]})
    
    with reverts('dev: weight change too big'):
        contract_glp.setPoolWeight(prev_weight + 51, {"from": accounts[0]})
        
    with reverts('dev: weight change too big'):
        contract_glp.setPoolWeight(prev_weight - 51, {"from": accounts[0]})
        
    
    contract_glp.mintSwapNative(0, {"from": arb_addr, "value": 1e18})
    oracle_pool_weight1 = contract_oracle.getPoolCollatWeight(contract_glp.address) / 1e15
    
    assert contract_glp.balanceCollateral() > 0
    assert oracle_pool_weight1 != 0
    
    
    contract_token2.approve(contract_glp2.address, 2**256-1, {"from": arb_addr2})
    contract_glp2.mintSwap(1e18, 0, {"from": arb_addr2})
    oracle_pool_weight2 = contract_oracle.getPoolCollatWeight(contract_glp2.address) / 1e15
    
    assert contract_glp2.balanceCollateral() > 0
    assert oracle_pool_weight2 != 0
    
    new_weight = prev_weight - 50
    expected_poolsupply = round(100000000 * new_weight / 1000) * int(1e18)
    
    contract_glp.setPoolWeight(new_weight, {"from": accounts[0]})
    
    assert contract_glp.poolSupply() == expected_poolsupply
    assert contract_glp.poolWeight() == deploy_args['GenLiqPoolNat'][1] - 50
    
    actualWeight = (contract_glp.getCollateralValue() *1e3) / contract_oracle.getTotalCollatValue();
    print(actualWeight, contract_glp.poolWeight())
    contract_glp.setPoolWeight(contract_glp.poolWeight() - 50, {"from": accounts[0]})
    
    assert contract_glp.poolWeight() == deploy_args['GenLiqPoolNat'][1] - 100
        
    with reverts('dev: oracle weight change too big'):
        contract_glp.setPoolWeight(contract_glp.poolWeight() - 50, {"from": accounts[0]})
    
    chain.revert()


  
# Math of this function is fully tested on python simulations
@given(amount = strategy('uint128'))
def test_amountOutGEX(contract_glp, contract_oracle, amount):
    
    chain.snapshot()
    
    with_tradeInit_native(contract_glp, contract_oracle)
    
    
    # mintratio = contract_glp._mintRatio()
    # burnratio = contract_glp._burnRatio()
    
    # assert mintratio >= int(1e6)
    # assert mintratio <= int(2*1e6)
    # assert burnratio >= int(1e6)
    # assert burnratio <= int(2*1e6)
    
    assert contract_glp.amountMint(amount) >= 0
    assert contract_glp.amountBurn(amount) >= 0
    
    assert contract_glp.amountOutGEX(amount) >= 0
    
    chain.revert()
    
    
# Math of this function is fully tested on python simulations
@given(amount = strategy('uint128'))
def test_amountOutCollateral(contract_glp, contract_oracle, amount):
    
    chain.snapshot()
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
    
    # mintratio = contract_glp._mintRatio()
    # burnratio = contract_glp._burnRatio()
    
    # assert mintratio >= int(1e6)
    # assert mintratio <= int(2*1e6)
    # assert burnratio >= int(1e6)
    # assert burnratio <= int(2*1e6)
    
    assert contract_glp.amountMint(amount) >= 0
    assert contract_glp.amountBurn(amount) >= 0
    
    assert contract_glp.amountOutCollateral(amount) >= 0
    
    chain.revert()



        
def test_mintSwap_redeemSwap(contract_glp, contract_gex, contract_oracle):
    
    chain.snapshot()
    
    with_tradeInit_native(contract_glp, contract_oracle)
    
    
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(10):
        print(i)
        chain.sleep(3600*3)
        chain.mine()
        contract_glp.mintSwapNative(0, {"from": accounts[0], 'value': 5*1e18})
        
    
    balanceGEX = contract_gex.balanceOf(accounts[0])
    amount = int(balanceGEX / 51)
    
    for i in range(20):
        print(i)
        print(contract_gex.balanceOf(accounts[0])/1e18)
        print(amount/1e18)
        print(contract_glp.amountOutCollateral(amount)/1e18)
        chain.sleep(600)
        chain.mine()
        contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
        
    assert contract_glp.balanceGEX() < contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_glp.balance()
        
    chain.revert()
        
        
    
    
def test_mintRedeem_alt(contract_glp, contract_gex, contract_oracle):
    
    chain.snapshot()
    
    with_tradeInit_native(contract_glp, contract_oracle)
   
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(20):
        print(i)
        
        contract_glp.mintSwapNative(0, {"from": accounts[0], "value": 3*1e18})
        chain.sleep(3600)
        chain.mine()

        amount = contract_gex.balanceOf(accounts[0])
        contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
        
    
    assert contract_glp.balanceGEX() < contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_glp.balance()
    
    chain.revert()
            
          

def test_mintRedeem_rand(contract_glp, contract_gex, contract_oracle):
    
    chain.snapshot()
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
  
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(100):
        print(i)
        op = np.random.choice([0,1])
        
        if op > 0:
            amount = np.random.randint(0, 100) * int(1e18)
            contract_glp.mintSwapNative(0, {"from": accounts[0], "value": amount})
        
        else:
            balance = int(contract_gex.balanceOf(accounts[0]) / 1e18)
            amount = np.random.randint(0, balance) * int(1e18)

            contract_glp.redeemSwap(amount, 0, {"from": accounts[0]})
        
        chain.sleep(np.random.randint(1, 10000))
        chain.mine()
 
    chain.revert()
            
            
            
def test_multiPool_rand(contract_glp, contract_glp2, contract_gex, 
                        contract_token2, contract_oracle):
    
    chain.snapshot()
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
 
    contract_gex.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    contract_gex.approve(contract_glp2.address, 2**256-1, {"from": accounts[0]})
    contract_token2.approve(contract_glp.address, 2**256-1, {"from": accounts[0]})
    
    for i in range(500):
        print(i)
        op = np.random.choice([0,1])
        pool = np.random.choice([0,1])
        
        if op > 0:
            value = np.random.randint(0, 10000) * int(1e18) 
            
            if pool > 0:
                amount1 = value * 1e18 / contract_glp.collateralPrice()
                contract_glp.mintSwapNative(0, {"from": accounts[0], "value": amount1})
            
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


    
    
def test_matchBalancesNative(contract_glp, contract_gex):
    
    with reverts():
        contract_glp.matchBalances({"from": accounts[1]})
    
    with reverts('dev: Balances match'):
        contract_glp.matchBalances({"from": accounts[0]})
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() == contract_glp.balance()



def test_lendCollateralNative(contract_glp, contract_scminter, 
                        contract_oracle, contract_gex, contract_usdi):
    
    chain.snapshot()
    
    
    with reverts('dev: null amount'):
        contract_glp.lendCollateral(0, {"from": accounts[0]})
        
    with reverts('dev: pool empty'):
        contract_glp.lendCollateral(1e18, {"from": accounts[0]})
        
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
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
    with_some_usdi_minted_native(contract_scminter, contract_glp, 
                          contract_oracle, contract_gex, contract_usdi)
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    balance_collat = contract_glp.balanceCollateral()
    
    tx = contract_glp.lendCollateral(balance_collat, {"from": lender_addr})
    
    assert tx.return_value == contract_glp.balanceLent()
    assert lender_addr.balance() >= contract_glp.balanceLent()
    
    chain.revert()


def test_repayCollateralNative(contract_glp, contract_scminter, 
                                contract_oracle, contract_gex, contract_usdi):
    
    chain.snapshot()
    
    # with reverts('dev: Nothing to repay'):
    with reverts():
        contract_glp.repayCollateral(0, {"from": accounts[0]})
        
    
    lender_addr = with_setLender(contract_glp)
    contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
    with_setSCMinter(contract_glp, contract_scminter)
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    with_some_usdi_minted_native(contract_scminter, contract_glp, 
                          contract_oracle, contract_gex, contract_usdi)
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    balance_collat = contract_glp.balanceCollateral()
    
    contract_glp.lendCollateral(balance_collat, {"from": lender_addr})
    
    
    # with reverts('dev: invalid caller address'):
    with reverts():
        contract_glp.repayCollateral(1e18, {"from": accounts[0]})
        
    amount = contract_glp.balanceLent()
    tx = contract_glp.repayCollateralNative({"from": lender_addr, 'value': amount})
    
    assert tx.return_value == amount
    assert contract_glp.balanceLent() == 0
        
    chain.revert()


def test_collectFees(contract_glp, contract_oracle, contract_gex):
    
    chain.snapshot()
    
    # with reverts('dev: Nothing to collect'):
    with reverts():
        contract_glp.collectFees({"from": accounts[0]})
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
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
    

def test_getMintInfo(contract_glp, contract_oracle):
    
    chain.snapshot()
    
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
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


def test_getRedeemInfo(contract_glp, contract_oracle):
    
    chain.snapshot()
    
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    
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
                    contract_token2, contract_gex):
    
    chain.snapshot()
    
    new_addr = contract_glp3.address
    assert contract_glp3.collateralPrice()
    assert contract_glp3.balanceGEX() == 0
    assert contract_glp3.balanceCollateral() == 0
    assert contract_glp3.getCollateralValue() == 0
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() <= contract_glp.balance()
    
    with reverts():
        contract_glp.requestMigration(new_addr, {"from": accounts[0]})
        
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
    with_reduce_pool_weight(49, contract_glp, contract_glp2, contract_oracle, contract_gex)
    
    with_setOracle(contract_glp3, contract_oracle)
    contract_oracle.requestAddAddress(contract_glp3.address, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_oracle.addPool(contract_glp3.address, {"from": accounts[0]})
    chain.sleep(3600*24*31)
    chain.mine()
    
    assert contract_glp.poolWeight() < 50
    
    
    contract_oracle.requestAddressChange(contract_glp.address, contract_glp3.address, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_glp.requestMigration(new_addr, {"from": accounts[0]})
    
    with reverts("Mint paused"):
        contract_glp.mintSwapNative(0, {"from": accounts[0], "value": 1e18})
    
    assert contract_glp.isMigrationRequested() == True
    assert abs(contract_glp.timestampMigrationRequest() - chain.time()) <= 2
    assert contract_glp.migrationPool() == contract_glp3.address
    assert contract_glp.isMintPaused() == True
    assert contract_oracle.isAnyPoolMigrating() == True
    assert contract_oracle.isMigratingPool(contract_glp.address) == True
    
    
    with reverts():
        contract_glp.migratePool({"from": accounts[0]})
        
    with_reduce_pool_weight(19, contract_glp, contract_glp2, contract_oracle, contract_gex)
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
    assert contract_glp.balance() == 0
    
    assert contract_glp3.balanceGEX() == transfer_balance_gex
    assert contract_glp3.balanceCollateral() == transfer_balance_collat
    assert contract_glp3.initMintedAmount() == init_minted_amount
    assert contract_gex.balanceOf(contract_glp3.address) == transfer_balance_gex
    assert contract_glp3.balance() >= transfer_balance_collat
    
    
    assert contract_oracle.isAnyPoolMigrating() == False
    assert contract_oracle.isMigratingPool(contract_glp.address) == False
    assert contract_oracle.isPool(contract_glp.address) == False
    
    
    chain.revert()




def test_removePool(contract_glp, contract_glp2, contract_glp3, contract_oracle, 
                    contract_token2, contract_gex):
    
    chain.snapshot()
    
    assert contract_glp.balanceGEX() >= contract_gex.balanceOf(contract_glp.address)
    assert contract_glp.balanceCollateral() <= contract_glp.balance()
    
    
    with reverts():
        contract_glp.requestRemove({"from": accounts[0]})
        
    
    with_some_prev_mints_native(contract_glp, contract_oracle)
    with_some_prev_mints(contract_glp2, contract_token2, contract_oracle)
    with_reduce_pool_weight(45, contract_glp, contract_glp2, contract_oracle, contract_gex)
    
    assert contract_glp.poolWeight() < 50
    
    chain.sleep(3600*24*31)
    chain.mine()
    
    contract_oracle.requestRemoveAddress(contract_glp.address, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_glp.requestRemove({"from": accounts[0]})
    
    with reverts("Mint paused"):
        contract_glp.mintSwapNative(0, {"from": accounts[0], "value": 1e18})
    
    assert contract_glp.isRemoveRequested() == True
    assert abs(contract_glp.timestampMigrationRequest() - chain.time()) <= 1
    assert contract_glp.isMintPaused() == True
    assert contract_oracle.isAnyPoolRemoving() == True
    assert contract_oracle.isRemovingPool(contract_glp.address) == True
    
    
    with reverts():
        contract_glp.removePool({"from": accounts[0]})
        
    with_reduce_pool_weight(9, contract_glp, contract_glp2, contract_oracle, contract_gex)
    chain.sleep(3600*24*31)
    chain.mine()
    
    init_owner_gex_balance = contract_gex.balanceOf(accounts[0])
    init_owner_collat_balance = accounts[0].balance()
    remove_balance_gex = contract_gex.balanceOf(contract_glp.address)
    remove_balance_collat = contract_glp.balance()
    
    
    contract_glp.removePool({"from": accounts[0]})

    
    assert contract_glp.isRemoveRequested() == False
    assert contract_glp.balanceGEX() == 0
    assert contract_glp.balanceCollateral() == 0
    assert contract_gex.balanceOf(contract_glp.address) == 0
    assert contract_glp.balance() == 0
    
    assert contract_gex.balanceOf(accounts[0]) == init_owner_gex_balance + remove_balance_gex
    assert accounts[0].balance() == init_owner_collat_balance + remove_balance_collat
    
    assert contract_oracle.isAnyPoolRemoving() == False
    assert contract_oracle.isRemovingPool(contract_glp.address) == False
    assert contract_oracle.isPool(contract_glp.address) == False
    
    
    chain.sleep(3600)
    chain.mine()
    chain.revert()
    
    




"""
CONTEXT FUNCTIONS
"""
# chain revert should be used if this approach is used for test isolation

def with_some_usdi_minted_native(contract_scminter, contract_glp, 
                          contract_oracle, contract_gex, contract_usdi):
    
    with_many_prev_mints_native(contract_glp, contract_oracle)

    contract_gex.approve(contract_scminter.address, 2**256-1, {"from": accounts[0]})
    amount = contract_glp.balanceGEX() / 50
    contract_scminter.mintStablecoin(contract_usdi.address, amount, {"from": accounts[0]})



def with_tradeInit_native(contract_glp, contract_oracle):
    
    with_setOracle(contract_glp, contract_oracle)
    arb_address = with_setArbitrageur(contract_glp)
    
    amount = 1000 * int(1e36) / contract_glp.collateralPrice()
    contract_glp.mintSwapNative(0, {"from": arb_address, "value": amount})
    
    chain.sleep(3600)
    chain.mine()


def with_some_prev_mints_native(contract_glp, contract_oracle):
    
    with_tradeInit_native(contract_glp, contract_oracle)
    
    amount = 1000 * int(1e36) / contract_glp.collateralPrice()
    
    for i in range(5):
        print(i)
        chain.sleep(3600)
        chain.mine()
        contract_glp.mintSwapNative(0, {"from": accounts[0], "value": amount})
        
    chain.sleep(3600)
    chain.mine()
    
    
    
def with_many_prev_mints_native(contract_glp, contract_oracle):
    
    with_tradeInit_native(contract_glp, contract_oracle)
    
    amount = 10000 * int(1e36) / contract_glp.collateralPrice()
    
    for i in range(10):
        print(i)
        chain.sleep(i*3600)
        chain.mine()
        contract_glp.mintSwapNative(0, {"from": accounts[0], "value": amount})
        
    chain.sleep(3600)
    chain.mine()
    







