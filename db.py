import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)

db = client["application-processing-system"]

users = db["users"]
requests_db = db["requests"]
comments = db["comments"]
messages = db["messages"]