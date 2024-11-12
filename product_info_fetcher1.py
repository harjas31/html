import requests
from bs4 import BeautifulSoup
import logging
import re
import random
import time
from requests.exceptions import RequestException, HTTPError

logger = logging.getLogger(__name__)

# List of user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.54"
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

def fetch_with_retries(url, max_retries=3, initial_delay=5):
    for attempt in range(max_retries):
        try:
            headers = get_random_headers()
            
            # Add a random wait time before each request
            wait_time = random.uniform(1, 1.2)  # Random wait between 1 to 3 seconds
            logger.info(f"Waiting for {wait_time:.2f} seconds before making a request...")
            time.sleep(wait_time)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except HTTPError as http_err:
            if response.status_code == 503 and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"503 error encountered. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise
        except RequestException as e:
            logger.error(f"An error occurred while fetching data: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(initial_delay)
            else:
                raise

def fetch_amazon_product_info(identifier):
    try:
        soup = fetch_amazon_data(identifier)
        return process_amazon_data(soup, identifier)
    except Exception as e:
        logger.error(f"Error fetching Amazon product info: {str(e)}")
        return None

def fetch_amazon_data(identifier):
    if re.match(r'^[A-Z0-9]{10}$', identifier):
        url = f"https://www.amazon.in/dp/{identifier}"
    elif 'amazon.in' in identifier:
        url = identifier
    else:
        raise ValueError(f"Invalid Amazon URL or ASIN: {identifier}")

    response = fetch_with_retries(url)
    return BeautifulSoup(response.content, 'html.parser')

def process_amazon_data(soup, identifier):
    try:
        title_elem = soup.find("span", {"id": "productTitle"})
        title = title_elem.text.strip() if title_elem else "N/A"
        
        price_elem = soup.find("span", {"class": "a-price-whole"})
        price = price_elem.text.strip() if price_elem else "N/A"
        
        rating_elem = soup.find("span", {"class": "a-icon-alt"})
        rating = rating_elem.text.split()[0] if rating_elem else "N/A"
        
        reviews_elem = soup.find("span", {"id": "acrCustomerReviewText"})
        reviews = reviews_elem.text.split()[0] if reviews_elem else "N/A"

        stock_status = check_stock_availability(soup)

        # Add bought last month detection
        bought_last_month = "N/A"
        bought_elem = soup.find("span", {"class": "social-proofing-faceout-title-text"})
        if bought_elem:
            bought_text = bought_elem.text.strip()
            if "bought in past month" in bought_text.lower():
                bought_match = re.search(r'(\d+K?\+?)', bought_text)
                if bought_match:
                    bought_last_month = bought_match.group(1)

        bestseller_ranks = []
        rank_elem = soup.find("div", {"id": "detailBulletsWrapper_feature_div"})
        if rank_elem:
            rank_items = rank_elem.find_all("span", {"class": "a-list-item"})
            for item in rank_items:
                if "Best Sellers Rank" in item.text:
                    rank_text = item.text.strip()
                    ranks = re.findall(r'#([\d,]+) in ([^(#]+)', rank_text)
                    for rank, category in ranks:
                        bestseller_ranks.append(f"#{rank.replace(',', '')} in {category.strip()}")

        if not bestseller_ranks:
            rank_table = soup.find("table", {"id": "productDetails_detailBullets_sections1"})
            if rank_table:
                rank_rows = rank_table.find_all("tr")
                for row in rank_rows:
                    if "Best Sellers Rank" in row.text:
                        rank_text = row.find("td", {"class": "a-size-base"}).text.strip()
                        ranks = re.findall(r'#([\d,]+) in ([^(#]+)', rank_text)
                        for rank, category in ranks:
                            bestseller_ranks.append(f"#{rank.replace(',', '')} in {category.strip()}")

        asin = identifier if not identifier.startswith('http') else re.search(r'/dp/([A-Z0-9]{10})', identifier).group(1)

        return {
            "ASIN": asin,
            "title": title,
            "price": price,
            "rating": rating,
            "reviews": reviews,
            "link": f"https://www.amazon.in/dp/{asin}",
            "BestSeller": " | ".join(bestseller_ranks) if bestseller_ranks else "N/A",
            "In Stock": stock_status,
            "bought_last_month": bought_last_month
        }
    except Exception as e:
        logger.error(f"Error processing Amazon product data: {str(e)}")
        return None

def fetch_flipkart_product_info(url):
    try:
        soup = fetch_flipkart_data(url)
        return process_flipkart_data(soup, url)
    except Exception as e:
        logger.error(f"Error fetching Flipkart product info: {str(e)}")
        return None

def fetch_flipkart_data(url):
    response = fetch_with_retries(url)
    return BeautifulSoup(response.content, 'lxml')

def process_flipkart_data(soup, url):
    try:
        title_elem = soup.find('span', class_='VU-ZEz')
        title = title_elem.text.strip() if title_elem else 'N/A'
        price_elem = soup.find('div', class_='Nx9bqj CxhGGd')
        price = price_elem.text.strip() if price_elem else 'N/A'
        rating_elem = soup.find('div', class_='XQDdHH')
        rating = rating_elem.text.strip() if rating_elem else 'N/A'
        reviews_elem = soup.find('span', class_='Wphh3N')
        reviews = reviews_elem.text.strip() if reviews_elem else 'N/A'

        if reviews != 'N/A':
            reviews = reviews.split()[0]

        return {
            "link": url,
            "title": title,
            "price": price,
            "rating": rating,
            "reviews": reviews,
        }
    except Exception as e:
        logger.error(f"Error processing Flipkart product data: {str(e)}")
        return None

def check_stock_availability(soup):
    try:
        stock_elem = soup.find("span", {"class": "a-size-medium a-color-success"})
        if stock_elem and "In stock" in stock_elem.text:
            return "Yes"
        if stock_elem and "Currently unavailable" in stock_elem.text:
            return "No"
        return "Unknown"
    except Exception as e:
        logger.error(f"Error checking stock availability: {str(e)}")
        return "Unknown"

# Set up logging
logging.basicConfig(level=logging.DEBUG)