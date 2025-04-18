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

def prepare_gemini_input(prompt: str, text: str = None, image_paths: list = None) -> list:
    """Prepares the input list for the Gemini API."""
    content_parts = [prompt] # Start with the main prompt

    if text:
        content_parts.append("\n\n--- PDF Text Content ---\n")
        content_parts.append(text)

    if image_paths:
        content_parts.append("\n\n--- PDF Page Images ---\n")
        print(f"Loading {len(image_paths)} images for Gemini...")
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                # Optional: Resize large images to avoid hitting size limits,
                # but be mindful of losing detail needed for OCR/analysis.
                # max_size = (1024, 1024)
                # img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Convert image to bytes if needed or pass PIL object directly
                # Depending on the specific API version/library behavior
                # Passing PIL object is generally preferred with google-generativeai
                content_parts.append(img)
                print(f"Added image: {img_path}")
            except Exception as e:
                print(f"Warning: Could not load or add image {img_path}: {e}")
        print("Image loading complete.")

    return content_parts

def send_to_gemini(content_parts: list) -> str:
    """Sends the prepared content to the Gemini API and returns the response."""
    try:
        start_time = time.time()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=content_parts,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=1024)
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

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text/screenshots from PDF and analyze with Gemini.")
    parser.add_argument("pdf_file", help="Path to the input PDF file.")
    parser.add_argument(
        "--mode",
        choices=["text", "screenshots", "both"],
        required=True,
        help="Data source to send to Gemini: 'text', 'screenshots', or 'both'."
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
    if not extracted_text and not screenshot_paths:
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
    gemini_prompt = """
Analyze the provided content (text excerpts and/or page images from a PDF document, likely a scientific paper, patent, or technical sheet). Your goal is to identify chemical substances mentioned.

Follow these instructions carefully:

1.  **Identify Chemical Substances:** Find all mentions of specific chemical compounds, ingredients, or substances. Filter out not relevant one, for example try to find in the introduction of the report the substances that the specific report is focusing on, usually they are specified in the introduction as a list of substances.
2.  **Recognize Synonyms & Abbreviations:** Understand that the same substance might be referred to by different names (e.g., Sodium Chloride, NaCl, salt, saline solution) or abbreviations (e.g., H2O2 for Hydrogen Peroxide, EtOH for Ethanol). Group these under a primary or common standardized name where possible. If an abbreviation's meaning isn't explicitly defined but is clear from context (common chemical abbreviations), include it.
3.  **Extract Concentration/Range:** For each identified substance, search the text and any visible tables in the images for concentration information. Look for percentages (e.g., 5%, 0.1% w/w, 1-10% v/v), ranges (e.g., "between 0.5% and 2%", "up to 15%"), or descriptive terms (e.g., "trace amount", "major component"). Report the found range or value precisely as stated. If no concentration is found for a substance, state "Not specified".
4.  **Determine Use Case/Function:** Based on the context where the substance is mentioned, determine its described purpose or application. Examples include: 'active ingredient', 'preservative', 'emulsifier', 'solvent', 'pH adjuster', 'fragrance component', 'thickener', 'rinse-off product context', 'leave-on formulation context', 'catalyst', 'reactant', etc. If the context is unclear or no specific function is mentioned, state "Not specified". Look for mentions in formulation tables, experimental descriptions, or introductory/concluding remarks about components.
5.  **Order by Importance:** List the substances in descending order of their apparent importance or prominence within the document. Consider factors like:
    *   Frequency of mention.
    *   Whether it's listed as a primary active ingredient or key component.
    *   Detailed discussion of its properties or role.
    *   Presence in example formulations or core experimental sections.
    *   Substances mentioned only briefly or in passing should be lower on the list.
6.  **Output Format:** Present the results STRICTLY as a Markdown table with the following columns: `Substance Name` | `Concentration Range` | `Use Case`. Do NOT include any introductory text before the table or concluding remarks after it. Just output the table.
7.  **Exclusions:** Generally exclude very common, non-functional substances like 'water' or 'air' unless they are specifically discussed in a functional role (e.g., 'water-in-oil emulsion', 'solvent system: water/ethanol'). Focus on the functional or characterized chemicals.

Example Table Row:
| Substance Name      | Concentration Range | Use Case                  |
|---------------------|---------------------|---------------------------|
| Sodium Hyaluronate  | 0.1% - 1.5% w/w     | Moisturizer, Active       |
| Phenoxyethanol      | up to 1%            | Preservative              |
| Glycerin            | 2% - 5%             | Humectant, Solvent        |
| Citric Acid         | Not specified       | pH Adjuster               |
| Titanium Dioxide (TiO2)| 10%              | UV Filter (Sunscreen)     |

Now, analyze the provided PDF content and generate the table. Output ONLY the table, with no additional text, explanations, or whitespace before or after the table.
"""

    content_parts = prepare_gemini_input(gemini_prompt, extracted_text, screenshot_paths)
    gemini_response = send_to_gemini(content_parts)

    # Clean the response to ensure it's only a table
    def clean_table_response(response: str) -> str:
        # Find the start of the table (first |)
        # table_start = response.find('|')
        # if table_start == -1:
        #     return "Error: No table found in response"
        
        # # Find the end of the table (last |)
        # table_end = response.rfind('|')
        # if table_end == -1:
        #     return "Error: No table found in response"
        
        # Extract the table and clean it
        table = response.strip()
        # Remove any empty lines
        lines = [line for line in table.split('\n') if line.strip()]
        return '\n'.join(lines)

    # Clean the response and save it
    cleaned_response = clean_table_response(gemini_response)
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_response)
    print(f"Analysis results saved to {text_output_path}")

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