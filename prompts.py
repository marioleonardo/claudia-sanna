from typing import List

def get_initial_analysis_prompt() -> str:
    return """
Analyze the provided content (text excerpts and/or page images from a PDF document, likely a scientific paper, patent, or technical sheet). Your goal is to identify chemical substances mentioned.

Follow these instructions carefully:

1.  **Identify Chemical Substances:** Find chemical compounds, ingredients, or substances. Filter out not relevant one, for example try to find in the introduction of the report the substances that the specific report is focusing on, usually they are specified in the introduction as a list of substances. IMPORTANT: Do not include any substances that are not mentioned in the introduction of the report.
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

def get_detailed_analysis_prompt() -> str:
    return """
Analyze the provided content (text excerpts and/or page images from a PDF document) to create a detailed analysis of chemical substances and their specific use cases.

Follow these instructions carefully:

1. **Identify All Use Cases:** For each chemical substance identified in the document, list ALL distinct use cases mentioned, even if they appear in different contexts or sections.
2. **Match Concentration Ranges:** For each use case, identify the specific concentration range or amount mentioned in that context.
3. **Create Detailed Entries:** Create a separate table entry for each unique combination of substance, use case, and concentration range.
4. **Include Context:** If a substance is mentioned with different concentration ranges for different use cases, create separate entries for each combination.
5. **Be Specific:** If a substance has multiple use cases with different concentration ranges, list each combination separately.

Output Format:
Present the results as a Markdown table with the following columns:
`Substance Name` | `Concentration Range` | `Use Case`

Example:
If a document mentions:
- Substance A used as a preservative at 0.5-1%
- Substance A used as a solvent at 2-5%
- Substance B used as a thickener at 0.1-0.3%

The table should look like:
| Substance Name | Concentration Range | Use Case     |
|----------------|---------------------|--------------|
| Substance A    | 0.5% - 1%          | Preservative |
| Substance A    | 2% - 5%            | Solvent      |
| Substance B    | 0.1% - 0.3%        | Thickener    |

Now, analyze the provided PDF content and generate the detailed table. Output ONLY the table, with no additional text or explanations.
""" 