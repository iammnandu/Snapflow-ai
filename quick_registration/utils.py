# quick_registration/utils.py
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile


def generate_event_card_image(registration_link, request=None):
    """
    Generate an event card image with event details and QR code
    
    Args:
        registration_link: QuickRegistrationLink object
        request: HTTP request object for generating full URLs
        
    Returns:
        BytesIO object containing the event card image
    """
    event = registration_link.event
    
    # Create a QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    full_url = registration_link.get_full_url(request)
    qr.add_data(full_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Create a new image with white background
    card_width, card_height = 1000, 600
    card = Image.new('RGB', (card_width, card_height), color='white')
    draw = ImageDraw.Draw(card)
    
    # Try to load fonts
    try:
        # Try to use system fonts or fonts from settings if configured
        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Roboto-Regular.ttf')
        title_font = ImageFont.truetype(font_path, 40)
        header_font = ImageFont.truetype(font_path, 30)
        text_font = ImageFont.truetype(font_path, 24)
    except IOError:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Add company logo/name at top
    company_name = "SnapFlow"
    draw.text((50, 40), company_name, fill='#0066CC', font=title_font)
    
    # Add horizontal line below company name
    draw.line((50, 100, card_width-50, 100), fill='#CCCCCC', width=2)
    
    # Add event title
    title_y = 120
    draw.text((50, title_y), event.title, fill='#000000', font=header_font)
    
    # Add event details
    details_y = title_y + 60
    draw.text((50, details_y), f"Type: {event.event_type}", fill='#333333', font=text_font)
    draw.text((50, details_y + 40), f"Date: {event.start_date.strftime('%B %d, %Y')}", fill='#333333', font=text_font)
    if event.end_date and event.end_date != event.start_date:
        draw.text((50, details_y + 80), f"End: {event.end_date.strftime('%B %d, %Y')}", fill='#333333', font=text_font)
    
    # Add location information
    location_y = details_y + 120
    draw.text((50, location_y), f"Location: {event.location}", fill='#333333', font=text_font)
    
    # Try to load event logo if it exists
    if event.logo:
        try:
            logo_size = (120, 120)
            logo_img = Image.open(event.logo.path)
            logo_img = logo_img.resize(logo_size, Image.LANCZOS)
            card.paste(logo_img, (card_width - 170, 130))
        except (IOError, AttributeError):
            # If logo can't be loaded, draw a placeholder
            draw.rectangle((card_width - 170, 130, card_width - 50, 250), outline='#CCCCCC')
            draw.text((card_width - 140, 180), "LOGO", fill='#CCCCCC', font=text_font)
    
    # Place QR code
    qr_size = 200
    qr_img_resized = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    card.paste(qr_img_resized, (card_width - qr_size - 50, card_height - qr_size - 50))
    
    # Add registration information next to QR code
    reg_text_y = card_height - qr_size - 40
    draw.text((50, reg_text_y), "Scan to Register:", fill='#000000', font=header_font)
    draw.text((50, reg_text_y + 50), "Or visit:", fill='#333333', font=text_font)
    draw.text((50, reg_text_y + 90), full_url, fill='#0066CC', font=text_font)
    
    # Add expiration information if applicable
    if registration_link.expires_at:
        expires_text = f"Link expires: {registration_link.expires_at.strftime('%B %d, %Y %H:%M')}"
        draw.text((50, reg_text_y + 130), expires_text, fill='#FF6600', font=text_font)
    
    # Save to BytesIO
    buffer = BytesIO()
    card.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer


def generate_event_card_pdf(registration_link, request=None):
    """
    Generate an elegant event card PDF with event details and QR code
    
    Args:
        registration_link: QuickRegistrationLink object
        request: HTTP request object for generating full URLs
        
    Returns:
        BytesIO object containing the event card PDF
    """
    event = registration_link.event
    buffer = BytesIO()
    
    # Create PDF canvas
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    
    full_url = registration_link.get_full_url(request)
    qr.add_data(full_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to a temporary file
    qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    qr_img.save(qr_temp.name)
    qr_temp.close()
    
    # Define colors
    primary_color = colors.HexColor('#a07b50')  # Elegant gold/bronze
    text_color = colors.HexColor('#333333')
    accent_color = colors.HexColor('#e0e0e0')
    
    # Try to register custom fonts
    try:
        pdfmetrics.registerFont(TTFont('Roboto', os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Roboto-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('RobotoBold', os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Roboto-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('RobotoLight', os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Roboto-Light.ttf')))
        font_name = 'Roboto'
        bold_font = 'RobotoBold'
        light_font = 'RobotoLight'
    except:
        font_name = 'Helvetica'
        bold_font = 'Helvetica-Bold'
        light_font = 'Helvetica'
    
    # Company name/logo at top (centered)
    c.setFont(bold_font, 28)
    c.setFillColor(primary_color)
    company_name = "SnapFlow"
    company_width = c.stringWidth(company_name, bold_font, 28)
    c.drawString((width - company_width) / 2, height - 1*inch, company_name)
    
    # Horizontal line
    c.setStrokeColor(accent_color)
    c.line(1*inch, height - 1.3*inch, width - 1*inch, height - 1.3*inch)
    
    # Event title (centered)
    c.setFont(bold_font, 22)
    c.setFillColor(text_color)
    title_width = c.stringWidth(event.title, bold_font, 22)
    c.drawString((width - title_width) / 2, height - 2*inch, event.title)
    
    # Event details (centered layout)
    c.setFont(font_name, 14)
    c.setFillColor(text_color)
    
    # Type
    type_text = f"Type: {event.event_type}"
    c.drawString(1.5*inch, height - 2.5*inch, type_text)
    
    # Date information
    date_text = f"Date: {event.start_date.strftime('%B %d, %Y')}"
    c.drawString(1.5*inch, height - 2.9*inch, date_text)
    
    # End date if applicable
    if event.end_date and event.end_date != event.start_date:
        end_date_text = f"End: {event.end_date.strftime('%B %d, %Y')}"
        c.drawString(1.5*inch, height - 3.3*inch, end_date_text)
        location_y = 3.7
    else:
        location_y = 3.3
    
    # Location
    location_text = f"Location: {event.location}"
    c.drawString(1.5*inch, height - location_y*inch, location_text)
    
    # Place QR code (right aligned)
    qr_width, qr_height = 2*inch, 2*inch
    c.drawImage(qr_temp.name, width - 3*inch, height - 3.5*inch, width=qr_width, height=qr_height)
    
    # Registration information (centered)
    scan_text = "Scan to Register"
    c.setFont(bold_font, 16)
    c.setFillColor(primary_color)
    scan_width = c.stringWidth(scan_text, bold_font, 16)
    c.drawString((width - scan_width) / 2, height - 5*inch, scan_text)
    
    # "Or visit:" text
    c.setFont(font_name, 12)
    c.setFillColor(text_color)
    visit_text = "Or visit:"
    visit_width = c.stringWidth(visit_text, font_name, 12)
    c.drawString((width - visit_width) / 2, height - 5.3*inch, visit_text)
    
    # URL text
    c.setFillColor(primary_color)
    url_width = c.stringWidth(full_url, font_name, 12)
    if url_width > width - 2*inch:
        # Truncate URL if it's too long
        display_url = full_url
        while c.stringWidth(display_url + "...", font_name, 12) > width - 2*inch and len(display_url) > 10:
            display_url = display_url[:-1]
        display_url += "..."
        url_width = c.stringWidth(display_url, font_name, 12)
        c.drawString((width - url_width) / 2, height - 5.6*inch, display_url)
    else:
        c.drawString((width - url_width) / 2, height - 5.6*inch, full_url)
    
    # Expiration information if applicable
    if registration_link.expires_at:
        c.setFont(light_font, 11)
        c.setFillColor(text_color)
        expires_text = f"Link expires: {registration_link.expires_at.strftime('%B %d, %Y')}"
        expires_width = c.stringWidth(expires_text, light_font, 11)
        c.drawString((width - expires_width) / 2, height - 6*inch, expires_text)
    
    # Add elegant footer
    c.setFont(light_font, 9)
    c.setFillColor(colors.gray)
    footer_text = "Generated by SnapFlow Event Management"
    c.drawCentredString(width/2, 0.5*inch, footer_text)
    
    # Save the PDF canvas
    c.save()
    
    # Clean up temporary file
    try:
        os.unlink(qr_temp.name)
    except (OSError, PermissionError):
        pass
    
    buffer.seek(0)
    return buffer