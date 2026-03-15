"""
VnExpress RSS API Crawler
=========================
Lấy bài viết từ VnExpress thông qua RSS API, sau đó extract nội dung đầy đủ.
Hỗ trợ 8 chuyên mục tin tức.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import sqlite3
import datetime
import time
import os
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# VnExpress RSS Feeds - API chính thức
# ============================================================
RSS_FEEDS = {
    "CÔNG NGHỆ": "https://vnexpress.net/rss/so-hoa.rss",
    "KINH TẾ": "https://vnexpress.net/rss/kinh-doanh.rss",
    "THỂ THAO": "https://vnexpress.net/rss/the-thao.rss",
    "SỨC KHỎE": "https://vnexpress.net/rss/suc-khoe.rss",
    "GIẢI TRÍ": "https://vnexpress.net/rss/giai-tri.rss",
    "GIÁO DỤC": "https://vnexpress.net/rss/giao-duc.rss",
    "DU LỊCH": "https://vnexpress.net/rss/du-lich.rss",
    "PHÁP LUẬT": "https://vnexpress.net/rss/phap-luat.rss",
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "news.db")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def init_db():
    """Khởi tạo database nếu chưa tồn tại"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS News (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            image_url TEXT,
            category TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            published_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def clear_all_news():
    """Xóa toàn bộ bài viết cũ trong database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Xóa behaviors liên quan trước (nếu có)
    try:
        cursor.execute("DELETE FROM Behavior")
        print("  -> Đã xóa toàn bộ behaviors cũ")
    except sqlite3.OperationalError:
        pass  # Bảng Behavior chưa tồn tại
    # Xóa recommendations (nếu có)
    try:
        cursor.execute("DELETE FROM Recommendation")
        print("  -> Đã xóa toàn bộ recommendations cũ")
    except sqlite3.OperationalError:
        pass
    # Xóa toàn bộ news
    cursor.execute("DELETE FROM News")
    # Reset autoincrement
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='News'")
    conn.commit()
    count_after = cursor.execute("SELECT COUNT(*) FROM News").fetchone()[0]
    conn.close()
    print(f"  -> Đã xóa toàn bộ bài viết. Còn lại: {count_after}")


def get_count():
    """Đếm số bài viết hiện có"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM News")
    count = cur.fetchone()[0]
    conn.close()
    return count


