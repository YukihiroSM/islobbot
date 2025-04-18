import os
import tempfile
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from loguru import logger

template_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(template_dir))

async def capture_statistics_image(stats_data, output_path=None, template_name="template.html"):
    """
    Generate a statistics image using Playwright and the existing template
    
    Args:
        stats_data (dict): Dictionary containing statistics data
        output_path (str, optional): Path to save the output image. If None, a temporary file is created.
        template_name (str): Name of the template file to use
        
    Returns:
        str: Path to the generated image
    """
    # If no output path is provided, create a temporary file
    if output_path is None:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "statistics_image.png")
    
    # Create a temporary HTML file from the template
    template = env.get_template(template_name)
    html_content = template.render(charts=stats_data, user={"name": "Training Stats"})
    
    temp_html_path = os.path.join(os.path.dirname(output_path), "temp_stats.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Use Playwright to capture a screenshot
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        
        # Create a new page
        page = await browser.new_page(viewport={"width": 1200, "height": 1600})
        
        # Navigate to the HTML file (using proper file:// URL format)
        file_url = f"file://{os.path.abspath(temp_html_path)}"
        await page.goto(file_url)
        
        # Wait for charts to render (adjust timeout as needed)
        await page.wait_for_timeout(2000)  # 2 seconds
        
        # Take a screenshot
        await page.screenshot(path=output_path, full_page=True)
        
        # Close the browser
        await browser.close()
    
    # Clean up the temporary HTML file
    try:
        os.remove(temp_html_path)
    except Exception as e:
        logger.warning(f"Failed to remove temporary HTML file: {e}")
    
    return output_path

