// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20 is ERC20 {

    uint8 private _decimals;

    constructor(
        uint256 numTokensMinted, 
        string memory name, 
        string memory symbol,
        uint8 decimals_
    ) 
        ERC20(name, symbol)
    {
        _decimals = decimals_;
        _mint(msg.sender, numTokensMinted * 10**_decimals);
    }

    function decimals() public view override returns(uint8) {
        return _decimals;
    }
}
