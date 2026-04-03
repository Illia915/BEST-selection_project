from fpdf import FPDF
from datetime import datetime
import os

class FlightReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_fonts()
        
    def _setup_fonts(self):
        # Try to find a font that supports Ukrainian
        fonts_to_try = [
            ("/System/Library/Fonts/Supplemental/Arial.ttf", "ArialU"), # MacOS
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu"), # Linux
            ("/usr/share/fonts/TTF/DejaVuSans.ttf", "DejaVu"), # Linux alternate
        ]
        self.unicode_font = None
        for path, name in fonts_to_try:
            if os.path.exists(path):
                self.add_font(name, "", path)
                self.unicode_font = name
                break

    def header(self):
        self.set_fill_color(15, 17, 23)
        self.rect(0, 0, 210, 40, "F")
        self.set_xy(10, 15)
        self.set_font("Arial" if not self.unicode_font else self.unicode_font, "B", 24)
        self.set_text_color(230, 237, 243)
        self.cell(0, 10, "UAV FLIGHT REPORT", align="L")
        self.set_xy(10, 25)
        self.set_font("Arial" if not self.unicode_font else self.unicode_font, "", 10)
        self.set_text_color(139, 148, 158)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="L")
        self.ln(25)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial" if not self.unicode_font else self.unicode_font, "I", 8)
        self.set_text_color(139, 148, 158)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_pdf_report(filename, metrics, ai_report):
    pdf = FlightReport()
    pdf.add_page()
    
    f_name = pdf.unicode_font if pdf.unicode_font else "Arial"
    
    # Summary Section
    pdf.set_font(f_name, "B", 16)
    pdf.set_text_color(88, 166, 255)
    pdf.cell(0, 10, f"Flight: {filename}", ln=True)
    pdf.ln(5)
    
    # Metrics Table
    pdf.set_font(f_name, "B", 12)
    pdf.set_text_color(230, 237, 243)
    pdf.set_fill_color(22, 27, 34)
    pdf.cell(190, 10, "Flight Metrics", ln=True, fill=True, align='C')
    pdf.ln(2)
    
    pdf.set_font(f_name, "", 10)
    pdf.set_text_color(60, 60, 60)
    
    metric_labels = {
        'total_distance_m': ('Total Distance', 'm'),
        'total_duration_s': ('Flight Duration', 's'),
        'max_horiz_speed_ms': ('Max Horiz Speed', 'm/s'),
        'max_vert_speed_ms': ('Max Vert Speed', 'm/s'),
        'max_alt_m': ('Max Altitude', 'm'),
        'max_acceleration': ('Max Acceleration', 'm/s²'),
        'imu_max_vz_ms': ('IMU Max Vertical Speed', 'm/s'),
        'max_vibration': ('Max Vibration', 'm/s²'),
    }
    
    for key, (label, unit) in metric_labels.items():
        val = metrics.get(key)
        if val is not None:
            pdf.set_font(f_name, "B", 10)
            pdf.cell(80, 8, f"{label}:", border=0)
            pdf.set_font(f_name, "", 10)
            pdf.cell(110, 8, f"{val:.1f} {unit}", border=0, ln=True)
            
    pdf.ln(10)
    
    # AI Report Section
    pdf.set_font(f_name, "B", 16)
    pdf.set_text_color(88, 166, 255)
    pdf.cell(0, 10, "AI Analysis Report", ln=True)
    pdf.ln(2)
    
    pdf.set_font(f_name, "", 10)
    pdf.set_text_color(0, 0, 0)
    
    clean_report = ai_report.replace('```markdown', '').replace('```', '').strip()
    
    # Fallback for non-unicode FPDF: replace Ukrainian characters with Latin counterparts or similar if font not found
    if not pdf.unicode_font:
        # Simple character map for visualization if Unicode font is missing
        # (Very basic, better than nothing)
        ua_map = {'і':'i', 'ї':'i', 'є':'e', 'ґ':'g', 'І':'I', 'Ї':'I', 'Є':'E', 'Ґ':'G'}
        for k, v in ua_map.items():
            clean_report = clean_report.replace(k, v)
        # Note: Cyryllic in general will still be broken in standard FPDF fonts.
        # But this is a best-effort fallback.
    
    pdf.multi_cell(0, 6, clean_report)
    
    return pdf.output()
