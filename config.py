import os

# Telegram Bot - Get from @BotFather https://t.me/botfather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# OpenAI API Key - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Garmin Connect credentials
# The bot will log in and store tokens locally (~/.garminconnect)
# Tokens are valid for one year
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL", "")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD", "")

# PayPal credentials - Get from https://developer.paypal.com/
# For payouts, you need a PayPal Business account
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_RECIPIENT_EMAIL = os.getenv("PAYPAL_RECIPIENT_EMAIL", "")

# Bot settings
CONVERSATION_HISTORY_LIMIT = 10
PENALTY_AMOUNT = 50  # Amount in AUD for missed goals

# OpenAI model to use (gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Database path
DB_PATH = os.getenv("DB_PATH", "data/coach.db")

# Server configuration (for deployment)
SERVER_HOSTNAME = os.getenv("SERVER_HOSTNAME", "jocko.ai")
SERVER_IP = os.getenv("SERVER_IP", "203.57.51.49")
SERVER_USER = os.getenv("SERVER_USER", "root")
SERVER_PASSWORD = os.getenv("SERVER_PASSWORD", "")