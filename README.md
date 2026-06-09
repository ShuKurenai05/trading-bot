#To Run, use this in terminal

cd trading_bot
pip install -r requirements.txt
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# Market order
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit order
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 71000
