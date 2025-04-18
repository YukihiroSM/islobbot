#!/usr/bin/env python3
"""
Script to capture statistics as an image.
"""

import os
import json
from datetime import datetime
import time
import argparse
import decimal
import subprocess

from loguru import logger

from openai import AsyncOpenAI
from statistics_web.generate_web_data import generate_html_from_data, get_statistics_data
from statistics_web.playwright_capture import capture_statistics_image

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

async def capture_html_screenshot(html_file, output_path, window_width=1200, window_height=1600):
    """
    Capture a screenshot of an HTML file using a headless browser
    
    Args:
        html_file (str): Path to the HTML file
        output_path (str): Path to save the screenshot
        window_width (int): Width of the browser window
        window_height (int): Height of the browser window
        
    Returns:
        str: Path to the saved screenshot
    """
    try:
        # Get the absolute path of the HTML file
        abs_path = os.path.abspath(html_file)
        
        # Read the HTML content to extract the data
        with open(abs_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Extract the JSON data from the HTML
        # This is a simple approach - in a real implementation, you might want to use a more robust method
        start_marker = "const sampleData = "
        end_marker = ";"
        
        start_idx = html_content.find(start_marker) + len(start_marker)
        end_idx = html_content.find(end_marker, start_idx)
        
        if start_idx > len(start_marker) and end_idx > start_idx:
            json_str = html_content[start_idx:end_idx].strip()
            try:
                # Parse the JSON data
                stats_data = json.loads(json_str)
                
                # Use our Playwright-based approach to generate the image
                logger.info("Using Playwright to generate statistics image")
                return await capture_statistics_image(stats_data, output_path, template_name="template.html")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data from HTML: {e}")
        else:
            logger.error("Could not find chart data in HTML file")
            
        # Fallback to a simple approach if we couldn't extract the data
        logger.warning("Using fallback method for capturing screenshot")
        
        # For Heroku, we need to use a different approach
        # First, check if we're on Heroku by looking for the DYNO environment variable
        if os.environ.get("DYNO"):
            logger.info("Running on Heroku, using alternative screenshot method")
            
            # On Heroku, we'll use our Playwright-based approach with a placeholder
            # Create a simple HTML file with a message
            placeholder_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        display: flex; 
                        justify-content: center; 
                        align-items: center; 
                        height: 100vh; 
                        background-color: #f0f0f0;
                    }
                    .message { 
                        text-align: center; 
                        padding: 20px; 
                        background: white; 
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    }
                </style>
            </head>
            <body>
                <div class="message">
                    <h2>Statistics Image</h2>
                    <p>Your statistics are being processed.</p>
                    <p>Please check back later.</p>
                </div>
            </body>
            </html>
            """
            
            # Write the placeholder HTML to a temporary file
            temp_html = os.path.join(os.path.dirname(output_path), "placeholder.html")
            with open(temp_html, "w") as f:
                f.write(placeholder_html)
                
            # Use Playwright to capture the placeholder
            try:
                # Create an empty dictionary for the placeholder
                return await capture_statistics_image({}, output_path, temp_html)
            except Exception as e:
                logger.error(f"Failed to capture placeholder with Playwright: {e}")
                
                # If all else fails, copy a static placeholder image
                placeholder_path = os.path.join(os.path.dirname(__file__), "statistics_web", "placeholder.png")
                if os.path.exists(placeholder_path):
                    import shutil
                    shutil.copy(placeholder_path, output_path)
                    return output_path
                else:
                    logger.error("Placeholder image not found")
                    return None
        
        # If not on Heroku, try to use wkhtmltoimage
        try:
            logger.info(f"Capturing screenshot using wkhtmltoimage: {abs_path}")
            subprocess.run([
                "wkhtmltoimage",
                "--width", str(window_width),
                "--height", str(window_height),
                "--quality", "100",
                abs_path,
                output_path
            ], check=True)
            
            logger.info(f"Screenshot saved to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"wkhtmltoimage failed: {e}")
            
            # Try using Playwright as a fallback
            try:
                logger.info("Falling back to Playwright")
                # Use the synchronous version that works within an event loop
                
                # Use the HTML file directly
                return await capture_statistics_image({}, output_path, abs_path)
            except Exception as e:
                logger.error(f"Playwright fallback failed: {e}")
                return None
            
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        return None


async def analyze_metrics_with_assistant(stats_data, user_name):
    """
    Analyze metrics using OpenAI Assistant and return text analysis.
    
    Args:
        stats_data (dict): Statistics data dictionary
        user_name (str): User's name
        
    Returns:
        str: Text analysis from the assistant
    """
    logger.info("Analyzing metrics with OpenAI Assistant...")
    
    if not ASSISTANT_ID:
        error_msg = "Error: OPENAI_ASSISTANT_ID not found in environment variables"
        logger.error(error_msg)
        return error_msg
    
    try:
        # Create a custom JSON encoder to handle Decimal objects
        class DecimalEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, decimal.Decimal):
                    return float(obj)
                return super(DecimalEncoder, self).default(obj)
        
        # Convert stats_data to JSON string for the assistant using the custom encoder
        metrics_json = json.dumps(stats_data, indent=2, ensure_ascii=False, cls=DecimalEncoder)
        
        # Create a thread
        thread = await client.beta.threads.create()
        
        # Add a message to the thread
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Будь ласка, проаналізуй ці фітнес-метрики та надай висновки щодо тренувальних звичок користувача, якості сну, рівня стресу та загального прогресу. Ось метрики:\n\n user_full_name: {user_name}\n{metrics_json}",
        )
        
        # Run the assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=ASSISTANT_ID
        )
        
        # Wait for the analysis to complete
        while run.status in ["queued", "in_progress"]:
            logger.debug(f"Assistant run status: {run.status}")
            time.sleep(1)
            run = await client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        if run.status == "completed":
            messages = await client.beta.threads.messages.list(thread_id=thread.id)
            analysis = messages.data[0].content[0].text.value
            logger.info(f"Received analysis from assistant: {analysis[:100]}...")
            return analysis
        else:
            error_msg = f"Error during analysis. Run status: {run.status}"
            logger.error(error_msg)
            return error_msg
    
    except Exception as e:
        error_msg = f"Error during OpenAI analysis: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return error_msg


async def generate_statistics_image(chat_id, period='monthly', start_date=None, end_date=None, output_dir=None):
    """
    Generate a statistics image for a user
    
    Args:
        chat_id (int): User's chat ID
        period (str): Time period for statistics ('weekly' or 'monthly')
        start_date (datetime): Optional start date for custom period
        end_date (datetime): Optional end date for custom period
        output_dir (str): Optional output directory for the image
    
    Returns:
        tuple: (Path to the generated image file, Analysis text from OpenAI Assistant)
    """
    logger.info(f"Generating statistics image for user {chat_id}, period: {period}")
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statistics_web/static/images')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"stats_{chat_id}_{period}_{timestamp}.png"
    output_path = os.path.join(output_dir, filename)
    
    try:
        # Get statistics data
        stats_data = get_statistics_data(
            user_id=chat_id, 
            period=period, 
            start_date=start_date, 
            end_date=end_date
        )
        if "error" in stats_data:
            logger.error(f"Error getting statistics data: {stats_data['error']}")
            return None, None
        
        # Generate AI analysis of the statistics
        user_name = stats_data.get('user', {}).get('name', f"User {chat_id}")
        # analysis = await analyze_metrics_with_assistant(stats_data, user_name)
        analysis = "TESDT"
        
        # Generate HTML directly from the data dictionary
        temp_html = os.path.join(output_dir, f"temp_{chat_id}.html")
        generate_html_from_data(stats_data, output_path=temp_html, for_image=True)
        
        # Capture screenshot
        await capture_html_screenshot(temp_html, output_path)
        
        # Clean up temp files
        try:
            # Remove the temporary HTML file
            if os.path.exists(temp_html):
                os.remove(temp_html)
                logger.debug(f"Removed temporary HTML file: {temp_html}")
            
            # Remove any stats_image.html and stats_image_debug.html files
            stats_image_html = os.path.join(os.path.dirname(__file__), "statistics_web", "stats_image.html")
            stats_image_debug_html = os.path.join(os.path.dirname(__file__), "statistics_web", "stats_image_debug.html")
            
            if os.path.exists(stats_image_html):
                os.remove(stats_image_html)
                logger.debug(f"Removed stats_image.html file: {stats_image_html}")
                
            if os.path.exists(stats_image_debug_html):
                os.remove(stats_image_debug_html)
                logger.debug(f"Removed stats_image_debug.html file: {stats_image_debug_html}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
        
        logger.info(f"Generated statistics image at: {output_path}")
        return output_path, analysis
        
    except Exception as e:
        logger.error(f"Error generating statistics: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


async def main():
    """Command line interface for generating statistics images"""
    parser = argparse.ArgumentParser(description='Generate statistics image for a user')
    parser.add_argument('--chat_id', type=int, required=True, help='User chat ID')
    parser.add_argument('--period', type=str, default='monthly', choices=['daily', 'weekly', 'monthly'],
                        help='Period type (daily, weekly, monthly)')
    parser.add_argument('--start_date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('--output', type=str, help='Output image path')
    parser.add_argument('--output_dir', type=str, help='Directory to save output files')
    
    args = parser.parse_args()
    
    # If output is specified, use it directly
    if args.output:
        output_dir = os.path.dirname(args.output)
        if not output_dir:
            output_dir = "."
        
        # Generate HTML and capture screenshot
        data_path = get_statistics_data(args.chat_id, args.period, args.start_date, args.end_date)
        html_file = os.path.join(output_dir, f"stats_{args.chat_id}_temp.html")
        generate_html_from_data(data_path, output_path=html_file, for_image=True)
        output_path = await capture_html_screenshot(html_file, args.output)
        print(f"Statistics image saved to: {output_path}")
    else:
        # Use the function with directory
        output_path, analysis = await generate_statistics_image(
            args.chat_id, 
            args.period, 
            args.start_date, 
            args.end_date, 
            args.output_dir
        )
        print(f"Statistics image saved to: {output_path}")
        print(f"Analysis: {analysis}")


if __name__ == "__main__":
    main()
