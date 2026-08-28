import asyncio
from otrs_mcp.config import OTRSConfig
from otrs_mcp.client import OTRSClient

async def test_search():
    config = OTRSConfig()
    client = OTRSClient(config)
    try:
        result = await client.search_tickets(title="*BEONUP*", limit=20)
        print("Search Result (Title=*BEONUP*):", result)
        
        # Test without title
        result2 = await client.search_tickets(limit=10)
        print("Search Result (No Title):", result2)
        
        # Test with customer user explicitly set
        result3 = await client.search_tickets(customer_user=config.username, limit=10)
        print("Search Result (CustomerUser set):", result3)
    except Exception as e:
        print("Error:", e)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_search())
