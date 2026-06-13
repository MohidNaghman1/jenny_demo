"""
create_mock_data.py — Regenerate contracts.pdf and payments.db with complete demo data.
Run: python3 data/create_mock_data.py
Then: python3 ingestion/ingest.py
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))

# ── PDF ────────────────────────────────────────────────────────────────────────

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

PDF_PATH = os.path.join(BASE, "contracts.pdf")

def create_pdf():
    doc    = SimpleDocTemplate(PDF_PATH, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2.5*cm, rightMargin=2.5*cm)
    styles = getSampleStyleSheet()
    h1     = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=13, spaceAfter=6)
    h2     = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceAfter=4)
    body   = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=6, leading=14)
    story  = []

    def heading(text, style=h1):
        story.append(Paragraph(text, style))
        story.append(Spacer(1, 0.2*cm))

    def para(text):
        story.append(Paragraph(text, body))

    def space():
        story.append(Spacer(1, 0.4*cm))

    # ── CONTRACT 001 ───────────────────────────────────────────────────────────
    heading("SERVICE AGREEMENT — CONTRACT-001")
    para("Client: Acme Corp")
    para("Contract Period: January 1, 2024 – December 31, 2024")
    para("Service: Enterprise Software Support & Maintenance")
    space()

    heading("Section 1 — Payment Terms", h2)
    para("Invoices are due within 30 days of issue date. Acme Corp is billed monthly at $5,000 per invoice.")

    heading("Section 2 — Late Payment Penalties", h2)
    para("A late payment penalty of 3% per month applies to all overdue balances. Penalties accrue from the due date until full payment is received.")

    heading("Section 3 — Service Suspension", h2)
    para("Services will be suspended after 60 days of non-payment. Written notice will be provided 7 days prior to suspension. Reinstatement requires full payment of the outstanding balance plus a $200 reinstatement fee.")

    heading("Section 4 — Refund Policy", h2)
    para("Payments made in advance are eligible for a pro-rata refund within 30 days of written cancellation notice. No refunds are issued after services have been rendered for the applicable period. Disputed charges must be raised in writing within 14 days of the invoice date. Approved refunds are processed within 10 business days.")

    heading("Section 5 — Contract Termination", h2)
    para("Either party may terminate this agreement with 30 days written notice. Early termination by the client incurs a fee equal to one month's service charge.")

    space()

    # ── CONTRACT 002 ───────────────────────────────────────────────────────────
    heading("SERVICE AGREEMENT — CONTRACT-002")
    para("Client: BrightTech Ltd")
    para("Contract Period: March 1, 2024 – February 28, 2025")
    para("Service: Cloud Infrastructure Management")
    space()

    heading("Section 1 — Payment Terms", h2)
    para("Invoices are due within 45 days of issue. BrightTech Ltd is billed quarterly at $12,000 per quarter.")

    heading("Section 2 — Late Payment Penalties", h2)
    para("A late payment penalty of 2% per month applies to overdue balances after the 45-day grace period.")

    heading("Section 3 — Service Suspension", h2)
    para("Services will be immediately suspended after 45 days of non-payment. The client must provide written notice of payment intent before reinstatement. No reinstatement fee applies if payment is made within 7 days of suspension.")

    heading("Section 4 — Refund Policy", h2)
    para("BrightTech Ltd may request a refund for pre-paid services not yet rendered, within 21 days of cancellation. Refunds are calculated on a pro-rata basis. Setup fees and one-time charges are non-refundable. Refunds are processed within 14 business days of approval.")

    heading("Section 5 — Contract Termination", h2)
    para("Either party may terminate with 60 days written notice. No early termination fee applies after the first 6 months of the contract.")

    space()

    # ── CONTRACT 003 ───────────────────────────────────────────────────────────
    heading("SERVICE AGREEMENT — CONTRACT-003")
    para("Client: Nova Solutions")
    para("Contract Period: June 1, 2024 – May 31, 2025")
    para("Service: Data Analytics & Reporting Platform")
    space()

    heading("Section 1 — Payment Terms", h2)
    para("Invoices are due within 30 days of issue. Nova Solutions is billed monthly at $3,200 per invoice.")

    heading("Section 2 — Late Payment Penalties", h2)
    para("A late payment penalty of 2.5% per month applies to all overdue balances. Penalties begin accruing on the 31st day after the invoice date.")

    heading("Section 3 — Service Suspension", h2)
    para("Services will be suspended after 90 days of non-payment. A 14-day written notice is required before suspension is enacted. Reinstatement requires full payment of outstanding balance plus a $150 reinstatement fee and a signed payment commitment letter.")

    heading("Section 4 — Refund Policy", h2)
    para("Nova Solutions is entitled to a full refund for any prepaid month in which services were not delivered due to provider fault. Partial refunds for unused days are available upon cancellation with 30 days notice. No refunds are granted for months already in progress at time of cancellation. All refund requests must be submitted via written notice within 10 days of the cancellation date.")

    heading("Section 5 — Contract Termination", h2)
    para("Nova Solutions may terminate with 30 days notice after the initial 3-month lock-in period. Early termination within the lock-in period incurs a penalty of 2 months service charge.")

    doc.build(story)
    print(f"✅ contracts.pdf created at {PDF_PATH}")

# ── SQLite ─────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(BASE, "payments.db")

def create_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE payments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            amount     REAL NOT NULL,
            due_date   TEXT NOT NULL,
            status     TEXT NOT NULL
        )
    """)

    records = [
        ("Acme Corp",     5000.00, "2024-10-01", "overdue"),
        ("Acme Corp",     5000.00, "2024-11-01", "overdue"),
        ("BrightTech Ltd", 12000.00, "2024-09-01", "paid"),
        ("Nova Solutions", 3200.00, "2024-10-01", "overdue"),
        ("BrightTech Ltd", 12000.00, "2024-12-01", "paid"),
    ]

    cursor.executemany(
        "INSERT INTO payments (name, amount, due_date, status) VALUES (?, ?, ?, ?)",
        records
    )

    conn.commit()
    conn.close()
    print(f"✅ payments.db created at {DB_PATH} ({len(records)} records)")

if __name__ == "__main__":
    create_pdf()
    create_db()
    print("\n✅ Mock data ready. Now run: python3 ingestion/ingest.py")
