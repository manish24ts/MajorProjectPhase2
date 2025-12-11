import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
import re

def fetch_news(topics, limit=10):
    """Fetch news articles from multiple RSS feeds based on topics."""
    all_articles = []
    
    rss_feeds = {
        'technology': [
            'https://feeds.bbci.co.uk/news/technology/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
        ],
        'business': [
            'https://feeds.bbci.co.uk/news/business/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
        ],
        'science': [
            'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Science.xml',
        ],
        'health': [
            'https://feeds.bbci.co.uk/news/health/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Health.xml',
        ],
        'world': [
            'https://feeds.bbci.co.uk/news/world/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
        ],
        'sports': [
            'https://feeds.bbci.co.uk/sport/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml',
        ],
        'entertainment': [
            'https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml',
        ],
        'general': [
            'https://feeds.bbci.co.uk/news/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
        ]
    }
    
    feeds_to_check = []
    for topic in topics:
        topic_lower = topic.lower().strip()
        matched = False
        for category, urls in rss_feeds.items():
            if topic_lower in category or category in topic_lower:
                feeds_to_check.extend(urls)
                matched = True
                break
        if not matched:
            feeds_to_check.extend(rss_feeds['general'])
    
    feeds_to_check = list(set(feeds_to_check))
    
    for feed_url in feeds_to_check:
        try:
            articles = parse_rss_feed(feed_url, topics)
            all_articles.extend(articles)
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {e}")
            continue
    
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        if article['title'] not in seen_titles:
            seen_titles.add(article['title'])
            unique_articles.append(article)
    
    scored_articles = []
    for article in unique_articles:
        score = calculate_relevance(article, topics)
        article['relevance_score'] = score
        scored_articles.append(article)
    
    scored_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return scored_articles[:limit]

def parse_rss_feed(feed_url, topics):
    """Parse an RSS feed and extract articles with images."""
    articles = []
    
    try:
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries[:20]:
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            
            image_url = extract_image_from_entry(entry, summary)
            
            summary = BeautifulSoup(summary, 'html.parser').get_text()
            summary = re.sub(r'\s+', ' ', summary).strip()
            
            link = entry.get('link', '')
            
            published = entry.get('published', entry.get('updated', ''))
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    published = pub_date.strftime('%B %d, %Y')
            except:
                published = datetime.now().strftime('%B %d, %Y')
            
            source = feed.feed.get('title', 'Unknown Source')
            
            articles.append({
                'title': title,
                'summary': summary[:500] if summary else '',
                'link': link,
                'image_url': image_url,
                'published': published,
                'source': source
            })
            
    except Exception as e:
        print(f"Error parsing RSS feed: {e}")
    
    return articles

def extract_image_from_entry(entry, summary_html):
    """Extract image URL from RSS entry."""
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('medium') == 'image' or media.get('type', '').startswith('image'):
                return media.get('url', '')
    
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url', '')
    
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('href', enc.get('url', ''))
    
    if summary_html:
        soup = BeautifulSoup(summary_html, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    
    return ''

def calculate_relevance(article, topics):
    """Calculate relevance score based on topic matching."""
    score = 0
    text = (article['title'] + ' ' + article['summary']).lower()
    
    for topic in topics:
        topic_lower = topic.lower().strip()
        words = topic_lower.split()
        
        for word in words:
            if word in text:
                if word in article['title'].lower():
                    score += 3
                else:
                    score += 1
    
    return score

def scrape_article_content(url):
    """Scrape full article content from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        article = soup.find('article') or soup.find('main') or soup.find('body')
        
        if article:
            paragraphs = article.find_all('p')
            content = ' '.join(p.get_text() for p in paragraphs)
            return re.sub(r'\s+', ' ', content).strip()
        
        return ''
    except Exception as e:
        print(f"Error scraping article: {e}")
        return ''
