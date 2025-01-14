# Morph L2 Transaction Monitor

A monitoring tool for tracking transactions on the Morph L2 network, specifically focusing on ETH/MPH related operations and identifying abnormal transactions.

## Features

- Continuous monitoring of address transactions
- Detection of ETH/MPH related transactions
- Identification of abnormal transactions (non-ETH/MPH)
- REST API for querying monitoring statistics
- Persistent storage of transaction data
- Configurable monitoring interval

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd web3monitor
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start Monitoring

To start monitoring an address:

```bash
python morph_monitor.py --address 0xaE1c7FB1EA42d3DF0d8b683Fc4F4b7CA5f23FCf0 --monitor
```

### Command Line Arguments

- `--address`: The address to monitor (required)
- `--base-token`: Base token symbol (default: ETH)
- `--quote-token`: Quote token symbol (default: MPH)
- `--interval`: Monitoring interval in seconds (default: 300)
- `--monitor`: Enable continuous monitoring mode

### API Endpoints

The monitoring service exposes a REST API endpoint at `http://localhost:5000`:

#### GET /stats

`curl http://localhost:5000/stats`

Returns monitoring statistics including:
- Monitor information (start time, duration)
- Token information (addresses)
- Transaction statistics
- Recent abnormal transactions

Example response:
```json
{
    "monitor_info": {
        "start_time": "2025-01-13T00:24:46+00:00",
        "current_time": "2025-01-13T00:25:46+00:00",
        "monitoring_duration": "0:01:00",
        "monitored_address": "0xaE1c7FB1EA42d3DF0d8b683Fc4F4b7CA5f23FCf0"
    },
    "token_info": {
        "base_token": {
            "symbol": "ETH",
            "address": "0x5300000000000000000000000000000000000011"
        },
        "quote_token": {
            "symbol": "MPH",
            "address": "0x579C032A137D796f29b14AdEcb58C2E56B14e367"
        }
    },
    "statistics": {
        "total_transactions": 42,
        "abnormal_transactions": 3,
        "abnormal_percentage": "7.14%"
    },
    "recent_abnormal_transactions": [...]
}
```

## Data Storage

The monitor stores all transaction data in `transaction_data.json`, which includes:
- Configuration data
- Monitoring statistics
- Recent abnormal transactions (last 100)

## Logging

All monitoring activities are logged to:
- Console output
- `morph_transactions.log` file

## Known DEX Contracts

The monitor recognizes the following DEX contracts:
- UniversalRouter: `0xb789922D715475F419b7CB47B6155bF7a2ACECD6`

## Token Addresses

Default token addresses on Morph L2:
- ETH (WETH): `0x5300000000000000000000000000000000000011`
- MPH: `0x579C032A137D796f29b14AdEcb58C2E56B14e367`