def is_url_exists(url):
    """Kiểm tra URL đã tồn tại chưa"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM News WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def extract_image_from_description(description_html):
    """Trích xuất URL ảnh từ mô tả RSS (CDATA chứa HTML)"""
    if not description_html:
        return None
    try:
        soup = BeautifulSoup(description_html, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    except:
        pass
    return None


def extract_summary_text(description_html):
    """Trích xuất text tóm tắt từ mô tả RSS"""
    if not description_html:
        return None
    try:
        soup = BeautifulSoup(description_html, 'html.parser')
        text = soup.get_text(separator=' ').strip()
        return text if text else None
    except:
        return None


def extract_full_content(url):
    """Trích xuất nội dung đầy đủ bài viết từ URL"""
    try:
        # Phương pháp 1: newspaper3k
        article = Article(url, language='vi')
        article.download()
        article.parse()
        content = article.text

        if content and len(content) >= 100:
            return content

        # Phương pháp 2: BeautifulSoup fallback
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # VnExpress article body selectors
        content_selectors = [
            ('article', {'class': 'fck_detail'}),
            ('div', {'class': 'fck_detail'}),
            ('div', {'class': 'content-detail'}),
        ]

        for tag, attrs in content_selectors:
            content_div = soup.find(tag, attrs)
            if content_div:
                # Lấy text từ các thẻ p
                paragraphs = content_div.find_all('p', class_='Normal')
                if paragraphs:
                    content = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                else:
                    content = content_div.get_text(separator='\n').strip()

                if content and len(content) >= 100:
                    return content

    except Exception as e:
        pass

    return None


def parse_pub_date(date_str):
    """Parse ngày đăng từ RSS feed"""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        pass
    return datetime.datetime.now()


def crawl_from_rss(category, rss_url):
    """Crawl tất cả bài viết từ một RSS feed"""
    print(f"\n  📡 Đang lấy RSS: {category}")
    print(f"     URL: {rss_url}")

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  ❌ Lỗi parse RSS: {e}")
        return 0

    if not feed.entries:
        print(f"  ⚠️ Không có bài viết nào trong feed")
        return 0

    print(f"  📋 Tìm thấy {len(feed.entries)} bài viết trong RSS")

    new_count = 0
    for i, entry in enumerate(feed.entries):
        url = entry.get('link', '')
        if not url or not url.startswith('https://vnexpress.net/'):
            continue

        if is_url_exists(url):
            continue

        title = entry.get('title', '').strip()
        if not title:
            continue

        # Lấy thông tin từ RSS entry
        description_html = entry.get('description', '') or entry.get('summary', '')
        image_url = None
        summary = None

        # Lấy ảnh từ enclosure (chuẩn RSS)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image'):
                    image_url = enc.get('url') or enc.get('href')
                    break

        # Fallback: lấy ảnh từ description HTML
        if not image_url:
            image_url = extract_image_from_description(description_html)

        # Lấy summary text
        summary = extract_summary_text(description_html)

        # Lấy ngày đăng
        pub_date_str = entry.get('published', '') or entry.get('updated', '')
        published_at = parse_pub_date(pub_date_str)

        # Trích xuất nội dung đầy đủ từ URL bài viết
        print(f"     [{i+1}/{len(feed.entries)}] Đang lấy nội dung: {title[:50]}...", end="")
        content = extract_full_content(url)

        if not content or len(content) < 50:
            print(" ⚠️ Bỏ qua (nội dung ngắn)")
            continue

        # Lưu vào database
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO News (title, content, summary, image_url, category, source, url, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title,
                content,
                summary,
                image_url,
                category,
                "VnExpress",
                url,
                published_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(published_at, 'strftime') else str(published_at)
            ))
            conn.commit()
            conn.close()
            new_count += 1
            print(f" ✅ OK")
        except sqlite3.IntegrityError:
            print(f" ⚠️ Đã tồn tại")
            conn.close()
        except Exception as e:
            print(f" ❌ Lỗi: {e}")
            try:
                conn.close()
            except:
                pass

        # Rate limiting
        time.sleep(0.5)

    return new_count


def run_crawler(clear_old=True):
    """Chạy crawler chính"""
    print("=" * 60)
    print("  🚀 VNEXPRESS RSS CRAWLER")
    print("  Lấy bài viết đầy đủ qua RSS API")
    print("=" * 60)

    init_db()

    if clear_old:
        print("\n[BƯỚC 1] Xóa dữ liệu cũ...")
        clear_all_news()
    else:
        print(f"\n📊 Hiện có {get_count()} bài viết trong DB")

    print(f"\n[BƯỚC 2] Crawl bài viết từ {len(RSS_FEEDS)} chuyên mục RSS...")

    total_new = 0
    for category, rss_url in RSS_FEEDS.items():
        new = crawl_from_rss(category, rss_url)
        total_new += new
        print(f"  ➡️ {category}: +{new} bài mới")

    final_count = get_count()
    print("\n" + "=" * 60)
    print(f"  ✅ HOÀN TẤT! Tổng bài viết mới: {total_new}")
    print(f"  📊 Tổng bài viết trong DB: {final_count}")
    print("=" * 60)

    return total_new


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='VnExpress RSS Crawler')
    parser.add_argument('--keep-old', action='store_true', help='Giữ lại bài viết cũ, không xóa')
    args = parser.parse_args()

    run_crawler(clear_old=not args.keep_old)
