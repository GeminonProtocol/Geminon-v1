# -*- coding: utf-8 -*-
"""
Created on Mon Aug  8 04:29:02 2022

@author: Geminon
"""

# from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from brownie import accounts, reverts, convert
from brownie import GEX
from brownie.network.state import Chain
from brownie.test import given, strategy
from pytest import fixture

chain = Chain()

ZERO_ADDRESS = convert.to_address('0x' + '0'*40)


GEX_MINT_LIMIT = 5000000 * int(1e18)


@fixture(scope='module')
def contract_gex():
    
    return GEX.deploy({"from": accounts[0]})



def test_constructor(contract_gex):
    
    assert contract_gex.name() == 'Geminon'
    assert contract_gex.symbol() == 'GEX'
    assert contract_gex.isInitialized() == False
    assert contract_gex.supplyLimitMint() == GEX_MINT_LIMIT
    
    
    
def test_initialize(contract_gex):
    
    with reverts(): contract_gex.initialize([ZERO_ADDRESS], {"from": accounts[0]})
    with reverts(): contract_gex.initialize([accounts[0]], {"from": accounts[0]})
    
    contract_gex.initialize([accounts[1]], {"from": accounts[0]})
    
    assert contract_gex.minters(accounts[1]) == True
    assert contract_gex.isInitialized() == True
    
    with reverts(): contract_gex.initialize([accounts[2]], {"from": accounts[0]})
    
    
def test_requestAddAddress(contract_gex):
    
    with reverts(): 
        contract_gex.requestAddAddress(ZERO_ADDRESS, {"from": accounts[0]})
        
    with reverts():
        contract_gex.requestAddAddress(accounts[2], {"from": accounts[1]})
    
    
    contract_gex.requestAddAddress(accounts[2], {"from": accounts[0]})
    
    assert contract_gex.changeRequests(ZERO_ADDRESS)[0] == True
    assert abs(contract_gex.changeRequests(ZERO_ADDRESS)[1] - chain.time()) <= 1
    assert contract_gex.changeRequests(ZERO_ADDRESS)[2] == accounts[2]
    
    
def test_AddMinter(contract_gex):
    
    assert contract_gex.changeRequests(ZERO_ADDRESS)[0] == True
    assert contract_gex.changeRequests(ZERO_ADDRESS)[2] == accounts[2]
    
    with reverts('dev: Time elapsed'): 
        contract_gex.addMinter(accounts[2], {"from": accounts[0]})
    
    chain.sleep(3600*24*7)
    chain.mine()
    
    with reverts('dev: Wrong address'): 
        contract_gex.addMinter(accounts[3], {"from": accounts[0]})
        
    contract_gex.addMinter(accounts[2], {"from": accounts[0]})
    
    assert contract_gex.minters(accounts[2]) == True
    assert contract_gex.changeRequests(ZERO_ADDRESS)[0] == False
    
    with reverts('dev: Not requested'): 
        contract_gex.addMinter(accounts[2], {"from": accounts[0]})
    


def test_requestRemoveAddress(contract_gex):
    
    with reverts(): 
        contract_gex.requestRemoveAddress(ZERO_ADDRESS, {"from": accounts[0]})
        
    with reverts():
        contract_gex.requestRemoveAddress(accounts[2], {"from": accounts[1]})
    
    
    contract_gex.requestRemoveAddress(accounts[2], {"from": accounts[0]})
    
    assert contract_gex.changeRequests(accounts[2])[0] == True
    assert abs(contract_gex.changeRequests(accounts[2])[1] - chain.time()) <= 1
    assert contract_gex.changeRequests(accounts[2])[2] == ZERO_ADDRESS



def test_removeMinter(contract_gex):
    
    assert contract_gex.changeRequests(accounts[2])[0] == True
    assert contract_gex.changeRequests(accounts[2])[2] == ZERO_ADDRESS
    
    contract_gex.removeMinter(accounts[2], {"from": accounts[0]})
    
    assert contract_gex.minters(accounts[2]) == False
    assert contract_gex.changeRequests(accounts[2])[0] == False
    
    with reverts('dev: Not requested'): 
        contract_gex.removeMinter(accounts[2], {"from": accounts[0]})



