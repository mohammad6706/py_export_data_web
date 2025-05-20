
# **Web Content Extraction API Documentation**

📌 **Overview**

This API is designed to extract structured information from web pages and provides the following features:

✅ **HTML content** (only body section)

✅ **Cleaned text** (using the Trafilatura library)

✅ **Internal and external links** (only from the homepage of the website)

✅ **HTTP status codes** (for both target URL and homepage)

✅ **Error handling** (with retry mechanism for network issues)


🔗 **Important Links after server launch**

Interactive Documentation (Swagger UI):

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Ideal for direct API testing and exploring available endpoints.


Alternative Documentation (ReDoc):

[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Provides a more organized display of documentation.



**Technologies Used**

* FastAPI (Python web framework)
* aiohttp (Asynchronous HTTP client)
* BeautifulSoup4 (HTML parsing)
* Trafilatura (Text extraction from web pages)

🔧 **Setup and Installation**
**Prerequisites**

* Python 3.8 or higher
* pip (Python package manager)

1. Install the required libraries:

   ```bash
   pip install fastapi aiohttp beautifulsoup4 trafilatura tldextract uvicorn
   ```

2. Run the server:

   ```bash
   uvicorn main:app --reload
   ```

📡 **API Endpoints**

1. **Extract information from a URL (GET)**
   Path: `/extract`

   **Input parameters**:

   * `url` (required): The URL of the website to extract content from.
   * `timeout` (optional): Timeout duration for the request (default: 10 seconds).
   * `max_retries` (optional): Number of retry attempts in case of error (default: 2 retries).

   **Request Example**:

   ```bash
   curl "http://127.0.0.1:8000/extract?url=https://example.com&timeout=15&max_retries=3"
   ```

   **Response Example**:

   ```json
   {
     "original_url": "https://example.com",
     "home_url": "https://example.com/",
     "page_data": {
       "url": "https://example.com",
       "status_code": 200,
       "error": null,
       "body": "<body>...content...</body>",
       "text": "Cleaned text...",
       "success": true
     },
     "home_data": {
       "url": "https://example.com/",
       "status_code": 200,
       "error": null,
       "body": "<body>...homepage content...</body>",
       "text": "Homepage cleaned text...",
       "success": true,
       "links": {
         "internal": ["https://example.com/about"],
         "external": ["https://google.com"]
       }
     },
     "timing": {
       "processing_time_seconds": 1.5,
       "timestamp": "2023-05-20T12:00:00.000000"
     }
   }
   ```

2. **Extract information from a batch of URLs (POST)**
   Path: `/extract/batch`

   **Request body (JSON)**:

   ```json
   {
     "urls": ["https://example.com", "https://another-site.com"],
     "timeout": 20,
     "max_retries": 3
   }
   ```

   **Response Example**:

   ```json
   {
     "results": [
       {
         "original_url": "https://example.com",
         "page_data": { ... },
         "home_data": { ... }
       },
       {
         "original_url": "https://another-site.com",
         "page_data": { ... },
         "home_data": { ... }
       }
     ],
     "successful": 2,
     "failed": 0,
     "total_time": 4.2
   }
   ```

3. **Check Service Health (GET)**
   Path: `/health`

   **Response Example**:

   ```json
   {
     "status": "healthy",
     "timestamp": "2023-05-20T12:00:00.000000"
   }
   ```

⚙️ **Potential Errors**

| Status Code | Description           |
| ----------- | --------------------- |
| 400         | Invalid URL           |
| 408         | Request timed out     |
| 500         | Internal server error |

📌 **Important Notes**
✅ Supports HTTPS
✅ Automatic homepage analysis even if the input URL is problematic
✅ Logs error details for troubleshooting
✅ Asynchronous processing for better performance

📄 **Python Sample Code**

```python
import requests

# Extract single URL
response = requests.get("http://127.0.0.1:8000/extract?url=https://example.com")
print(response.json())

# Extract batch URLs
data = {
    "urls": ["https://example.com", "https://another-site.com"],
    "timeout": 20
}
response = requests.post("http://127.0.0.1:8000/extract/batch", json=data)
print(response.json())
```

