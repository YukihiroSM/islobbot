#!/usr/bin/env python3
"""
Script to send statistics image to a user based on their chat_id.
This captures the statistics web page as an image and sends it via Telegram.
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("send_statistics_image")

# Add the parent directory to sys.path to import modules from the main project
sys.path.append(str(Path(__file__).parent))

from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN
from capture_statistics_image import capture_statistics_image


async def send_statistics_image(bot, chat_id, period=None, start_date=None, end_date=None, caption=None):
    """
    Generate statistics image for a user and send it via Telegram
    
    Parameters:
    - bot: Telegram bot instance
    - chat_id: User's chat ID
    - period: Predefined period ("weekly", "monthly") - only used if start_date and end_date are None
    - start_date: Start date (string in format YYYY-MM-DD)
    - end_date: End date (string in format YYYY-MM-DD)
    - caption: Optional caption for the image
    
    Returns:
    - True if successful, False otherwise
    """
    try:
        # Generate the statistics image
        image_path = capture_statistics_image(chat_id, period=period, start_date=start_date, end_date=end_date)
        
        if not image_path:
            error_message = "Failed to generate statistics image"
            logger.error(error_message)
            await bot.send_message(chat_id=chat_id, text=error_message)
            return False
        
        # Determine period text for caption if not provided
        if not caption:
            if period == "weekly":
                caption = "Your weekly statistics"
            elif period == "monthly":
                caption = "Your monthly statistics"
            elif start_date and end_date:
                caption = f"Your statistics from {start_date} to {end_date}"
            else:
                caption = "Your statistics"
        
        # Send the image
        with open(image_path, 'rb') as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
        
        # Clean up the temporary file
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {image_path}: {str(e)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error sending statistics image: {str(e)}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error generating your statistics. Please try again later."
        )
        return False


async def main():
    """Parse command line arguments and send statistics image"""
    parser = argparse.ArgumentParser(description='Send statistics image to a user')
    parser.add_argument('--chat_id', type=int, required=True, help='User chat ID')
    parser.add_argument('--period', type=str, choices=['weekly', 'monthly'], help='Statistics period')
    parser.add_argument('--start_date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--caption', type=str, help='Optional caption for the image')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.period is None and (args.start_date is None or args.end_date is None):
        print("Either --period or both --start_date and --end_date must be provided")
        return 1
    
    # Initialize the bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Send the statistics image
    success = await send_statistics_image(
        app.bot,
        args.chat_id,
        period=args.period,
        start_date=args.start_date,
        end_date=args.end_date,
        caption=args.caption
    )
    
    if success:
        print(f"Statistics image sent to user {args.chat_id}")
        return 0
    else:
        print(f"Failed to send statistics image to user {args.chat_id}")
        return 1


if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
