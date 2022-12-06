// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../utils/DateTimeMath.sol";

contract MockChainlinkAPIConsumer is DateTimeMath {

    uint256 public latestValue;
    uint256 public latestTimestamp;

    mapping(uint16 => mapping(uint8 => uint256)) public CPIObservations;

    // @dev value decimals must match with the API contract, usually 1e18
    constructor(uint256 value) {
        setLastValue(value);
    }

    function getLastValue() external view returns(uint256) {
        return latestValue;
    }

    function getLastObservationTimestamp() external view returns(uint256) {
        return latestTimestamp;
    }

    function getValue(uint16 year, uint8 month) external view returns(uint256) {
        return CPIObservations[year][month];
    }

    function setValues(uint16[] memory year, uint8[] memory months, uint256[] memory values) external {
        require(year.length == months.length);
        require(months.length == values.length);

        for(uint16 i=0; i<values.length; i++) {
            setValue(year[i], months[i], values[i]);
        }
        setLastObservation(year[values.length-1], months[values.length-1], values[values.length-1]);
    }

    function setLastValue(uint256 value) public {
        latestValue = value;
    }

    function setLastTimestamp(uint256 timestamp) public {
        latestTimestamp = timestamp;
    }

    function setLastObservation(uint16 year, uint8 month, uint256 value) public {
        CPIObservations[year][month] = value;
        setLastValue(value);
        setLastTimestamp(timestampFromDate(year, month, 1));
    }

    function setValue(uint16 year, uint8 month, uint256 value) public {
        CPIObservations[year][month] = value;
    }
}
