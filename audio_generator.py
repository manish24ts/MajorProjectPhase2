import os
from gtts import gTTS
from datetime import datetime

def generate_audio(articles, output_path, overall_summary=''):
    """Generate audio version of the newsletter using gTTS."""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    script = create_audio_script(articles, overall_summary)
    
    try:
        tts = gTTS(text=script, lang='en', slow=False)
        tts.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error generating audio: {e}")
        raise

def create_audio_script(articles, overall_summary=''):
    """Create a readable script for text-to-speech."""
    
    lines = []
    
    lines.append("Welcome to your daily newsletter.")
    lines.append(f"Today is {datetime.now().strftime('%B %d, %Y')}.")
    lines.append(f"We have {len(articles)} stories for you today.")
    
    if overall_summary:
        lines.append("")
        lines.append("Here's a quick overview of today's top stories.")
        lines.append(clean_text_for_speech(overall_summary))
    
    lines.append("")
    lines.append("Now, let's dive into the details.")
    lines.append("")
    
    for i, article in enumerate(articles, 1):
        lines.append(f"Story number {i}.")
        
        title = article.get('title', 'Untitled')
        title = clean_text_for_speech(title)
        lines.append(title)
        
        lines.append(f"From {article.get('source', 'unknown source')}.")
        
        summary = article.get('simplified_summary', article.get('original_summary', ''))
        summary = clean_text_for_speech(summary)
        lines.append(summary)
        
        if article.get('link'):
            lines.append("You can find the full article link in your PDF newsletter.")
        
        if i < len(articles):
            lines.append("Moving on to the next story.")
        
        lines.append("")
    
    lines.append("That concludes today's newsletter.")
    lines.append("Thank you for listening. Have a great day!")
    
    return " ".join(lines)

def clean_text_for_speech(text):
    """Clean text to make it more suitable for speech synthesis."""
    
    replacements = {
        '&': 'and',
        '%': 'percent',
        '$': 'dollars',
        '#': 'number',
        '@': 'at',
        '+': 'plus',
        '=': 'equals',
        '<': 'less than',
        '>': 'greater than',
        '|': ',',
        '/': ' or ',
        '...': '.',
        '—': ', ',
        '–': ', ',
        '"': '',
        "'": '',
        '\n': ' ',
        '\t': ' ',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    import re
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def estimate_audio_duration(articles):
    """Estimate the duration of the audio in minutes."""
    script = create_audio_script(articles)
    words = len(script.split())
    words_per_minute = 150
    return round(words / words_per_minute, 1)
