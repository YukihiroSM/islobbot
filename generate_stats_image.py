#!/usr/bin/env python3
"""
Module for generating statistics images for users.
This can be used as a standalone script or as a Telegram job.
"""

import argparse
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from telegram.ext import CallbackContext

# Import the function from capture_statistics_image.py
from capture_statistics_image import generate_statistics_image
# Import database utilities
from database import get_db
from utils.db_utils import get_all_active_users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_stats_image')

async def generate_statistics_images_job(context: CallbackContext) -> None:
    """
    Telegram job to generate statistics images for all active users.
    
    Args:
        context: The callback context as provided by the application
    """
    logger.info("Starting statistics image generation job")
    
    # Default to last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent / "stats_images"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all active users
    with next(get_db()) as db_session:
        users = get_all_active_users(db_session)
        
        for user in users:
            try:
                # Generate statistics image for each user
                image_path = generate_statistics_image(
                    chat_id=user.chat_id,
                    period='monthly',
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir
                )
                
                logger.info(f"Generated statistics image for user {user.chat_id}: {image_path}")
                
                # Note: We're not sending the image here as requested
                # This will be handled by a separate job
                
            except Exception as e:
                logger.error(f"Error generating statistics image for user {user.chat_id}: {str(e)}")
    
    logger.info("Completed statistics image generation job")


def generate_image_for_user(chat_id: int, period: str = 'monthly', 
                           days_back: int = 30, output_dir: Optional[str] = None) -> str:
    """
    Generate a statistics image for a specific user
    
    Args:
        chat_id: User's chat ID
        period: Period type (daily, weekly, monthly)
        days_back: Number of days to look back from today
        output_dir: Directory to save the output files
        
    Returns:
        str: Path to the generated image
    """
    # Calculate date range
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    logger.info(f"Generating statistics image for user {chat_id} from {start_date} to {end_date}")
    
    # Call the function from capture_statistics_image.py
    image_path = generate_statistics_image(
        chat_id=chat_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir
    )
    
    return image_path


def generate_images_for_users(chat_ids: List[int], period: str = 'monthly',
                             days_back: int = 30, output_dir: Optional[str] = None) -> dict:
    """
    Generate statistics images for multiple users
    
    Args:
        chat_ids: List of user chat IDs
        period: Period type (daily, weekly, monthly)
        days_back: Number of days to look back from today
        output_dir: Directory to save the output files
        
    Returns:
        dict: Dictionary mapping chat_ids to image paths
    """
    results = {}
    
    for chat_id in chat_ids:
        try:
            image_path = generate_image_for_user(
                chat_id=chat_id,
                period=period,
                days_back=days_back,
                output_dir=output_dir
            )
            results[chat_id] = image_path
        except Exception as e:
            logger.error(f"Error generating image for user {chat_id}: {str(e)}")
            results[chat_id] = None
    
    return results


def main():
    """Command line interface for generating statistics images"""
    parser = argparse.ArgumentParser(description='Generate statistics images for users')
    parser.add_argument('--chat_id', type=int, help='User chat ID (if not specified, generates for all users)')
    parser.add_argument('--period', type=str, default='monthly', 
                        choices=['daily', 'weekly', 'monthly'],
                        help='Period type (daily, weekly, monthly)')
    parser.add_argument('--days_back', type=int, default=30, 
                        help='Number of days to look back from today')
    parser.add_argument('--output_dir', type=str, default='./stats_images',
                        help='Directory to save output files')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.chat_id:
        # Generate image for a specific user
        image_path = generate_image_for_user(
            chat_id=args.chat_id,
            period=args.period,
            days_back=args.days_back,
            output_dir=args.output_dir
        )
        
        if image_path:
            logger.info(f"Successfully generated statistics image: {image_path}")
            print(f"Statistics image saved to: {image_path}")
        else:
            logger.error("Failed to generate statistics image")
            print("Failed to generate statistics image")
    else:
        # Generate images for all active users
        with next(get_db()) as db_session:
            users = get_all_active_users(db_session)
            chat_ids = [user.chat_id for user in users]
        
        results = generate_images_for_users(
            chat_ids=chat_ids,
            period=args.period,
            days_back=args.days_back,
            output_dir=args.output_dir
        )
        
        success_count = sum(1 for path in results.values() if path is not None)
        logger.info(f"Generated {success_count} out of {len(results)} statistics images")
        print(f"Generated {success_count} out of {len(results)} statistics images")


if __name__ == "__main__":
    main()
