// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./IChainlinkFredObservation.sol";
import "../utils/DateTimeMath.sol";
import "../utils/StringUtils.sol";


/**
* @title ChainlinkFredObservation
* @author Geminon Protocol
* @notice This contract makes an API call through a Chainlink oracle and
* retrieves the value of the requested CPI observation.
*/
contract ChainlinkFredObservation is 
    IChainlinkFredObservation, 
    ChainlinkClient, 
    Ownable, 
    DateTimeMath, 
    StringUtils 
{
    using Chainlink for Chainlink.Request;

    LinkTokenInterface public link;

    address public oracle;
    bytes32 public jobId;
    uint256 public fee;
    int256 public requestDecimals = 1e18;

    /// @dev this is needed for cancelRequest()
    bytes32 private lastRequestId;
    uint256 private expiration;
    address private lastRequester;

    struct CPIobservation {
        uint16 year;
        uint8 month;
        uint256 observation;
    }
    CPIobservation private lastObservation;
    string public lastResponse;
    
    address[] private linkBalanceKeys;
    mapping(address => uint256) public linkTokenBalance;  // TODO private
    mapping(address => bool) public validDataConsumers;  // TODO private

    /// @dev Emitted when external user pays fee for Chainlink request
    event FeePaid(address from, uint256 amount);

    /// @dev Emitted when owner withdraws all Link from the contract
    event LinkWithdrawn(uint256 amount);

    /// @dev Emitted when the request is sent to the oracle
    event RequestSent(string url);

    /// @dev Emitted when oracle fullfills the job
    event DataFullfilled(string data1, string data2);

    /// @dev Emitted when a request is canceled
    event RequestCanceled(bytes32 requestId);

    
    /**
     * https://market.link
     * https://docs.chain.link/docs/decentralized-oracles-ethereum-mainnet/
     * Link addresses: https://docs.chain.link/docs/link-token-contracts/
     *
     * Network: Rinkeby
     * Description: Rinkeby_Test_Node / Get > Uint256
     * Oracle: 0xF59646024204a733E1E4f66B303c9eF4f68324cC
     * Job ID: 6a92925dbb0e48e9b375b1deac4751c0
     * Fee: 0.1 LINK
     * LINK Rinkeby: 0x01BE23585060835E02B77ef475b0Cc51aA1e0709
     *
     * Network: Kovan
     * Description: Chainlink Devrel / Get > uint256
     * Oracle: 0x74EcC8Bdeb76F2C6760eD2dc8A46ca5e581fA656
     * Job ID: ca98366cc7314957b8c012c72f05aeeb
     *
     * Description: Chainlink Devrel / Get > String
     * Oracle: 0x74EcC8Bdeb76F2C6760eD2dc8A46ca5e581fA656
     * Job ID: 7d80a6386ef543a3abb52817f6707e3b
     *
     * Fee: 0.1 LINK
     * LINK Kovan: 0xa36085F69e2889c224210F603D836748e7dC0088
     */
    constructor(address oracle_, bytes32 jobId_, uint256 fee_, address link_) {
        if (link_ == address(0)) setPublicChainlinkToken();
        else setChainlinkToken(link_);
        
        link = LinkTokenInterface(chainlinkTokenAddress());
        oracle = oracle_;
        jobId = jobId_;
        fee = fee_;

        setDataConsumer(msg.sender);
    }

    /// @dev Allows to change oracle params after deployment.
    function setOracleParams(address oracle_, bytes32 jobId_, uint256 fee_) external onlyOwner {
        oracle = oracle_;
        jobId = jobId_;
        fee = fee_;
    }

    /// @notice This funtion is used to deposit Link for the oracle fees on the contract. 
    /// Never send funds directly to the contract.
    function depositLink(uint256 amount) external {
        require(amount >= fee, "Insufficient amount");
        linkTokenBalance[msg.sender] += amount;
        linkBalanceKeys.push(msg.sender);
        require(link.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        emit FeePaid(msg.sender, amount);
    }

    // TODO Reset linkTokenBalance for all addresses to 0.
    /// @notice Allows owner withdraw all Link from the contract, in case someone sends directly
    /// the tokens without using the depositLink() function or if there are unspendable balances.
    function withdrawLink() external onlyOwner {
        for (uint16 i=0; i<linkBalanceKeys.length; i++) {
            linkTokenBalance[linkBalanceKeys[i]] = 0;
        }
        uint256 amount = link.balanceOf(address(this));
        require(link.transfer(msg.sender, amount), "Unable to transfer");
        emit LinkWithdrawn(amount);
    }

    /// @dev Give permission to an address to consume the data of this contract
    function setDataConsumer(address newConsumer) public onlyOwner {
        validDataConsumers[newConsumer] = true;
    }
    
    /// @dev Revoques permission to consume the data of this contract 
    function removeDataConsumer(address consumer) public onlyOwner {
        validDataConsumers[consumer] = false;
    }

    /// @notice Create a Chainlink request to retrieve API response, find the target
    /// data, then multiply by 1e18 (to remove decimal places from data).
    function makeMultipleRequest(string memory requestURL) public {
        require(_linkFeeAvailable(msg.sender), "Not enough LINK for request fee");

        linkTokenBalance[msg.sender] -= fee;
        lastRequester = msg.sender;

        Chainlink.Request memory request = buildChainlinkRequest(jobId, address(this), this.fulfill.selector);
        request.add("get", requestURL);
        request.add("path", "observations.0.value");
        request.add("path", "observations.0.date");
        
        lastRequestId = sendChainlinkRequestTo(oracle, request, fee);

        expiration = block.timestamp + 5 minutes;

        emit RequestSent(requestURL);
    }
    

    /// @notice Callback executed by the oracle on the data retrieved from the API. It process and stores the data.
    function fulfill(bytes32 requestId, string memory value, string memory date) 
        public 
        recordChainlinkFulfillment(requestId) 
    {    
        (uint16 year, uint8 month) = stringDateToYearmonth(date);
        uint256 observation = stringFloatToUint(value, '.', 18);
        
        lastObservation = CPIobservation(year, month, observation);
        
        emit DataFullfilled(value, date);
    }


    /// @notice Cancels the last request if it hasn't ben fullfilled before expiration time (5 minutes by default)
    function cancelRequest() public onlyOwner {
        cancelChainlinkRequest(lastRequestId, fee, this.fulfill.selector, expiration);
        emit RequestCanceled(lastRequestId);
    }

    /// @dev Get last retrieved data. Only approved addresses, owner or the address that paid last 
    /// fee can access to the value.
    function getLastObservation() public view returns(uint16 year, uint8 month, uint256 observation) {
        require(msg.sender == owner() || validDataConsumers[msg.sender] || lastRequester == msg.sender);
        return (lastObservation.year, lastObservation.month, lastObservation.observation);
    }

    /// @dev Checks if an address has paid enough Link for the gas to make the oracle request
    function hasPaidFee(address requester) public view returns(bool) {
        return _linkFeeAvailable(requester);
    }

    /// @dev Checks if msg.sender has paid enough Link for the gas to make the oracle request
    function _linkFeeAvailable(address sender) private view returns(bool) {
        if ((sender == owner() || validDataConsumers[sender]) && link.balanceOf(address(this)) >= fee) 
            return true;
        if (linkTokenBalance[sender] >= fee) 
            return true;
        return false;
    }

    /// @dev Converts string date to a tuple of year-month
    function stringDateToYearmonth(string memory date) private pure returns(uint16 year, uint8 month) {
        year = uint16(stringToUint(substring(date, 4, 0)));
        month = uint8(stringToUint(substring(date, 2, 5)));
    }
}