import requests
import json
from datetime import datetime, timedelta, timezone
import argparse
import logging
import pytz
import time
import threading
from flask import Flask, jsonify
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('morph_transactions.log'),
        logging.StreamHandler()
    ]
)

# Flask app for API
app = Flask(__name__)

class MorphTransactionMonitor:
    # Token addresses on Morph
    TOKEN_ADDRESSES = {
        'ETH': '0x5300000000000000000000000000000000000011',  # WETH
        'MPH': '0x579C032A137D796f29b14AdEcb58C2E56B14e367'  # Morphahaha
    }

    # Known DEX contracts
    DEX_CONTRACTS = {
        'UniversalRouter': '0xb789922D715475F419b7CB47B6155bF7a2ACECD6'.lower(),
        'UniswapV2Router02': '0x81606E6f8aAD6C75c2f383Ea595c2b9f8ce8aE3a'.lower(),
    }

    def __init__(self, address, base_token="ETH", quote_token="MPH"):
        self.address = address.lower()
        self.base_token = base_token
        self.quote_token = quote_token
        self.base_token_address = self.TOKEN_ADDRESSES.get(base_token)
        self.quote_token_address = self.TOKEN_ADDRESSES.get(quote_token)
        self.api_url = f"https://explorer-api.morphl2.io/api/v2/addresses/{address}/transactions"
        self.last_processed_tx = None
        self.data_file = 'transaction_data.json'
        
        # Initialize data file if it doesn't exist
        self.init_data_file()
        
    def init_data_file(self):
        """Initialize data file with basic structure"""
        if not os.path.exists(self.data_file):
            initial_data = {
                'config': {
                    'monitored_address': self.address,
                    'base_token': self.base_token,
                    'quote_token': self.quote_token,
                    'token_addresses': {
                        self.base_token: self.base_token_address,
                        self.quote_token: self.quote_token_address
                    },
                    'dex_contracts': self.DEX_CONTRACTS
                },
                'monitoring': {
                    'start_time': None,
                    'last_processed_tx': None,
                    'total_transactions': 0,
                    'abnormal_transactions': 0
                },
                'abnormal_txs': []
            }
            self.save_data(initial_data)
    
    def load_data(self):
        """Load transaction data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                if data.get('monitoring', {}).get('start_time'):
                    data['monitoring']['start_time'] = datetime.fromisoformat(
                        data['monitoring']['start_time'].replace('Z', '+00:00')
                    )
                return data
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Error loading data file: {e}")
            return None
        
    def save_data(self, data):
        """Save transaction data to JSON file"""
        try:
            # Convert datetime to string if present
            if data.get('monitoring', {}).get('start_time'):
                data['monitoring']['start_time'] = data['monitoring']['start_time'].isoformat()
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
        
    def get_transactions(self):
        try:
            params = {
                "filter": "to | from"
            }
            headers = {
                "accept": "application/json"
            }
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching transactions: {e}")
            return None

    def is_target_pair_transaction(self, tx):
        """
        Check if the transaction is related to ETH/MPH.
        """
        if not tx.get("to"):
            return False

        to_address = tx["to"].get("hash", "").lower()
        
        # Check if it's a DEX trade through any known DEX contract
        if to_address in self.DEX_CONTRACTS.values():
            return True
            
        # Check if it's interaction with ETH or MPH
        if to_address in [self.base_token_address.lower(), self.quote_token_address.lower()]:
            return True
                
        return False

    def analyze_transactions(self):
        """Analyze transactions and provide statistics"""
        transactions = self.get_transactions()
        if not transactions or "items" not in transactions:
            logging.error("Failed to fetch transactions")
            return

        # Load current data
        data = self.load_data()
        if not data:
            # Initialize data if loading failed
            data = {
                'config': {
                    'monitored_address': self.address,
                    'base_token': self.base_token,
                    'quote_token': self.quote_token,
                    'token_addresses': {
                        self.base_token: self.base_token_address,
                        self.quote_token: self.quote_token_address
                    },
                    'dex_contracts': self.DEX_CONTRACTS
                },
                'monitoring': {
                    'start_time': datetime.now(timezone.utc),
                    'last_processed_tx': None,
                    'total_transactions': 0,
                    'abnormal_transactions': 0
                },
                'abnormal_txs': []
            }

        # Initialize start time if not set
        if not data['monitoring']['start_time']:
            data['monitoring']['start_time'] = datetime.now(timezone.utc)

        new_transactions = []
        for tx in transactions["items"]:
            # Stop if we've reached previously processed transaction
            if tx["hash"] == data['monitoring'].get('last_processed_tx'):
                break
            new_transactions.append(tx)

        # Update last processed transaction
        if transactions["items"]:
            data['monitoring']['last_processed_tx'] = transactions["items"][0]["hash"]

        # Process new transactions in chronological order
        for tx in reversed(new_transactions):
            data['monitoring']['total_transactions'] += 1
            
            # Check if transaction is related to ETH/MPH
            if not self.is_target_pair_transaction(tx):
                data['monitoring']['abnormal_transactions'] += 1
                
                # Create abnormal transaction record
                abnormal_tx = {
                    "hash": tx["hash"],
                    "timestamp": tx["timestamp"],
                    "method": tx.get("method", "Unknown"),
                    "to_address": tx.get("to", {}).get("hash", "Unknown"),
                    "to_name": tx.get("to", {}).get("name", "Unknown"),
                    "value": tx.get("value", "0"),
                    "status": tx.get("status", "Unknown"),
                    "gas_used": tx.get("gasUsed", "Unknown"),
                }
                
                # Add new abnormal transaction
                data['abnormal_txs'].append(abnormal_tx)
                # Keep only last 100 abnormal transactions
                data['abnormal_txs'] = data['abnormal_txs'][-100:]
                
                logging.warning(f"Abnormal transaction detected!")
                logging.warning(f"Hash: {tx['hash']}")
                logging.warning(f"To: {tx.get('to', {}).get('name', 'Unknown')} ({tx.get('to', {}).get('hash', 'Unknown')})")
                logging.warning(f"Method: {tx.get('method', 'Unknown')}")
                logging.warning("-" * 50)

        # Save updated data
        self.save_data(data)

    def monitor_continuously(self, interval=300):
        """
        Continuously monitor transactions with specified interval in seconds
        """
        logging.info(f"Starting continuous monitoring for address {self.address}")
        logging.info(f"Watching for non-{self.base_token}/{self.quote_token} transactions")
        logging.info(f"Press Ctrl+C to stop monitoring")
        
        while True:
            try:
                self.analyze_transactions()
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Error during monitoring: {e}")
                time.sleep(interval)

@app.route('/stats')
def get_stats():
    # Load current data from file
    monitor = MorphTransactionMonitor("dummy")  # Create temporary instance to access file
    data = monitor.load_data()
    if not data:
        return jsonify({"error": "No monitoring data available"}), 404

    now = datetime.now(timezone.utc)
    
    # Ensure all required fields exist
    if 'monitoring' not in data:
        data['monitoring'] = {
            'start_time': now,
            'last_processed_tx': None,
            'total_transactions': 0,
            'abnormal_transactions': 0
        }
        monitor.save_data(data)
    
    start_time = data['monitoring']['start_time']
    
    # Calculate monitoring duration
    duration = str(now - start_time) if start_time else "Not started"
    
    # Prepare detailed statistics
    stats = {
        'monitor_info': {
            'start_time': start_time.isoformat() if start_time else None,
            'current_time': now.isoformat(),
            'monitoring_duration': duration,
            'monitored_address': data['config']['monitored_address'],
        },
        'token_info': {
            'base_token': {
                'symbol': data['config']['base_token'],
                'address': data['config']['token_addresses'][data['config']['base_token']]
            },
            'quote_token': {
                'symbol': data['config']['quote_token'],
                'address': data['config']['token_addresses'][data['config']['quote_token']]
            }
        },
        'dex_contracts': data['config']['dex_contracts'],
        'statistics': {
            'total_transactions': data['monitoring']['total_transactions'],
            'abnormal_transactions': data['monitoring']['abnormal_transactions'],
            'abnormal_percentage': f"{(data['monitoring']['abnormal_transactions'] / data['monitoring']['total_transactions'] * 100):.2f}%" if data['monitoring']['total_transactions'] > 0 else "0%"
        },
        'recent_abnormal_transactions': data.get('abnormal_txs', [])[-10:]  # Last 10 abnormal transactions
    }
    return jsonify(stats)

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def main():
    parser = argparse.ArgumentParser(description='Monitor Morph L2 transactions for specific address')
    parser.add_argument('--address', required=True, help='Address to monitor')
    parser.add_argument('--base-token', default='ETH', help='Base token of the pair (default: ETH)')
    parser.add_argument('--quote-token', default='MPH', help='Quote token of the pair (default: MPH)')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--monitor', action='store_true', help='Enable continuous monitoring')
    
    args = parser.parse_args()
    
    monitor = MorphTransactionMonitor(args.address, args.base_token, args.quote_token)
    
    if args.monitor:
        # Start Flask API in a separate thread
        api_thread = threading.Thread(target=run_flask, daemon=True)
        api_thread.start()
        
        # Start monitoring
        monitor.monitor_continuously(args.interval)
    else:
        monitor.analyze_transactions()

if __name__ == "__main__":
    main()
