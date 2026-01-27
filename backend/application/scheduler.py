"""
Scheduler Service - Background jobs for price tracking
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from infrastructure.persistence.database import SessionLocal
from domain.entities import Product
from infrastructure.clients.scraper import scrape_current_price
from application.product_service import ProductService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceScheduler:
    """Scheduler for automated price tracking"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        """Start the scheduler"""
        if self._is_running:
            return
        
        # Schedule daily price update at 6:00 AM
        self.scheduler.add_job(
            self.update_all_prices,
            CronTrigger(hour=6, minute=0),
            id='daily_price_update',
            name='Daily Price Update',
            replace_existing=True
        )
        
        # Also run every 6 hours for more frequent updates (optional)
        self.scheduler.add_job(
            self.update_all_prices,
            CronTrigger(hour='*/6'),
            id='periodic_price_update',
            name='Periodic Price Update (every 6 hours)',
            replace_existing=True
        )
        
        self.scheduler.start()
        self._is_running = True
        logger.info("✅ Price scheduler started - updates at 6:00 AM and every 6 hours")
    
    def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler stopped")
    
    async def update_all_prices(self):
        """Update prices for all tracked products"""
        logger.info(f"🔄 Starting price update job at {datetime.now()}")
        
        db: Session = SessionLocal()
        updated_count = 0
        error_count = 0
        
        try:
            # Get all products
            products = db.query(Product).all()
            total = len(products)
            logger.info(f"Found {total} products to update")
            
            for i, product in enumerate(products):
                try:
                    # Add delay between requests to be respectful
                    if i > 0:
                        await asyncio.sleep(2)  # 2 second delay between requests
                    
                    # Scrape current price
                    price_data = await scrape_current_price(product.url)
                    
                    if price_data and price_data.get("price"):
                        # Use ProductService to ensure daily unique log
                        ProductService.add_price_log(
                            db, 
                            product.id, 
                            price_data["price"], 
                            price_data.get("discount_rate")
                        )
                        logger.info(f"  [{i+1}/{total}] Processed {product.title}: {price_data['price']}원")
                        updated_count += 1
                    else:
                        logger.warning(f"  [{i+1}/{total}] No price data for {product.title}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"  [{i+1}/{total}] Error updating {product.title}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Price update job failed: {e}")
        finally:
            db.close()
        
        logger.info(f"✅ Price update complete: {updated_count} updated, {error_count} errors")
    
    async def update_single_product(self, product_id: int) -> Optional[dict]:
        """Update price for a single product"""
        db: Session = SessionLocal()
        
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            price_data = await scrape_current_price(product.url)
            
            if price_data and price_data.get("price"):
                # Use ProductService to ensure daily unique log
                ProductService.add_price_log(
                    db, 
                    product.id, 
                    price_data["price"], 
                    price_data.get("discount_rate")
                )
                
                return {
                    "product_id": product_id,
                    "price": price_data["price"],
                    "discount_rate": price_data.get("discount_rate")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return None
        finally:
            db.close()


# Global scheduler instance
price_scheduler = PriceScheduler()
