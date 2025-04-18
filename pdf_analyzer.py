from google import genai
from google.genai import types
import fitz  # PyMuPDF
import os
import argparse
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import io
import time

from pdf_report import beautify_report
from prompts import get_initial_analysis_prompt, get_detailed_analysis_prompt

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file or environment variables.")

# Initialize the client
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash-preview-04-17"

# Use gemini-pro if you ONLY ever plan to send text
# TEXT_MODEL_NAME = "gemini-pro"

# --- Core Functions ---

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all text content from a PDF file."""
    full_text = ""
    try:
        doc = fitz.open(pdf_path)
        print(f"Extracting text from {doc.page_count} pages...")
        for i, page in enumerate(doc.pages()):
            text = page.get_text("text")
            if text:
                full_text += f"\n--- Page {i+1} ---\n{text}"
        doc.close()
        print("Text extraction complete.")
        return full_text.strip()
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

def take_screenshots_of_pdf(pdf_path: str, output_folder: str, dpi: int = 150) -> list:
    """Takes screenshots of each page of a PDF and saves them."""
    image_paths = []
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    try:
        doc = fitz.open(pdf_path)
        print(f"Taking screenshots of {doc.page_count} pages (DPI: {dpi})...")
        for i, page in enumerate(doc.pages()):
            pix = page.get_pixmap(dpi=dpi)
            img_path = Path(output_folder) / f"page_{i+1:03d}.png"
            pix.save(str(img_path))
            image_paths.append(str(img_path))
            print(f"Saved screenshot: {img_path}")
        doc.close()
        print(f"Screenshots saved to {output_folder}")
        return image_paths
    except Exception as e:
        print(f"Error taking screenshots from {pdf_path}: {e}")
        return []

def prepare_gemini_input(prompt: str, text: str = None, image_paths: list = None, pdf_path: str = None) -> list:
    """Prepares the input list for the Gemini API."""
    content_parts = []
    
    # Add the prompt as the first part
    content_parts.append(types.Part.from_text(text=prompt))
    
    if pdf_path:
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            content_parts.append(types.Part.from_bytes(
                data=pdf_bytes,
                mime_type='application/pdf'
            ))
            print(f"Added PDF file: {pdf_path}")
        except Exception as e:
            print(f"Warning: Could not load or add PDF file {pdf_path}: {e}")
    
    if text:
        content_parts.append(types.Part.from_text(text="\n\n--- PDF Text Content ---\n"))
        content_parts.append(types.Part.from_text(text=text))

    if image_paths:
        content_parts.append(types.Part.from_text(text="\n\n--- PDF Page Images ---\n"))
        print(f"Loading {len(image_paths)} images for Gemini...")
        for img_path in image_paths:
            try:
                with open(img_path, 'rb') as f:
                    img_bytes = f.read()
                content_parts.append(types.Part.from_bytes(
                    data=img_bytes,
                    mime_type='image/png'
                ))
                print(f"Added image: {img_path}")
            except Exception as e:
                print(f"Warning: Could not load or add image {img_path}: {e}")
        print("Image loading complete.")

    # Create a single content with all parts
    content = types.Content(
        role='user',
        parts=content_parts
    )
    
    return [content]

def send_to_gemini(content_parts: list) -> str:
    """Sends the prepared content to the Gemini API and returns the response."""
    try:
        start_time = time.time()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=content_parts,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=4024)
            )
        )
        end_time = time.time()
        print(f"Gemini processing took {end_time - start_time:.2f} seconds.")

        # Calculate token usage and cost
        if hasattr(response, 'usage_metadata'):
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
            total_tokens = input_tokens + output_tokens
            
            # Calculate costs (per 1M tokens)
            input_cost = (input_tokens / 1_000_000) * 0.15  # $0.15 per 1M input tokens
            output_cost = (output_tokens / 1_000_000) * 3.50  # $3.50 per 1M output tokens
            total_cost = input_cost + output_cost
            
            print("\n--- API Usage and Cost Estimation ---")
            print(f"Input tokens: {input_tokens:,}")
            print(f"Output tokens: {output_tokens:,}")
            print(f"Total tokens: {total_tokens:,}")
            print(f"Estimated cost: ${total_cost:.6f}")
            print(f"  - Input cost: ${input_cost:.6f}")
            print(f"  - Output cost: ${output_cost:.6f}")
            print("------------------------------------")

        return response.text

    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        return f"Error: Failed to get response from Gemini. {e}"

def clean_table_response(response: str) -> str:
    """Cleans the response to ensure it's only a table."""
    # Extract the table and clean it
    table = response.strip()
    # Remove any empty lines
    lines = [line for line in table.split('\n') if line.strip()]
    return '\n'.join(lines)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text/screenshots from PDF and analyze with Gemini.")
    parser.add_argument("pdf_file", help="Path to the input PDF file.")
    parser.add_argument(
        "--mode",
        choices=["text", "screenshots", "both", "direct"],
        required=True,
        help="Data source to send to Gemini: 'text', 'screenshots', 'both', or 'direct' (send PDF directly)."
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Resolution (DPI) for screenshots (default: 150)."
    )
    parser.add_argument(
        "--skip_gemini",
        action="store_true",
        help="Only extract text/screenshots, do not send to Gemini."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete screenshot files after sending to Gemini (use with caution)."
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.is_file():
        print(f"Error: PDF file not found at {args.pdf_file}")
        exit(1)

    # Create output directory structure
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate output filenames based on input file and mode
    base_name = pdf_path.stem
    screenshots_dir = output_dir / f"{base_name}_screenshots"
    text_output_path = output_dir / f"{base_name}_{args.mode}_analysis.md"
    detailed_output_path = output_dir / f"{base_name}_{args.mode}_detailed_analysis.md"

    # --- Step 1 & 2: Extract Text / Take Screenshots ---
    extracted_text = None
    screenshot_paths = []

    if args.mode in ["text", "both"]:
        extracted_text = extract_text_from_pdf(str(pdf_path))
        if not extracted_text:
            print("Warning: No text could be extracted.")

    if args.mode in ["screenshots", "both"]:
        screenshot_paths = take_screenshots_of_pdf(str(pdf_path), str(screenshots_dir), args.dpi)
        if not screenshot_paths:
            print("Warning: No screenshots could be generated.")

    # --- Check if any data was generated ---
    if not extracted_text and not screenshot_paths and args.mode != "direct":
        print("Error: No text extracted and no screenshots generated. Cannot proceed.")
        exit(1)

    if args.skip_gemini:
        print("Skipping Gemini analysis as requested.")
        # Save extracted text to a file
        if extracted_text:
            with open(text_output_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            print(f"Extracted text saved to {text_output_path}")
        exit(0)

    # --- Step 3: Prepare Input and Send to Gemini ---
    # First analysis
    content_parts = prepare_gemini_input(
        get_initial_analysis_prompt(), 
        extracted_text if args.mode != "direct" else None, 
        screenshot_paths if args.mode != "direct" else None,
        str(pdf_path) if args.mode == "direct" else None
    )
    gemini_response = send_to_gemini(content_parts)
    cleaned_response = clean_table_response(gemini_response)
    
    # Save initial analysis
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_response)
    print(f"Initial analysis results saved to {text_output_path}")
    
    # Generate initial PDF report
    initial_report_path = beautify_report(cleaned_response, str(pdf_path))
    print(f"Initial professional report generated: {initial_report_path}")

    # Second analysis (detailed)
    content_parts = prepare_gemini_input(
        get_detailed_analysis_prompt(), 
        extracted_text if args.mode != "direct" else None, 
        screenshot_paths if args.mode != "direct" else None,
        str(pdf_path) if args.mode == "direct" else None
    )
    detailed_response = send_to_gemini(content_parts)
    cleaned_detailed_response = clean_table_response(detailed_response)
    
    # Save detailed analysis
    with open(detailed_output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_detailed_response)
    print(f"Detailed analysis results saved to {detailed_output_path}")
    
    # Generate detailed PDF report
    detailed_report_path = beautify_report(cleaned_detailed_response, str(pdf_path))
    print(f"Detailed professional report generated: {detailed_report_path}")

    # Cleanup screenshots if requested
    if args.cleanup and screenshot_paths:
        print("Cleaning up screenshot files...")
        for img_path in screenshot_paths:
            try:
                os.remove(img_path)
            except Exception as e:
                print(f"Warning: Could not delete {img_path}: {e}")
        try:
            os.rmdir(screenshots_dir)
        except Exception as e:
            print(f"Warning: Could not remove directory {screenshots_dir}: {e}")

    print("\nScript finished.") 