"""
Bing Shopping Product Search API - Replicates notebook extraction logic
Renders JavaScript with Playwright and extracts products using BeautifulSoup
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import os
import re
from urllib.parse import quote_plus
import uuid

app = Flask(__name__)
CORS(app)

# Simple API key authentication
API_KEY = os.getenv('INTERNAL_API_KEY', 'milly-internal-2024')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/search', methods=['POST'])
def search_products():
    """Search Bing Shopping and return extracted products (like notebook)"""

    # Check API key
    api_key = request.headers.get('X-Internal-Key')
    if api_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    query = data.get('query')
    max_results = data.get('maxResults', 10)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        # Generate Bing Shopping URL
        cvid = uuid.uuid4().hex.upper()
        encoded_query = quote_plus(query)
        url = f"https://www.bing.com/shop?q={encoded_query}&qs=n&form=SHOPSB&sp=-1&lq=0&pq={encoded_query}&sc=0-{len(query)}&sk=&cvid={cvid}"

        print(f"🔍 Searching Bing Shopping: {query}")

        # Render with Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set headers
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8'
            })

            # Navigate and wait for network to be idle
            print(f"   ⏳ Loading page...")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Additional wait for JS to complete
            time.sleep(2)

            # Get rendered HTML
            html_content = page.content()

            # Close browser
            browser.close()

            print(f"   ✅ Rendered {len(html_content)} bytes")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find product cards (exact patterns from notebook)
        type1_cards = soup.select('li.br-item')  # Grid cards
        type2_cards = soup.select('div.br-gOffCard')  # Narrow cards (better - direct links)

        # Narrow cards first (they have direct product links)
        all_cards = type2_cards + type1_cards

        print(f"   📦 Found {len(type1_cards)} grid + {len(type2_cards)} narrow = {len(all_cards)} total")

        # Extract products from cards
        products = []

        for i, card in enumerate(all_cards[:max_results]):
            try:
                product = extract_from_bing_card(card)

                if product and product.get('name') and product.get('price'):
                    products.append(product)
                    print(f"   [{i+1}] ✅ {product['name'][:40]}... - {product['price']}")
            except Exception as e:
                print(f"   [{i+1}] ❌ Error: {e}")
                continue

        print(f"   ✅ Extracted {len(products)} products")

        return jsonify({
            'products': products,
            'query': query,
            'total_cards': len(all_cards),
            'extracted': len(products)
        })

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def extract_from_bing_card(card):
    """Extract product data from Bing Shopping card - EXACT NOTEBOOK LOGIC"""
    product = {
        'name': None,
        'price': None,
        'brand': None,
        'images': [],
        'link': None,
        'site': None,
        'sale_badge': None,
        'free_shipping': False,
    }

    # Extract product name - try multiple selectors (from notebook)
    name_elem = (
        card.select_one('.br-pdItemName span[title]') or
        card.select_one('.br-pdItemName-noHover span[title]') or
        card.select_one('.br-offTtl span[title]')
    )
    if name_elem:
        product['name'] = name_elem.get('title', '').strip()

    # Fallback: try getting text content
    if not product['name']:
        title_div = card.select_one('.br-pdItemName, .br-offTtl')
        if title_div:
            product['name'] = title_div.get_text(strip=True)

    # Extract price (from notebook)
    price_elem = (
        card.select_one('.pd-price.br-dealPrice') or
        card.select_one('.pd-price.br-standardPrice') or
        card.select_one('.br-offPrice .br-price') or
        card.select_one('.br-price')
    )
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        price_match = re.search(r'€\s*[\d,\.]+', price_text)
        if price_match:
            product['price'] = price_match.group(0).strip()

    # Extract seller (from notebook)
    seller_elem = (
        card.select_one('.br-sellersCite') or
        card.select_one('.br-offSlrTxt') or
        card.select_one('.br-offSlr')
    )
    if seller_elem:
        product['site'] = seller_elem.get_text(strip=True)

    # Extract sale badge
    badge_elem = card.select_one('.br-newbadge')
    if badge_elem:
        product['sale_badge'] = badge_elem.get_text(strip=True)

    # Check for free shipping
    free_text = card.get_text().lower()
    if 'gratis' in free_text or 'free shipping' in free_text:
        product['free_shipping'] = True

    # Extract images (from notebook logic)
    all_images = []

    # Method 1: Slideshow container with carousel
    slideshow_container = card.select_one('.br-sldshw')
    if slideshow_container:
        # Main image
        main_img = slideshow_container.select_one('.br-pdMainImg img[src]')
        if main_img:
            src = main_img.get('src', '')
            if src and not src.startswith('data:') and src.startswith('http'):
                all_images.append(src)

        # Carousel images
        carousel_imgs = slideshow_container.select('.b_slidebar .slide img[src]')
        for img in carousel_imgs:
            src = img.get('src', '')
            if src and not src.startswith('data:'):
                if src.startswith('//'):
                    src = 'https:' + src
                if src.startswith('http'):
                    width = img.get('width', '')
                    height = img.get('height', '')
                    if width in ['15', '18'] or height in ['15', '18']:
                        continue
                    if src not in all_images:
                        all_images.append(src)

    # Method 2: Narrow cards with slideshows
    if not all_images:
        slideexp_imgs = card.select('.b_slideexp .slide img[src], .b_slidebar .slide img[src]')
        for img in slideexp_imgs:
            src = img.get('src', '')
            if src and not src.startswith('data:'):
                if src.startswith('//'):
                    src = 'https:' + src
                if src.startswith('http'):
                    width = img.get('width', '')
                    height = img.get('height', '')
                    if width in ['15', '18'] or height in ['15', '18']:
                        continue
                    if src not in all_images:
                        all_images.append(src)

    # Method 3: Fallback to main image area
    if not all_images:
        img_containers = [
            '.br-offImg img[src]',
            '.br-pdMainImg img[src]',
            '.cico img[src]',
            'img[src]'
        ]

        for selector in img_containers:
            imgs = card.select(selector)
            for img in imgs:
                src = img.get('src', '')
                if src and not src.startswith('data:'):
                    if src.startswith('//'):
                        src = 'https:' + src
                    if src.startswith('http'):
                        width = img.get('width', '')
                        height = img.get('height', '')
                        if width in ['15', '18'] or height in ['15', '18']:
                            continue
                        if src not in all_images:
                            all_images.append(src)
                            break
            if all_images:
                break

    product['images'] = all_images[:5]  # Max 5 images

    # Extract link (from notebook - 6 strategies)
    link = None

    # Strategy 1: obo/oboSnOpt links (direct product links)
    link_elem = card.select_one('a.br-oboSnOptLink[href], a.br-offLink[href]')
    if link_elem:
        href = link_elem.get('href', '')
        if href and not 'bing.com/shop/entitydetails' in href:
            link = href

    # Strategy 2: Any link with aclick
    if not link:
        link_elem = card.select_one('a[href*="aclick"]')
        if link_elem:
            href = link_elem.get('href', '')
            if href and not 'bing.com/shop/entitydetails' in href:
                link = href

    # Strategy 3: data-url attribute
    if not link:
        if card.get('data-url'):
            link = card.get('data-url')

    # Strategy 4: Any href
    if not link:
        link_elem = card.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href and href.startswith('http') and not 'bing.com' in href:
                link = href

    product['link'] = link

    return product


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
