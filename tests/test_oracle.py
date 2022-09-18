# -*- coding: utf-8 -*-
"""
Created on Thu Sep  8 03:07:44 2022

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
                     GeminonOracle,
                     SCMinter
                     )
from brownie.network.state import Chain
from pytest import fixture

import numpy as np

from test_glp import deploy_args, initialize_args, with_many_prev_mints
from test_glp import with_setSCMinter

chain = Chain()

ZERO_ADDRESS = convert.to_address('0x' + '0'*40)




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
    decimals = deploy_args['Token'][3]
    for i in range(8):
        contract.transfer(accounts[i+1], 1e6 * 10**decimals, {"from": accounts[0]})
    
    return contract


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
def contract_scminter(contract_gex, contract_oracle, contract_usdi):
    
    deploy_args['SCMinter'][0] = contract_gex.address
    deploy_args['SCMinter'][1] = contract_usdi.address
    deploy_args['SCMinter'][2] = contract_oracle.address
    
    return SCMinter.deploy(*deploy_args['SCMinter'], 
                           {"from": accounts[0]})
    
    

@fixture(scope='module')
def initialize(contract_gex, contract_glp, contract_glp2, contract_pricefeed, 
               contract_pricefeed2, contract_oracle):
    
    pools = [contract_glp.address, contract_glp2.address]
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
    



def test_constructor(contract_oracle, contract_glp, contract_glp2, contract_scminter):
    
    assert abs(contract_oracle.poolAge(contract_glp.address) - chain.time()) < 4
    assert abs(contract_oracle.poolAge(contract_glp2.address) - chain.time()) < 4
    assert contract_oracle.pools(0) == contract_glp.address
    assert contract_oracle.pools(1) == contract_glp2.address
    
    


def test_setSCMinter(contract_oracle, contract_scminter):
    
    chain.snapshot()
    
    assert contract_oracle.scMinter() == ZERO_ADDRESS
    
    with reverts():
        contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[1]})
        
    with reverts():
        contract_oracle.setSCMinter(ZERO_ADDRESS, {"from": accounts[0]})
        
    
    timestamp = chain.time()    
    contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
    
    assert contract_oracle.scMinter() == contract_scminter.address
    assert abs(contract_oracle.ageSCMinter() - timestamp) < 2
    
    with reverts():
        contract_oracle.setSCMinter(contract_scminter.address, {"from": accounts[0]})
        
    chain.revert()


def test_setTreasuryLender(contract_oracle):
    
    chain.snapshot()
    
    lender_addr = accounts[2]
    
    assert contract_oracle.treasuryLender() == ZERO_ADDRESS
    
    with reverts():
        contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[1]})
        
    with reverts():
        contract_oracle.setTreasuryLender(ZERO_ADDRESS, {"from": accounts[0]})
    
    
    timestamp = chain.time()
    contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
    
    assert contract_oracle.treasuryLender() == lender_addr
    assert abs(contract_oracle.ageTreasuryLender() - timestamp) < 2
    
    with reverts():
        contract_oracle.setTreasuryLender(lender_addr, {"from": accounts[0]})
        
    chain.revert()


def test_setCollector(contract_oracle):
    
    chain.snapshot()
    
    collector_addr = accounts[3]
    
    assert contract_oracle.feesCollector() == ZERO_ADDRESS
    
    with reverts():
        contract_oracle.setCollector(collector_addr, {"from": accounts[1]})
        
    
    timestamp = chain.time()
    contract_oracle.setCollector(collector_addr, {"from": accounts[0]})
    
    assert contract_oracle.feesCollector() == collector_addr
    assert abs(contract_oracle.ageFeesCollector() - timestamp) < 2
    
    chain.revert()
    


def test_addPool(contract_oracle):
    
    new_pool = accounts[4]
    
    with reverts():
        contract_oracle.requestAddAddress(new_pool, {"from": accounts[1]})
        
    contract_oracle.requestAddAddress(new_pool, {"from": accounts[0]})
    
    
    with reverts():
        contract_oracle.addPool(new_pool, {"from": accounts[0]})
        
    chain.sleep(3600*24*8)
    chain.mine()
    
    with reverts():
        contract_oracle.addPool(new_pool, {"from": accounts[1]})
        
    contract_oracle.addPool(new_pool, {"from": accounts[0]})
    
    assert abs(contract_oracle.poolAge(new_pool) - chain.time()) < 2
    assert contract_oracle.pools(2) == new_pool
    assert contract_oracle.isPool(new_pool) == True
    
    


def test_removePool(contract_oracle):
    
    rm_pool = accounts[4]
    
    with reverts():
        contract_oracle.requestRemoveAddress(rm_pool, {"from": accounts[1]})
        
    contract_oracle.requestRemoveAddress(rm_pool, {"from": accounts[0]})
    
    
    with reverts():
        contract_oracle.removePool(rm_pool, {"from": accounts[0]})
        
    chain.sleep(3600*24*8)
    chain.mine()
    
    with reverts():
        contract_oracle.removePool(rm_pool, {"from": accounts[1]})
        
    contract_oracle.removePool(rm_pool, {"from": accounts[0]})
    
    with reverts(): contract_oracle.pools(2)
    assert contract_oracle.isPool(rm_pool) == False



def test_requestMigratePool(contract_oracle, contract_glp, contract_glp2):
    
    chain.snapshot()
    
    new_pool = accounts[5]
    
    with reverts():
        contract_oracle.requestMigratePool(new_pool, {"from": contract_glp.address})
        
    
    with_addPool(contract_oracle, new_pool)
        
    with reverts():
        contract_oracle.requestMigratePool(new_pool, {"from": accounts[0]})
        
    with reverts():
        contract_oracle.requestMigratePool(new_pool, {"from": contract_glp.address})
        
    
    contract_oracle.requestAddressChange(contract_glp.address, new_pool, 
                                          {"from": accounts[0]})
    
    with reverts():
        contract_oracle.requestMigratePool(new_pool, {"from": contract_glp.address})
        
    chain.sleep(3600*24*8)
    chain.mine()    
    
    contract_oracle.requestMigratePool(new_pool, {"from": contract_glp.address})
    
    with reverts():
        contract_oracle.requestMigratePool(accounts[6], {"from": contract_glp2.address})
        
    assert contract_oracle.isPool(new_pool) == True
    assert contract_oracle.isMigratingPool(contract_glp.address) == True
    assert contract_oracle.isAnyPoolMigrating() == True

    chain.revert()
    
    


def test_setMigrationDone(contract_oracle, contract_glp, contract_glp2):
    
    chain.snapshot()
    
    new_pool = accounts[5]
    
    with reverts():
        contract_oracle.setMigrationDone({"from": contract_glp.address})
    
    
    with_requestMigratePool(contract_oracle, contract_glp, new_pool)
    
    with reverts():
        contract_oracle.setMigrationDone({"from": accounts[0]})
        
    with reverts():
        contract_oracle.setMigrationDone({"from": contract_glp2.address})
    
    contract_oracle.setMigrationDone({"from": contract_glp.address})
    
    assert contract_oracle.isPool(new_pool) == True
    assert contract_oracle.isPool(contract_glp.address) == False
    assert contract_oracle.isMigratingPool(contract_glp.address) == False
    assert contract_oracle.isAnyPoolMigrating() == False
    
    chain.revert()


def test_cancelMigration(contract_oracle, contract_glp):
    
    chain.snapshot()
    
    new_pool = accounts[5]
    
    with_requestMigratePool(contract_oracle, contract_glp, new_pool)
    
    with reverts():
        contract_oracle.cancelMigration({"from": accounts[0]})
        
    contract_oracle.cancelMigration({"from": contract_glp.address})
    
    assert contract_oracle.isPool(contract_glp.address) == True
    assert contract_oracle.isMigratingPool(contract_glp.address) == False
    assert contract_oracle.isAnyPoolMigrating() == False
    
    chain.revert()



def test_requestRemovePool(contract_oracle, contract_glp, contract_glp2):
    
    chain.snapshot()
        
    with reverts():
        contract_oracle.requestRemovePool({"from": accounts[0]})
        
    with reverts():
        contract_oracle.requestRemovePool({"from": contract_glp.address})
    
    
    contract_oracle.requestRemoveAddress(contract_glp.address, {"from": accounts[0]})
    
    with reverts():
        contract_oracle.requestRemovePool({"from": contract_glp.address})
        
    chain.sleep(3600*24*8)
    chain.mine()
    
    contract_oracle.requestRemovePool({"from": contract_glp.address})
    
    with reverts():
        contract_oracle.requestRemovePool({"from": contract_glp2.address})
        
    assert contract_oracle.isRemovingPool(contract_glp.address) == True
    assert contract_oracle.isAnyPoolRemoving() == True

    chain.revert()


def test_setRemoveDone(contract_oracle, contract_glp, contract_glp2):
    
    chain.snapshot()
    
    with_requestRemovePool(contract_oracle, contract_glp)
    
    with reverts():
        contract_oracle.setRemoveDone({"from": accounts[0]})
        
    with reverts():
        contract_oracle.setRemoveDone({"from": contract_glp2.address})
    
    contract_oracle.setRemoveDone({"from": contract_glp.address})
    
    assert contract_oracle.isPool(contract_glp.address) == False
    assert contract_oracle.isRemovingPool(contract_glp.address) == False
    assert contract_oracle.isAnyPoolRemoving() == False
    
    chain.revert()


def test_cancelRemove(contract_oracle, contract_glp):
    
    chain.snapshot()
    
    with_requestRemovePool(contract_oracle, contract_glp)
    
    with reverts():
        contract_oracle.cancelRemove({"from": accounts[0]})
        
    contract_oracle.cancelRemove({"from": contract_glp.address})
    
    assert contract_oracle.isPool(contract_glp.address) == True
    assert contract_oracle.isRemovingPool(contract_glp.address) == False
    assert contract_oracle.isAnyPoolRemoving() == False
    
    chain.revert()



def test_requestMigrateMinter(contract_oracle, contract_scminter):
    
    chain.snapshot()
    
    new_minter = accounts[6]
    with_setSCMinter(contract_oracle, contract_scminter)
    
    with reverts():
        contract_oracle.requestMigrateMinter(new_minter, {"from": accounts[0]})
    
        
    contract_oracle.requestAddressChange(contract_scminter.address, new_minter, 
                                          {"from": accounts[0]})
    
    with reverts():
        contract_oracle.requestMigrateMinter(new_minter, {"from": accounts[0]})
        
    chain.sleep(3600*24*8)
    chain.mine()
    
    contract_oracle.requestMigrateMinter(new_minter, {"from": contract_scminter.address})
    
    assert contract_oracle.isMigratingMinter() == True
    assert contract_oracle.newMinter() == new_minter
    
    chain.revert()


def test_setMinterMigrationDone(contract_oracle, contract_scminter):
    
    chain.snapshot()
    
    new_minter = accounts[6]
    with_setSCMinter(contract_oracle, contract_scminter)
    
    with reverts():
        contract_oracle.setMinterMigrationDone({"from": contract_scminter.address})
        
    with_requestMigrateMinter(contract_oracle, contract_scminter, new_minter)
    
    
    with reverts():
        contract_oracle.setMinterMigrationDone({"from": accounts[0]})

    
    contract_oracle.setMinterMigrationDone({"from": contract_scminter.address})
    
    assert abs(contract_oracle.ageSCMinter() - chain.time()) < 2
    assert contract_oracle.scMinter() == new_minter
    assert contract_oracle.isMigratingMinter() == False
    
    chain.revert()


def test_cancelMinterMigration(contract_oracle, contract_scminter):
    
    chain.snapshot()
    
    new_minter = accounts[6]
    with_setSCMinter(contract_oracle, contract_scminter)
    with_requestMigrateMinter(contract_oracle, contract_scminter, new_minter)
    
    with reverts():
        contract_oracle.cancelMinterMigration({"from": accounts[0]})
        
    contract_oracle.cancelMinterMigration({"from": contract_scminter.address})
        
    assert contract_oracle.isMigratingMinter() == False
    assert contract_oracle.scMinter() == contract_scminter.address
    assert contract_oracle.newMinter() == ZERO_ADDRESS
    
    chain.revert()





def test_prepare_pools(contract_glp, contract_glp2, contract_token, contract_token2, initialize):
    
    assert contract_glp.isInitialized()
    assert contract_glp2.isInitialized()
    
    with_many_prev_mints(contract_glp, contract_token, None)
    with_many_prev_mints(contract_glp2, contract_token2, None)



def test_getTotalCollatValue(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.getCollateralValue()
    value2 = contract_glp2.getCollateralValue()
    
    expected_value = contract_oracle.getTotalCollatValue()
    
    assert expected_value == value1 + value2


def test_getPoolCollatWeight(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.getCollateralValue()
    value2 = contract_glp2.getCollateralValue()
    weight1 = (1e18*value1 / (value1+value2))
    weight2 = (1e18*value2 / (value1+value2))
    
    expected_weight1 = contract_oracle.getPoolCollatWeight(contract_glp.address)
    expected_weight2 = contract_oracle.getPoolCollatWeight(contract_glp2.address)
    
    assert abs(weight1 + weight2 - int(1e18)) < 2
    assert abs(expected_weight1 + expected_weight2 - int(1e18)) < 2
    assert abs(expected_weight1 - weight1) < 10
    assert abs(expected_weight2 - weight2) < 10



def test_getSafePrice(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.getCollateralValue()
    value2 = contract_glp2.getCollateralValue()
    weight1 = int(1e18*value1 / (value1 + value2))
    weight2 = int(1e18*value2 / (value1 + value2))
    mean_price1 = contract_glp.meanPrice()
    mean_price2 = contract_glp2.meanPrice()
    
    expected_price = int((weight1*mean_price1 + weight2*mean_price2) / 1e18)
    
    price = contract_oracle.getSafePrice()
    
    assert abs(price - expected_price) < 10


def test_getLastPrice(contract_oracle, contract_glp, contract_glp2):
    
    mean_price1 = contract_glp.lastPrice()
    mean_price2 = contract_glp2.lastPrice()
    
    expected_price = int((mean_price1 + mean_price2) / 2)
    
    price = contract_oracle.getLastPrice()
    
    assert abs(price - expected_price) < 10


def test_getMeanVolume(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.meanVolume()
    value2 = contract_glp2.meanVolume()
    expected_value = (value1 + value2) / 2
    
    volume = contract_oracle.getMeanVolume()
    
    assert abs(expected_value - volume) < 2
    
    


def test_getLastVolume(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.lastVolume()
    value2 = contract_glp2.lastVolume()
    expected_value = (value1 + value2) / 2
    
    volume = contract_oracle.getLastVolume()
    
    assert abs(expected_value - volume) < 2


def test_getTotalMintedGEX(contract_oracle, contract_glp, contract_glp2):
    
    value1 = contract_glp.mintedGEX()
    value2 = contract_glp2.mintedGEX()
    expected_value = value1 + value2
    
    value = contract_oracle.getTotalMintedGEX()
    
    assert expected_value == value


def test_getLockedAmountGEX(contract_oracle, contract_glp, contract_scminter):
    
    with reverts():
        contract_oracle.getLockedAmountGEX({"from": accounts[1]})
        
    with reverts():
        contract_oracle.getLockedAmountGEX({"from": accounts[0]})
        
    with reverts():
        contract_oracle.getLockedAmountGEX({"from": contract_glp.address})
        
    
    with_setSCMinter(contract_oracle, contract_scminter)
    
    expected_value1 = contract_scminter.getBalanceGEX({"from": accounts[0]})
    expected_value2 = contract_scminter.getBalanceGEX({"from": contract_oracle.address})
    
    value1 = contract_oracle.getLockedAmountGEX({"from": accounts[0]})
    value2 = contract_oracle.getLockedAmountGEX({"from": contract_glp.address})
    
    assert value1 == value2
    assert expected_value1 == expected_value2
    assert expected_value1 == value1
    
    
    


def test_getHighestGEXPool(contract_oracle, contract_glp, contract_glp2):
    
    pools = [contract_glp.address, contract_glp2.address]
    value1 = contract_glp.mintedGEX()
    value2 = contract_glp2.mintedGEX()
    expected_value = pools[np.argmax([value1, value2])]
    
    value = contract_oracle.getHighestGEXPool()
    
    assert expected_value == value
    
    
    

"""
CONTEXT FUNCTIONS
"""
# chain revert should be used if this approach is used for test isolation


def with_addPool(contract_oracle, new_pool):
    
    contract_oracle.requestAddAddress(new_pool, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_oracle.addPool(new_pool, {"from": accounts[0]})
    
  
def with_requestMigratePool(contract_oracle, contract_glp, new_pool):
    
    with_addPool(contract_oracle, new_pool)
    contract_oracle.requestAddressChange(contract_glp.address, new_pool, 
                                         {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()    
    contract_oracle.requestMigratePool(new_pool, {"from": contract_glp.address})
    

def with_requestRemovePool(contract_oracle, contract_glp):
    
    contract_oracle.requestRemoveAddress(contract_glp.address, {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()
    contract_oracle.requestRemovePool({"from": contract_glp.address})
    

def with_requestMigrateMinter(contract_oracle, contract_scminter, new_minter):
    
    contract_oracle.requestAddressChange(contract_scminter.address, new_minter, 
                                         {"from": accounts[0]})
    chain.sleep(3600*24*8)
    chain.mine()    
    contract_oracle.requestMigrateMinter(new_minter, {"from": contract_scminter.address})