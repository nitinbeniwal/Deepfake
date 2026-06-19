import requests, os
from bs4 import BeautifulSoup

def crawl_page(url, output_folder="downloaded_content"):
    os.makedirs(output_folder, exist_ok=True)
    print(f"Crawling: {url}")
    try:
        soup = BeautifulSoup(
            requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text,
            "html.parser"
        )
        texts  = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 100]
        videos = [v.get("src") for v in soup.find_all("video") if v.get("src")]
        videos += [a["href"] for a in soup.find_all("a", href=True)
                   if a["href"].endswith((".mp4", ".webm"))]
        print(f"Found {len(texts)} texts, {len(videos)} videos ✅")
        return texts, videos
    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return [], []
