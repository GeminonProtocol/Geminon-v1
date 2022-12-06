// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20Indexed is ERC20 {

    uint256 pegValue;

    constructor(string memory name, string memory symbol) ERC20(name, symbol) {
        pegValue = 105*1e18/100;
    }

    function updateTarget() external {}

    function getOrUpdatePegValue() external returns(uint256) {}

    function getPegValue() external view returns(uint256) {
        return pegValue;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        _burn(from, amount);
    }

    function maxAmountMintable() external view returns(uint256) {}

    function addMinter(address newMinter) external {}

    function removeMinter(address minter) external {}
}
