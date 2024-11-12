# scraper_wrapper.py
import argparse
import json
import sys
from amazon_scraper1 import search as amazon_search
from flipkart_scraper import search as flipkart_search
from product_info_fetcher1 import fetch_amazon_product_info, fetch_flipkart_product_info

def print_json(data):
    """Print data as JSON and flush stdout"""
    print(json.dumps(data))
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keywords', help='Comma-separated keywords or URLs')
    parser.add_argument('--num_products', type=int, default=30)
    parser.add_argument('--platform', choices=['amazon', 'flipkart'])
    parser.add_argument('--type', choices=['rank', 'product'])
    args = parser.parse_args()

    try:
        keywords = args.keywords.split(',')
        total_items = len(keywords)
        all_results = []

        for idx, keyword in enumerate(keywords, 1):
            try:
                # Print progress
                print_json({
                    "type": "progress",
                    "current": idx,
                    "total": total_items,
                    "keyword": keyword
                })

                # Get results based on type and platform
                if args.type == 'rank':
                    if args.platform == 'amazon':
                        result = amazon_search(keyword, args.num_products)
                    else:
                        result = flipkart_search(keyword, args.num_products)
                else:  # product info
                    if args.platform == 'amazon':
                        result = fetch_amazon_product_info(keyword)
                    else:
                        result = fetch_flipkart_product_info(keyword)

                if result:
                    all_results.extend(result if isinstance(result, list) else [result])

                # Print individual result
                print_json({
                    "type": "result",
                    "data": result
                })

            except Exception as e:
                print_json({
                    "type": "error",
                    "message": str(e),
                    "keyword": keyword
                })

        # Print final results
        print_json({
            "type": "complete",
            "results": all_results
        })

    except Exception as e:
        print_json({
            "type": "error",
            "message": str(e)
        })
        sys.exit(1)

if __name__ == '__main__':
    main()