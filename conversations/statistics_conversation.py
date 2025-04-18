from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import text_constants
from database import get_db
from utils.commands import cancel
from utils.keyboards import main_menu_keyboard
from models import User
from capture_statistics_image import generate_statistics_image
from enum import Enum, auto
from loguru import logger
import datetime
from config import timezone as tz

class StatisticsConversation(Enum):
    SELECT_PERIOD = auto()


async def start_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the statistics conversation with period selection."""
    keyboard = [
        [text_constants.WEEK_STATISTICS, text_constants.MONTH_STATISTICS],
        [text_constants.BACK_TO_MAIN_MENU]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        text=text_constants.SELECT_STATISTICS_PERIOD,
        reply_markup=reply_markup,
    )
    return StatisticsConversation.SELECT_PERIOD


async def select_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle period selection and generate statistics."""
    logger.info("Statistics period selection triggered")
    user_input = update.message.text
    logger.debug(f"Received user input: {user_input}")
    
    if user_input == text_constants.BACK_TO_MAIN_MENU:
        logger.info("User selected back to main menu")
        await update.message.reply_text(
            text=text_constants.BACK_TO_MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(update.effective_chat.id)
        )
        return ConversationHandler.END
    
    # Determine the selected period
    if "тиждень" in user_input.lower():
        logger.info("User selected weekly statistics")
        period = "weekly"
    elif "місяць" in user_input.lower():
        logger.info("User selected monthly statistics")
        period = "monthly"
    else:
        logger.warning(f"Unexpected input received: {user_input}")
        await update.message.reply_text(
            text=text_constants.SELECT_STATISTICS_PERIOD,
            reply_markup=ReplyKeyboardMarkup(
                [
                    [text_constants.WEEK_STATISTICS, text_constants.MONTH_STATISTICS],
                    [text_constants.BACK_TO_MAIN_MENU]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return StatisticsConversation.SELECT_PERIOD
    
    # Send waiting message
    waiting_message = await update.message.reply_text(
        text="⏳ Чекай пару хвилин, зараз нагенеруємо тобі графіків та аналіз...",
        reply_markup=main_menu_keyboard(update.effective_chat.id)
    )
    
    try:
        logger.info(f"Generating {period} statistics")
        # Get user ID from database
        chat_id = update.effective_chat.id
        with next(get_db()) as db_session:
            user = db_session.query(User).filter(User.chat_id == str(chat_id)).first()
            if not user:
                logger.warning(f"User not found for chat_id: {chat_id}")
                # Delete waiting message if possible
                try:
                    await waiting_message.delete()
                except Exception:
                    pass
                
                await update.message.reply_text(
                    text=text_constants.USER_NOT_FOUND,
                    reply_markup=main_menu_keyboard(chat_id)
                )
                return ConversationHandler.END
            
            user_id = user.id
        
        # Generate statistics image
        start_date = None
        end_date = None

        if period == "weekly":
            end_date = datetime.datetime.now(tz=tz)
            start_date = end_date - datetime.timedelta(days=7)
        elif period == "monthly":
            end_date = datetime.datetime.now(tz=tz)
            start_date = end_date - datetime.timedelta(days=30)

        # Generate image and get AI analysis
        image_path, analysis = generate_statistics_image(
            chat_id=user_id,
            period=period,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if not image_path:
            logger.error("Failed to generate statistics image")
            # Delete waiting message if possible
            try:
                await waiting_message.delete()
            except Exception:
                pass
                
            await update.message.reply_text(
                text=text_constants.STATISTICS_ERROR,
                reply_markup=main_menu_keyboard(chat_id)
            )
            return ConversationHandler.END
            
        logger.debug(f"Statistics image generated at {image_path}")
        
        # Determine the period text for the caption
        period_text = text_constants.LAST_WEEK if period == "weekly" else text_constants.LAST_MONTH
        
        # Send image to user
        with open(image_path, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text_constants.STATISTICS_CAPTION.format(period=period_text)
            )
        
        # Delete waiting message if possible
        try:
            await waiting_message.delete()
        except Exception:
            pass
        
        # Send AI analysis as a separate message if available
        if analysis:
            logger.info("Sending AI analysis")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📊 *Аналіз ваших тренувань*\n\n{analysis}",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(chat_id)
            )
        
        logger.info("Statistics sent successfully")
        
        # Clean up the image file
        try:
            import os
            os.remove(image_path)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
    
    except Exception as e:
        logger.error(f"Failed to generate statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Delete waiting message if possible
        try:
            await waiting_message.delete()
        except Exception:
            pass
            
        await update.message.reply_text(
            text=text_constants.STATISTICS_ERROR,
            reply_markup=main_menu_keyboard(chat_id)
        )
    
    return ConversationHandler.END


# Create the conversation handler
statistics_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("statistics", start_statistics),
        MessageHandler(
            filters.Regex(f"^{text_constants.STATISTICS}$"), 
            start_statistics
        ),
    ],
    states={
        StatisticsConversation.SELECT_PERIOD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_period)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="statistics_conversation",
)
