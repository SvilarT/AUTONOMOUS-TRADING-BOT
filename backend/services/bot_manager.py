import asyncio
import logging
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorClient
import os

from services.bot_engine import BotEngine

logger = logging.getLogger(__name__)

class BotManager:
    """Manages multiple bot instances for different users"""
    
    def __init__(self, db):
        self.db = db
        self.active_bots: Dict[str, asyncio.Task] = {}
        self.bot_engines: Dict[str, BotEngine] = {}
        self.running = False
    
    async def start_manager(self):
        """Start the bot manager - monitors for active bots"""
        self.running = True
        logger.info("Bot Manager started")
        
        while self.running:
            try:
                # Check for active bot configurations
                active_configs = await self.db.bot_configs.find(
                    {"is_active": True},
                    {"_id": 0}
                ).to_list(100)
                
                for config in active_configs:
                    user_id = config['user_id']
                    
                    # Start bot if not already running
                    if user_id not in self.active_bots or self.active_bots[user_id].done():
                        logger.info(f"Starting bot for user {user_id}")
                        await self.start_bot(user_id)
                
                # Check for stopped bots
                for user_id in list(self.active_bots.keys()):
                    config = await self.db.bot_configs.find_one({"user_id": user_id})
                    if not config or not config.get('is_active'):
                        logger.info(f"Stopping bot for user {user_id}")
                        await self.stop_bot(user_id)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Bot manager error: {e}")
                await asyncio.sleep(5)
    
    async def start_bot(self, user_id: str):
        """Start a bot for a specific user"""
        if user_id in self.active_bots and not self.active_bots[user_id].done():
            logger.info(f"Bot already running for user {user_id}")
            return
        
        # Create bot engine
        bot_engine = BotEngine(self.db)
        self.bot_engines[user_id] = bot_engine
        
        # Start bot in background task
        task = asyncio.create_task(bot_engine.start(user_id))
        self.active_bots[user_id] = task
        
        logger.info(f"Bot started for user {user_id}")
    
    async def stop_bot(self, user_id: str):
        """Stop a bot for a specific user"""
        if user_id in self.active_bots:
            # Stop the bot engine
            if user_id in self.bot_engines:
                await self.bot_engines[user_id].stop()
                del self.bot_engines[user_id]
            
            # Cancel the task
            self.active_bots[user_id].cancel()
            try:
                await self.active_bots[user_id]
            except asyncio.CancelledError:
                pass
            
            del self.active_bots[user_id]
            logger.info(f"Bot stopped for user {user_id}")
    
    async def stop_manager(self):
        """Stop the bot manager and all running bots"""
        self.running = False
        
        # Stop all active bots
        for user_id in list(self.active_bots.keys()):
            await self.stop_bot(user_id)
        
        logger.info("Bot Manager stopped")
