import os, smtplib
from fpdf import FPDF
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def generate_legal_report(url, confidence, output_folder="reports"):
    os.makedirs(output_folder, exist_ok=True)
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial","B",20); pdf.set_text_color(180,0,0)
    pdf.cell(0,15,"DEEPFAKE CONTENT REMOVAL NOTICE",ln=True,align="C")
    pdf.set_draw_color(180,0,0); pdf.line(10,35,200,35); pdf.ln(10)
    pdf.set_font("Arial","",12); pdf.set_text_color(0,0,0)
    for label, value in [
        ("Report Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Flagged URL", url), ("AI Confidence", f"{confidence}%"),
        ("Status", "APPROVED FOR REMOVAL"), ("Issued By", "Deepfake Detection System"),
    ]:
        pdf.set_font("Arial","B",12); pdf.cell(60,10,f"{label}:",ln=False)
        pdf.set_font("Arial","",12); pdf.cell(0,10,str(value),ln=True)
    pdf.ln(5); pdf.set_font("Arial","B",12); pdf.cell(0,10,"Legal Notice:",ln=True)
    pdf.set_font("Arial","",11)
    pdf.multi_cell(0,8,"This notice is issued under authority for removal of detected deepfake "
                   "content. The URL has been flagged by AI detection. Removal required within 24h.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(output_folder, f"takedown_{ts}.pdf")
    pdf.output(out)
    print(f"Report → {out} ✅")
    return out

def send_takedown_email(to_email, url, report_path, from_email, password):
    msg = MIMEMultipart()
    msg["From"] = from_email; msg["To"] = to_email
    msg["Subject"] = "OFFICIAL DEEPFAKE CONTENT REMOVAL NOTICE"
    msg.attach(MIMEText(
        f"Platform Administrator,\n\nURL flagged for deepfake content:\n{url}\n\n"
        "Remove within 24 hours.\n\nDeepfake Detection Unit", "plain"))
    with open(report_path, "rb") as f:
        att = MIMEBase("application","octet-stream"); att.set_payload(f.read())
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", f"attachment; filename={os.path.basename(report_path)}")
        msg.attach(att)
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
        s.login(from_email, password); s.send_message(msg); s.quit()
        print("Email sent ✅")
    except Exception as e:
        print(f"Email error: {e}")
