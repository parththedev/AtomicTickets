import os
import redis.asyncio as redis
from src.core.config import settings

class RedisManager:
    def __init__(self):
        self.redis_client: redis.Redis | None = None
        self.buy_ticket_script = None

    async def connect(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        print("✅ Redis Connection Established")
        await self.load_lua_scripts()
 
    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
            print("🛑 Redis Connection Closed")

    async def load_lua_scripts(self):
        script_path = os.path.join("src", "redis", "buy_ticket.lua")
        
        try:
            with open(script_path, "r") as f:
                lua_content = f.read()
            self.buy_ticket_script = self.redis_client.register_script(lua_content)
            print("📜 Lua Script Loaded & Registered")
        except FileNotFoundError:
            print(f"❌ Error: Lua script not found at {script_path}")
            raise

# Create a Global Instance
redis_manager = RedisManager()

# Dependency for FastAPI to get the active client
async def get_redis_client():
    return redis_manager.redis_client