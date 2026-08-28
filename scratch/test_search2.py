import asyncio
import os
from dotenv import load_dotenv

# Load the user's .env which contains the Agent credentials
load_dotenv(".env")

from otrs_mcp.config import OTRSConfig
from otrs_mcp.client import OTRSClient

async def run_tests():
    config = OTRSConfig()
    print("Using username:", config.username)
    client = OTRSClient(config)
    
    try:
        # Test 1: By Title
        print("Test 1: Search by Title=*BEONUP*")
        res1 = await client.search_tickets(title="*BEONUP*", limit=5)
        print("Result 1:", res1)
        
        # Test 2: By CustomerID exact
        print("\nTest 2: Search by CustomerID=Beonup")
        res2 = await client.search_tickets(customer_id="Beonup", limit=5)
        print("Result 2:", res2)
        
        # Test 3: By CustomerID wildcard
        print("\nTest 3: Search by CustomerID=*Beonup*")
        res3 = await client.search_tickets(customer_id="*Beonup*", limit=5)
        print("Result 3:", res3)
        
    except Exception as e:
        print("Error:", e)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
