import os
import fitz  # PyMuPDF


def create_golden_agreement_pdf(output_path: str = "tests/fixtures/golden_agreement.pdf") -> str:
    """Generate a deterministic synthetic 2-page Indian residential agreement PDF for testing."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()

    # --- PAGE 1 ---
    page1 = doc.new_page(width=595, height=842)  # A4 size

    # Running header
    page1.insert_text((50, 35), "RESIDENTIAL LEAVE AND LICENSE AGREEMENT", fontsize=8, fontname="helv")

    # Document Heading
    page1.insert_text((180, 80), "RENT AGREEMENT", fontsize=16, fontname="helv")

    # Preamble
    preamble = (
        "This Leave and License Agreement is made and executed on this 1st day of October 2026, "
        "by and between Mr. Rajesh Kumar (Licensor) and Ms. Priya Sharma (Licensee)."
    )
    page1.insert_textbox(fitz.Rect(50, 110, 545, 170), preamble, fontsize=10, fontname="helv")

    # Clause 1 (Numbered)
    c1 = (
        "1. TERM OF AGREEMENT: The Licensor hereby grants to the Licensee the temporary permission to use "
        "and occupy the flat for an initial duration of 11 (eleven) months commencing from 1st October 2026."
    )
    page1.insert_textbox(fitz.Rect(50, 180, 545, 230), c1, fontsize=10, fontname="helv")

    # Clause 2 (Hierarchical)
    c2 = "2. FINANCIAL TERMS:"
    page1.insert_text((50, 250), c2, fontsize=11, fontname="helv")

    c2_1 = "2.1 Monthly Rent: The Licensee shall pay a sum of Rs. 35,000/- (Rupees Thirty Five Thousand) per month."
    page1.insert_textbox(fitz.Rect(50, 270, 545, 305), c2_1, fontsize=10, fontname="helv")

    c2_2 = (
        "2.2 Security Deposit: The Licensee has deposited an interest-free refundable deposit of Rs. 1,00,000/- with the Licensor."
    )
    page1.insert_textbox(fitz.Rect(50, 315, 545, 350), c2_2, fontsize=10, fontname="helv")

    # Subclauses (a) and (b)
    c2_a = "(a) The deposit shall be refunded within 30 days after peaceful handover of vacant possession."
    page1.insert_textbox(fitz.Rect(70, 360, 545, 390), c2_a, fontsize=10, fontname="helv")

    c2_b = "(b) Deductions shall only apply towards unpaid electricity bills and actual physical damage beyond normal wear."
    page1.insert_textbox(fitz.Rect(70, 400, 545, 430), c2_b, fontsize=10, fontname="helv")

    # Clause 3 Part 1 (Begins on Page 1, continues to Page 2)
    c3_part1 = (
        "3. MAINTENANCE AND REPAIRS: The Licensee shall maintain the interior of the premises in clean condition. "
        "All minor repairs such as tap washers, bulb replacements, and minor leakages up to Rs. 2,000 shall be borne by the Licensee."
    )
    page1.insert_textbox(fitz.Rect(50, 450, 545, 510), c3_part1, fontsize=10, fontname="helv")

    # Running footer
    page1.insert_text((270, 810), "Page 1 of 2", fontsize=9, fontname="helv")

    # --- PAGE 2 ---
    page2 = doc.new_page(width=595, height=842)

    # Running header
    page2.insert_text((50, 35), "RESIDENTIAL LEAVE AND LICENSE AGREEMENT", fontsize=8, fontname="helv")

    # Clause 3 Part 2 (Continuation from Page 1 without a new clause header)
    c3_part2 = (
        "Major structural repairs including seepage, external wall repairs, and electrical wiring failures "
        "shall remain the exclusive liability of the Licensor upon receiving written notice from the Licensee."
    )
    page2.insert_textbox(fitz.Rect(50, 70, 545, 120), c3_part2, fontsize=10, fontname="helv")

    # Clause 4 (Numbered)
    c4 = (
        "4. TERMINATION AND NOTICE: Either party may terminate this agreement prior to expiry by serving "
        "thirty (30) days written notice or payment of rent in lieu thereof."
    )
    page2.insert_textbox(fitz.Rect(50, 140, 545, 190), c4, fontsize=10, fontname="helv")

    # Running footer
    page2.insert_text((270, 810), "Page 2 of 2", fontsize=9, fontname="helv")

    doc.save(output_path)
    doc.close()
    return output_path


def create_sparse_scanned_pdf(output_path: str = "tests/fixtures/sparse_scanned.pdf") -> str:
    """Generate a single-page PDF with zero text (simulating an image scan)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Draw a line/rectangle so the page is not structurally empty, but has no text layer
    page.draw_rect(fitz.Rect(50, 50, 500, 700), color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    doc.save(output_path)
    doc.close()
    return output_path


if __name__ == "__main__":
    create_golden_agreement_pdf()
    create_sparse_scanned_pdf()
    print("Fixtures created successfully.")
