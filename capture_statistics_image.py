#!/usr/bin/env python3
"""
Script to capture statistics as an image.
"""

import os
import json
from datetime import datetime
import time
import tempfile
import shutil
import argparse
import decimal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openai import OpenAI
from loguru import logger

from statistics_web.generate_web_data import generate_html_from_data, get_statistics_data
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

def capture_html_screenshot(html_file, output_path, window_width=1200, window_height=1600):
    """
    Capture a screenshot of an HTML file using Selenium
    
    Args:
        html_file (str): Path to the HTML file
        output_path (str): Path to save the screenshot
        window_width (int): Width of the browser window
        window_height (int): Height of the browser window
        
    Returns:
        str: Path to the saved screenshot
    """
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={window_width},{window_height}")
    
    # Create a unique user data directory to avoid conflicts
    temp_dir = tempfile.mkdtemp(prefix="chrome_data_")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    
    # For Heroku compatibility
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Convert to absolute path and file:// URL format
        abs_path = os.path.abspath(html_file)
        file_url = f"file://{abs_path}"
        
        # Load the HTML file
        driver.get(file_url)
        
        # Wait for charts to render
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "chart-container"))
        )
        
        # Additional wait for charts to fully render
        time.sleep(2)
        
        # Take screenshot
        driver.save_screenshot(output_path)
        logger.info(f"Statistics image saved to {output_path}")
        
        return output_path
    finally:
        # Close the driver
        driver.quit()
        
        # Clean up the temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")


def analyze_metrics_with_assistant(stats_data, user_name):
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
        thread = client.beta.threads.create()
        
        # Add a message to the thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Будь ласка, проаналізуй ці фітнес-метрики та надай висновки щодо тренувальних звичок користувача, якості сну, рівня стресу та загального прогресу. Ось метрики:\n\n user_full_name: {user_name}\n{metrics_json}",
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=ASSISTANT_ID
        )
        
        # Wait for the analysis to complete
        while run.status in ["queued", "in_progress"]:
            logger.debug(f"Assistant run status: {run.status}")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
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


def generate_statistics_image(chat_id, period='monthly', start_date=None, end_date=None, output_dir=None):
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
        analysis = analyze_metrics_with_assistant(stats_data, user_name)
        
        # Generate HTML directly from the data dictionary
        temp_html = os.path.join(output_dir, f"temp_{chat_id}.html")
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statistics_web/template_image.html')
        
        # Pass the dictionary directly to generate_html_from_data
        html_content = generate_html_from_data(
            data_path=stats_data,
            template_path=template_path,
            output_path=None,
            for_image=True
        )
        
        # Check if html_content is a PosixPath or string
        if not isinstance(html_content, str):
            logger.debug(f"html_content is not a string, it's a {type(html_content)}")
            # If it's a path, read the content from the file
            if hasattr(html_content, 'read_text'):
                html_content = html_content.read_text()
            elif hasattr(html_content, 'read'):
                with open(html_content, 'r') as f:
                    html_content = f.read()
            else:
                raise TypeError(f"Expected html_content to be a string or path, got {type(html_content)}")
        
        # Save HTML to temp file
        with open(temp_html, 'w') as f:
            f.write(html_content)
        
        # Capture screenshot
        capture_html_screenshot(temp_html, output_path)
        
        # Clean up temp file
        os.remove(temp_html)
        
        logger.info(f"Generated statistics image at: {output_path}")
        return output_path, analysis
        
    except Exception as e:
        logger.error(f"Error generating statistics: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


def main():
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
        output_path = capture_html_screenshot(html_file, args.output)
        print(f"Statistics image saved to: {output_path}")
    else:
        # Use the function with directory
        output_path, analysis = generate_statistics_image(
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
