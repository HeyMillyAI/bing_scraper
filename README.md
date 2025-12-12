# Bing Shopping Product Scraper API

A Flask-based REST API that scrapes Bing Shopping and returns structured product data. Uses Playwright for JavaScript rendering and BeautifulSoup for HTML parsing.

## Features

- 🔍 **Product Search**: Search Bing Shopping with any query
- 🎭 **JavaScript Rendering**: Uses Playwright to render dynamic content
- 📦 **Structured Data**: Extracts product name, price, images, links, seller info, and more
- 🔐 **API Key Authentication**: Simple internal API key protection
- 🌐 **CORS Enabled**: Ready for cross-origin requests

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/HeyMillyAI/bing_scraper.git
cd bing_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env to customize API_KEY and PORT
```

## Usage

### Start the Server

```bash
python app.py
```

The API will start on `http://localhost:5000` (or the port specified in `.env`).

### API Endpoints

#### Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

#### Search Products
```bash
POST /search
```

**Headers:**
```
X-Internal-Key: milly-internal-2024
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "laptop",
  "maxResults": 10
}
```

**Response:**
```json
{
  "products": [
    {
      "name": "Dell XPS 13 Laptop",
      "price": "€ 1.299,00",
      "brand": null,
      "images": [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
      ],
      "link": "https://store.example.com/product",
      "site": "Example Store",
      "sale_badge": "Sale",
      "free_shipping": true
    }
  ],
  "query": "laptop",
  "total_cards": 25,
  "extracted": 10
}
```

### Example with cURL

```bash
curl -X POST http://localhost:5000/search \
  -H "X-Internal-Key: milly-internal-2024" \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop", "maxResults": 5}'
```

### Example with Python

```python
import requests

response = requests.post(
    'http://localhost:5000/search',
    headers={'X-Internal-Key': 'milly-internal-2024'},
    json={'query': 'laptop', 'maxResults': 5}
)

data = response.json()
print(f"Found {len(data['products'])} products")
```

## Product Data Fields

Each product in the response contains:

- `name`: Product name/title
- `price`: Price string (e.g., "€ 1.299,00")
- `brand`: Brand name (if available)
- `images`: Array of image URLs (up to 5)
- `link`: Direct product link
- `site`: Seller/store name
- `sale_badge`: Sale or promotional badge text (if any)
- `free_shipping`: Boolean indicating free shipping availability

## Configuration

Environment variables can be set in a `.env` file:

- `INTERNAL_API_KEY`: API key for authentication (default: `milly-internal-2024`)
- `PORT`: Server port (default: `5000`)

## Technical Details

### Extraction Strategy

The scraper uses multiple fallback strategies to extract product data:

1. **Card Detection**: Identifies both grid cards (`li.br-item`) and narrow cards (`div.br-gOffCard`)
2. **Name Extraction**: Tries multiple selectors to find product titles
3. **Price Parsing**: Uses regex to extract currency and amount
4. **Image Collection**: Implements 3 methods to find product images:
   - Slideshow containers with carousels
   - Narrow card slideshows
   - Fallback to main image areas
5. **Link Extraction**: 4 strategies to find direct product links:
   - Direct product links (oboSnOpt)
   - Links with tracking (aclick)
   - Data-url attributes
   - Standard href attributes

### Browser Rendering

- Uses Chromium via Playwright
- Sets custom User-Agent and Accept-Language headers
- Waits for network idle before extraction
- Additional 2-second delay for JavaScript completion

## Error Handling

- `401 Unauthorized`: Invalid or missing API key
- `400 Bad Request`: Missing required query parameter
- `500 Internal Server Error`: Scraping or extraction errors

## Limitations

- Requires internet connection to access Bing Shopping
- Extraction patterns are specific to Bing Shopping's current HTML structure
- Rate limiting may apply based on Bing's policies

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