def test_mint(contract_gex):
    
    # data = []
    
    contract_gex.mint(accounts[0], 1000*1e18, {"from": accounts[1]})
    
    with reverts('dev: Max mint rate'):
        contract_gex.mint(accounts[0], GEX_MINT_LIMIT, {"from": accounts[1]})
        
    with reverts('dev: Only minter'):
        contract_gex.mint(accounts[1], 1, {"from": accounts[2]})
    
    
    amount = 30000 * int(1e18)
    for i in range(100):
        chain.sleep(3600)
        chain.mine()
        contract_gex.mint(accounts[0], amount, {"from": accounts[1]})
    #     data.append((contract_gex._timestampLastMint(), 
    #                  amount / int(1e18), 
    #                  contract_gex._meanMintRatio() / int(1e18)))
        
    # pd.DataFrame(data, columns=['timestamp', 'amount', 'meanMintRatio'])\
    #     .to_csv('d:/Proyectos/Geminon/python/data/test_gex_mint.csv', index=False)
    
    


def test_burn(contract_gex):
    
    contract_gex.burn(accounts[0], 1000*1e18, {"from": accounts[1]})
    
    for i in range(100):
        contract_gex.burn(accounts[0], 30000*1e18, {"from": accounts[1]})
        
        
        
def test_mint_burn_alt(contract_gex):
    
    # data = []
    chain.sleep(3600*25)
    chain.mine()
    
    amount = GEX_MINT_LIMIT /2
    for i in range(100):
        contract_gex.mint(accounts[0], amount, {"from": accounts[1]})
        chain.sleep(60)
        chain.mine()
        # data.append((contract_gex._timestampLastMint(), 
        #              amount / int(1e18), 
        #              contract_gex._meanMintRatio() / int(1e18)))
        contract_gex.burn(accounts[0], amount, {"from": accounts[1]})
        chain.sleep(60)
        chain.mine()
        # data.append((contract_gex._timestampLastMint(), 
        #               -amount / int(1e18), 
        #               contract_gex._meanMintRatio() / int(1e18)))
        
    # pd.DataFrame(data, columns=['timestamp', 'amount', 'meanMintRatio'])\
    #     .to_csv('d:/Proyectos/Geminon/python/data/test_gex_mint_burn_alt.csv', index=False)
        
    
    
def test_mint_burn_rand(contract_gex):
    
    # data = []
    chain.sleep(3600*25)
    chain.mine()
    
    for i in range(100):
        amount = np.random.randint(-100000, 100000) * int(1e18)
        
        if amount > 0:
            contract_gex.mint(accounts[0], amount, {"from": accounts[1]})
        else:
            balance = contract_gex.balanceOf(accounts[0])
            if abs(amount) > balance:
                amount = balance
            contract_gex.burn(accounts[0], abs(amount), {"from": accounts[1]})
        
        # data.append((contract_gex._timestampLastMint(), 
        #              amount / int(1e18), 
        #              contract_gex._meanMintRatio() / int(1e18)))
        
        chain.sleep(np.random.randint(1, 10000))
        chain.mine()
        
    # pd.DataFrame(data, columns=['timestamp', 'amount', 'meanMintRatio'])\
    #     .to_csv('d:/Proyectos/Geminon/python/data/test_gex_mint_burn_rand.csv', index=False)
    





"""
PRIVATE FUNCTIONS TESTS
"""

# # Las matemáticas de la función se han testeado a fondo en python
# @given(amount = strategy('int256', 
#                           min_value = -int(1e12) * int(1e18), 
#                           max_value = int(1e12) * int(1e18)))
# def test_meanDailyAmount(contract_gex, amount):
    
#     contract_gex._meanDailyAmount(amount, {"from": accounts[0]})


