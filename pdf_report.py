from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from fpdf_table import PDFTable, Align

def beautify_report(table_content: str, pdf_path: str, output_dir: str = "output") -> str:
    """
    Creates a beautiful PDF report from the analysis results using fpdf_table.
    
    Args:
        table_content: The markdown table content from Gemini
        pdf_path: Path to the original PDF file
        output_dir: Directory to save the report
        
    Returns:
        Path to the generated report PDF
    """
    # Create report directory if it doesn't exist
    report_dir = Path(output_dir) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate report filename with original PDF name
    original_pdf_name = Path(pdf_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{original_pdf_name}_analysis_report_{timestamp}.pdf"
    report_path = report_dir / report_filename
    
    # Parse the markdown table
    lines = table_content.strip().split('\n')
    headers = [h.strip() for h in lines[0].split('|')[1:-1]]
    data = []
    for line in lines[2:]:  # Skip header and separator lines
        if line.strip():
            row = [cell.strip() for cell in line.split('|')[1:-1]]
            data.append(row)
    
    # Initialize PDFTable
    pdf = PDFTable()
    pdf.add_page()
    
    # Add title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Chemical Analysis Report", ln=True, align="C")
    pdf.ln(5)
    
    # Add timestamp
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", ln=True, align="C")
    pdf.ln(5)
    
    # Add source file information
    pdf.cell(0, 10, f"Source Document: {Path(pdf_path).name}", ln=True, align="C")
    pdf.ln(10)
    
    # Set up table styles
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(100, 100, 100)  # Grey background for header
    pdf.set_text_color(255, 255, 255)  # White text for header
    
    # Calculate available width for the table
    available_width = pdf.w - 2 * pdf.l_margin
    
    # Add table header with proportional column widths
    col_widths = [
        available_width * 0.3,  # Substance Name (30%)
        available_width * 0.2,  # Concentration Range (20%)
        available_width * 0.5   # Use Case (50%)
    ]
    
    # Ensure the total width doesn't exceed available width
    total_width = sum(col_widths)
    if total_width > available_width:
        scale_factor = available_width / total_width
        col_widths = [w * scale_factor for w in col_widths]
    
    pdf.table_header(headers, col_widths, align=Align.L)
    
    # Set up data row styles
    pdf.set_fill_color(245, 245, 220)  # Beige background for data
    pdf.set_text_color(0, 0, 0)  # Black text for data
    pdf.set_font("Helvetica", "", 9)
    
    # Add data rows with alternating background colors
    for i, row in enumerate(data):
        # Set background color for alternating rows
        if i % 2 == 0:
            pdf.set_fill_color(245, 245, 220)  # Light beige
        else:
            pdf.set_fill_color(255, 255, 255)  # White
        
        # Add row with responsive option
        pdf.table_row(
            row,
            col_widths,
            option='responsive'
        )
    
    # Add footer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 10, "Generated using Gemini AI Analysis Tool", ln=True, align="C")
    
    # Save the PDF
    pdf.output(str(report_path))
    
    print(f"Report generated: {report_path}")
    return str(report_path) 