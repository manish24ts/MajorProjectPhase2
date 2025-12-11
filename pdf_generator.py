from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import os
import requests
from io import BytesIO

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)

def get_font_family(font_style):
    """Get font family based on style preference."""
    fonts = {
        'modern': 'Helvetica',
        'classic': 'Times-Roman',
        'clean': 'Helvetica',
        'elegant': 'Times-Roman'
    }
    return fonts.get(font_style, 'Helvetica')

def download_image(url, max_width=400, max_height=200):
    """Download and resize image from URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            img_data = BytesIO(response.content)
            img = Image(img_data)
            
            aspect = img.imageWidth / img.imageHeight
            if img.imageWidth > max_width:
                img.drawWidth = max_width
                img.drawHeight = max_width / aspect
            if img.drawHeight > max_height:
                img.drawHeight = max_height
                img.drawWidth = max_height * aspect
            
            return img
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None

def generate_pdf(articles, output_path, primary_color='#1a73e8', secondary_color='#4285f4', font_style='modern', overall_summary=''):
    """Generate a styled PDF newsletter with links and images."""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    primary_rgb = hex_to_rgb(primary_color)
    secondary_rgb = hex_to_rgb(secondary_color)
    primary = colors.Color(*primary_rgb)
    secondary = colors.Color(*secondary_rgb)
    
    font_family = get_font_family(font_style)
    font_bold = font_family + '-Bold' if font_family == 'Helvetica' else font_family.replace('Roman', 'Bold')
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'NewsletterTitle',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=28,
        textColor=primary,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=12,
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=11,
        textColor=colors.darkgray,
        alignment=TA_JUSTIFY,
        spaceAfter=20,
        spaceBefore=10,
        leading=16,
        backColor=colors.Color(0.95, 0.95, 0.95),
        borderPadding=10
    )
    
    article_title_style = ParagraphStyle(
        'ArticleTitle',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=14,
        textColor=primary,
        spaceBefore=15,
        spaceAfter=6
    )
    
    source_style = ParagraphStyle(
        'SourceStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=9,
        textColor=secondary,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=11,
        textColor=colors.black,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leading=14
    )
    
    link_style = ParagraphStyle(
        'LinkStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=10,
        textColor=secondary,
        spaceAfter=12
    )
    
    elements = []
    
    elements.append(Paragraph("Your Daily Newsletter", title_style))
    elements.append(Paragraph(datetime.now().strftime("%B %d, %Y"), date_style))
    
    elements.append(HRFlowable(
        width="100%",
        thickness=2,
        color=primary,
        spaceBefore=10,
        spaceAfter=20
    ))
    
    if overall_summary:
        elements.append(Paragraph("<b>Today's Highlights</b>", ParagraphStyle(
            'HighlightTitle',
            parent=styles['Normal'],
            fontName=font_bold,
            fontSize=14,
            textColor=primary,
            spaceAfter=10
        )))
        safe_summary = overall_summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe_summary, summary_style))
        elements.append(Spacer(1, 10))
    
    if articles:
        intro_style = ParagraphStyle(
            'IntroStyle',
            parent=styles['Normal'],
            fontName=font_family,
            fontSize=12,
            textColor=colors.darkgray,
            alignment=TA_CENTER,
            spaceAfter=25
        )
        
        elements.append(Paragraph(
            f"Today's edition features {len(articles)} curated articles just for you.",
            intro_style
        ))
    
    for i, article in enumerate(articles):
        if i > 0:
            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(
                width="80%",
                thickness=0.5,
                color=colors.lightgrey,
                spaceBefore=5,
                spaceAfter=15
            ))
        
        safe_title = article.get('title', 'Untitled').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe_title, article_title_style))
        
        source_text = f"{article.get('source', 'Unknown')} | {article.get('published', 'Today')}"
        elements.append(Paragraph(source_text, source_style))
        
        image_url = article.get('image_url', '')
        if image_url:
            img = download_image(image_url)
            if img:
                elements.append(Spacer(1, 5))
                elements.append(img)
                elements.append(Spacer(1, 5))
        
        summary = article.get('simplified_summary', article.get('original_summary', ''))
        safe_summary = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe_summary, body_style))
        
        link = article.get('link', '')
        if link:
            safe_link = link.replace('&', '&amp;')
            link_text = f'<a href="{safe_link}" color="blue"><u>Read full article</u></a>'
            elements.append(Paragraph(link_text, link_style))
    
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%",
        thickness=1,
        color=secondary,
        spaceBefore=20,
        spaceAfter=10
    ))
    
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName=font_family,
        fontSize=9,
        textColor=colors.gray,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        "Generated by Your Personal Newsletter App",
        footer_style
    ))
    
    doc.build(elements)
    
    return output_path
