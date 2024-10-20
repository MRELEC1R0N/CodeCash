from pymongo import MongoClient
from datetime import datetime,timedelta
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))

db_login = client.login
users_collection = db_login.users

db_bank = client.bank
bank_collection = db_bank.assets
bank_assets_record = bank_collection.find_one({'_id': 'bank_assets'})
bank_assets = int(bank_assets_record.get('total_assets', 0))