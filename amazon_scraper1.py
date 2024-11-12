import requests
from bs4 import BeautifulSoup
import time
import random
import logging
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

def search(keywords, num_products=30):
    try:
        num_products = int(num_products)

        # Fetch data
        all_data = fetch_amazon_data(keywords, num_products)
        
        # Process data
        products = process_amazon_data(all_data, num_products)

        if not products:
            error_msg = f"No products found for '{keywords}'"
            logger.error(error_msg)
            raise Exception(error_msg)

        return products

    except ValueError as ve:
        error_msg = f"ValueError during Amazon search: {str(ve)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as e:
        error_msg = f"Error during Amazon search: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def fetch_amazon_data(keyword, num_products):
    all_data = []
    url = f"https://www.amazon.in/s?k={keyword.replace(' ', '+')}"

    page = 1
    max_retries = 3
    retry_delay = 5

    while len(all_data) * 16 < num_products:  # Assuming 16 products per page
        for attempt in range(max_retries):
            try:
                headers = get_random_headers()  # Get new headers for each request
                logger.info(f"Fetching page {page} for '{keyword}' (Attempt {attempt + 1})")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                all_data.append(soup)

                next_page = soup.find("a", class_="s-pagination-next")
                if next_page and "href" in next_page.attrs:
                    url = "https://www.amazon.in" + next_page["href"]
                    logger.info(f"Fetched page {page}, moving to next page...")
                    page += 1
                    time.sleep(random.uniform(2, 5))
                else:
                    logger.info(f"No more pages found for '{keyword}'")
                    return all_data

                break  # If successful, break the retry loop

            except HTTPError as http_err:
                if response.status_code == 503:
                    logger.warning(f"503 error encountered. Attempt {attempt + 1} of {max_retries}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Max retries reached for 503 error on page {page}")
                        raise
                else:
                    logger.error(f"HTTP error occurred: {http_err}")
                    raise
            except RequestException as e:
                logger.error(f"An error occurred while fetching results for '{keyword}' on page {page}: {e}")
                raise

    return all_data

def process_amazon_data(all_data, num_products=30):
    products = []
    for soup in all_data:
        search_results = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        logger.info(f"Found {len(search_results)} search results on this page")

        for result in search_results:
            if len(products) >= num_products:
                break

            try:
                asin = result.get("data-asin")
                logger.debug(f"Processing product with ASIN: {asin}")

                title_element = result.find("h2", class_="a-size-mini")
                title = title_element.text.strip() if title_element else "Title not found"
                
                price_element = result.find("span", class_="a-price-whole")
                if not price_element:
                    price_element = result.find("span", class_="a-color-base")
                price = price_element.text.strip() if price_element else "N/A"
                if not price.replace(',', '').replace('.', '').isdigit():
                    price = "N/A"
                
                # Construct link using ASIN
                link = f"https://www.amazon.in/dp/{asin}" if asin else "N/A"
                
                rating_element = result.find("span", class_="a-icon-alt")
                rating = rating_element.text.split(" ")[0] if rating_element else "N/A"
                
                reviews_element = result.find("span", class_="a-size-base s-underline-text")
                reviews = reviews_element.text.strip("() ") if reviews_element else "N/A"

                # Get bought in past month count - check both possible classes
                bought_count = "N/A"
                
                # Try the first class
                bought_element = result.find("span", class_="a-size-small.social-proofing-faceout-title-text")
                if not bought_element:
                    # Try the second class if first one not found
                    bought_element = result.find("span", class_="a-size-base a-color-secondary")
                
                if bought_element:
                    bought_text = bought_element.text.strip()
                    if "bought in past month" in bought_text.lower():
                        bought_count = bought_text.split()[0]

                # Determine if the product is sponsored based on data-asin class
                sponsored_class = result.get("class", [])
                product_type = "Sponsored" if "AdHolder" in sponsored_class else "Organic"
                
                logger.debug(f"Product type determined: {product_type}")

                products.append({
                    "rank": len(products) + 1,
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "link": link,
                    "rating": rating,
                    "reviews": reviews,
                    "bought_last_month": bought_count,
                    "type": product_type
                })

                logger.debug(f"Successfully processed product: {title}")

            except AttributeError as ae:
                logger.error(f"AttributeError processing product: {str(ae)}")
            except Exception as e:
                logger.error(f"Error processing product: {str(e)}")

    logger.info(f"Processed {len(products)} products in total")
    return products[:num_products]

# Set up more detailed logging
logging.basicConfig(level=logging.DEBUG)