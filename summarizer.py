import os

def get_groq_client():
    """Get Groq client if API key is available."""
    api_key = os.environ.get('GROQ_API_KEY')
    if api_key:
        from groq import Groq
        return Groq(api_key=api_key)
    return None

def summarize_articles(articles, prompt=''):
    """Summarize and simplify news articles using Groq (free LLM)."""
    if not articles:
        return []
    
    summarized = []
    
    for article in articles:
        try:
            summary = summarize_single_article(article, prompt=prompt)
            summarized.append({
                'title': article['title'],
                'original_summary': article['summary'],
                'simplified_summary': summary,
                'source': article['source'],
                'published': article['published'],
                'link': article.get('link', ''),
                'image_url': article.get('image_url', '')
            })
        except Exception as e:
            print(f"Error summarizing article: {e}")
            summarized.append({
                'title': article['title'],
                'original_summary': article['summary'],
                'simplified_summary': article['summary'],
                'source': article['source'],
                'published': article['published'],
                'link': article.get('link', ''),
                'image_url': article.get('image_url', '')
            })
    
    return summarized

def summarize_single_article(article, prompt=''):
    """Summarize a single article using Groq's free LLM API."""
    client = get_groq_client()
    
    if not client:
        return create_simple_summary(article)
    
    try:
        user_prompt = prompt.strip()
        base_prompt = """Summarize this news article in 2-3 clear, simple sentences that anyone can understand. 
Avoid jargon and technical terms. Make it engaging and informative."""
        if user_prompt:
            base_prompt += f"\n\nUser prompt: {user_prompt}"

        base_prompt += f"""

Title: {article['title']}

Content: {article['summary']}

Summary:"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles in simple, clear language."},
                {"role": "user", "content": base_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Groq API error: {e}")
        return create_simple_summary(article)

def create_simple_summary(article):
    """Create a simple summary without AI (fallback)."""
    summary = article.get('summary', '')
    
    if len(summary) > 200:
        sentences = summary.split('.')
        short_summary = '. '.join(sentences[:2])
        if short_summary and not short_summary.endswith('.'):
            short_summary += '.'
        return short_summary
    
    return summary

def generate_overall_summary(articles, prompt=''):
    """Generate an overall summary of all news articles."""
    client = get_groq_client()
    
    if not articles:
        return "No articles available for summary."
    
    if not client:
        titles = [a.get('title', '') for a in articles[:5]]
        return f"Today's newsletter covers {len(articles)} stories including: {', '.join(titles[:3])}."
    
    try:
        article_briefs = []
        for i, article in enumerate(articles[:10], 1):
            title = article.get('title', 'Untitled')
            summary = article.get('simplified_summary', article.get('summary', ''))[:200]
            article_briefs.append(f"{i}. {title}: {summary}")
        
        all_briefs = "\n".join(article_briefs)
        
        user_prompt = prompt.strip()
        base_prompt = """Based on these news articles, write a brief 3-4 sentence executive summary highlighting the main themes and most important stories of the day. Make it engaging and informative."""
        if user_prompt:
            base_prompt += f"\n\nUser prompt: {user_prompt}"

        base_prompt += f"""

Articles:
{all_briefs}

Overall Summary:"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a news editor who writes concise, engaging daily news briefings."},
                {"role": "user", "content": base_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating overall summary: {e}")
        titles = [a.get('title', '') for a in articles[:3]]
        return f"Today's newsletter covers {len(articles)} stories including: {', '.join(titles)}."

def generate_newsletter_intro(topics, article_count):
    """Generate a newsletter introduction."""
    client = get_groq_client()
    
    if not client:
        return f"Here's your personalized newsletter with {article_count} articles on {', '.join(topics)}."
    
    try:
        prompt = f"""Write a brief, friendly 1-2 sentence introduction for a newsletter about: {', '.join(topics)}.
It should mention there are {article_count} articles. Keep it warm and engaging."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a friendly newsletter writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.8
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Here's your personalized newsletter with {article_count} articles on {', '.join(topics)}."
