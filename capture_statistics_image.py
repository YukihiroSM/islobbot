#!/usr/bin/env python3
"""
Script to generate statistics image for a user based on their chat_id.
This uses the existing statistics_web functionality to generate the HTML
and then captures it as a PNG image.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('capture_statistics_image')

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent))

# Import after path setup
from statistics_web.generate_web_data import generate_html_from_data, get_statistics_data

# Import Selenium components
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


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
        
        # Give additional time for charts to fully render
        time.sleep(2)
        
        # Get the height of the content
        body_height = driver.execute_script("return document.body.scrollHeight")
        
        # Adjust window height if needed
        if body_height > window_height:
            driver.set_window_size(window_width, body_height)
            time.sleep(1)  # Allow time for resize
        
        # Take screenshot
        driver.save_screenshot(output_path)
        logger.info(f"Statistics image saved to {output_path}")
        
        return output_path
    finally:
        driver.quit()


def generate_statistics_image(chat_id, period='monthly', start_date=None, end_date=None, output_dir=None):
    """
    Generate a statistics image for a user
    
    Args:
        chat_id (int): User's chat ID
        period (str): Period type (daily, weekly, monthly)
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        output_dir (str): Directory to save the output files
        
    Returns:
        str: Path to the generated image
    """
    logger.info(f"Generating statistics image for chat_id={chat_id}, period={period}, start_date={start_date}, end_date={end_date}")
    
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = Path(__file__).parent / "temp"
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate filenames with user ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    html_file = output_dir / f"stats_{chat_id}_{timestamp}.html"
    image_file = output_dir / f"stats_{chat_id}_{timestamp}.png"
    
    # Generate HTML from data
    data_path = get_statistics_data(chat_id, period, start_date, end_date)
    generate_html_from_data(data_path, output_path=html_file, for_image=True)
    
    # Capture screenshot
    output_path = capture_html_screenshot(html_file, image_file)
    
    return output_path


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
        output_path = generate_statistics_image(
            args.chat_id, 
            args.period, 
            args.start_date, 
            args.end_date, 
            args.output_dir
        )
        print(f"Statistics image saved to: {output_path}")


if __name__ == "__main__":
    main()
