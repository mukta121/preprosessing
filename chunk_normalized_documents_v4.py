# -*- coding: utf-8 -*-
"""
chunk_normalized_documents_v3.py

INPUT
-----
normalized_documents/
    <document_id>.normalized.json

cleaned_normalized_documents/
    <document_id>.cleaned.normalized.md

OUTPUT
------
chunked_files/
    sob_chunks.jsonl

FINAL JSONL CONTAINS TWO CHUNK TYPES
------------------------------------
1. TEXT CHUNKS
   - text/prose
   - section hierarchy
   - can contain [TABLE: <table_id>] placeholder

2. TABLE CHUNKS
   - normalized Markdown table rows
   - repeated header
   - preceding/following context
   - linked using table_id
   - only tables still referenced in cleaned Markdown are chunked

DOCUMENT / CHUNK ID
-------------------
document_id:
    extracted from ID INSIDE document

chunk_id:
    <document_id>_chunk_0001
    <document_id>_chunk_0002
    ...

METADATA ON BOTH TEXT + TABLE CHUNKS
------------------------------------
- document_id
- chunk_id
- plan_name
- state
- effective_date
- form_number
- product_type
- plan_variant
- source_file
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple


# ============================================================
# 1. INPUT / OUTPUT
# ============================================================

NORMALIZED_FOLDER = Path(
    r"C:\Users\mm7453\OneDrive - Point32Health\p32_workplace\adhoc\SOBs\normalized_documents"
)

CLEANED_FOLDER = (
    NORMALIZED_FOLDER.parent
    / "cleaned_normalized_documents"
)

OUTPUT_FOLDER = (
    NORMALIZED_FOLDER.parent
    / "chunked_files"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_FOLDER
    / "sob_chunks.jsonl"
)


# ============================================================
# 2. CHUNKING CONFIGURATION
# ============================================================

CHUNK_SIZE = 5000
CHUNK_OVERLAP = 500
MIN_CHUNK = 100

TABLE_CHUNK_SIZE = 5000


# ============================================================
# 3. STATES
# ============================================================

STATE_PATTERNS = {
    "MASSACHUSETTS":
        "Massachusetts",

    "MAINE":
        "Maine",

    "NEW HAMPSHIRE":
        "New Hampshire",

    "RHODE ISLAND":
        "Rhode Island",

    "CONNECTICUT":
        "Connecticut",

    "VERMONT":
        "Vermont",

    "NEW YORK":
        "New York",
}


# ============================================================
# 4. PRODUCT TYPE RULES
# ============================================================

PRODUCT_PATTERNS = [

    (
        "Pediatric Dental",
        [
            r"\bPEDIATRIC\s+DENTAL\s+RIDER\b",
            r"\bPEDIATRIC\s+DENTAL\b",
        ]
    ),

    (
        "Dental",
        [
            r"\bDENTAL\s+RIDER\b",
            r"\bPREVENTIVE\s+DENTAL\b",
            r"\bDENTAL\s+PLAN\b",
        ]
    ),

    (
        "Vision",
        [
            r"\bVISIONCARE\b",
            r"\bVISION\s+CARE\b",
            r"\bVISION\s+BENEFIT\b",
        ]
    ),

    (
        "D-SNP",
        [
            r"\bD[\s-]?SNP\b",
            r"\bDUAL\s+ELIGIBLE\s+SPECIAL\s+NEEDS\b",
        ]
    ),

    (
        "SCO",
        [
            r"\bSENIOR\s+CARE\s+OPTIONS\b",
            r"\bSCO\b",
        ]
    ),

    (
        "USFHP",
        [
            r"\bUSFHP\b",
            r"\bUNIFORMED\s+SERVICES\s+FAMILY\s+HEALTH\s+PLAN\b",
        ]
    ),

    (
        "Medicare Enhance",
        [
            r"\bMEDICARE\s+ENHANCE\b",
        ]
    ),

    (
        "Medicare Advantage PPO",
        [
            r"\bMEDICARE\s+PREFERRED\s+PPO\b",
            r"\bMEDICARE\s+ADVANTAGE\s+PPO\b",
        ]
    ),

    (
        "Medicare Advantage HMO",
        [
            r"\bMEDICARE\s+PREFERRED\s+HMO\b",
            r"\bMEDICARE\s+ADVANTAGE\s+HMO\b",
        ]
    ),

    (
        "Medicare",
        [
            r"\bMEDICARE\b",
        ]
    ),

    (
        "EPO",
        [
            r"\bEPO\b",
        ]
    ),

    (
        "PPO",
        [
            r"\bPPO\b",
        ]
    ),

    (
        "POS",
        [
            r"\bPOS\b",
            r"\bPOINT[\s-]+OF[\s-]+SERVICE\b",
            r"\bDPO\s+PLAN\s*\(\s*POS\s*\)",
        ]
    ),

    (
        "DPO",
        [
            r"\bDPO\b",
        ]
    ),

    (
        "GEO",
        [
            r"\bGEO\b",
        ]
    ),

    (
        "HMO",
        [
            r"\bHMO\b",
        ]
    ),
]


# ============================================================
# 5. PLAN VARIANT RULES
# ============================================================

PLAN_VARIANT_PATTERNS = {

    "HSA": [
        r"\bHSA\b"
    ],

    "CDHP": [
        r"\bCDHP\b"
    ],

    "Flex Plus": [
        r"\bFLEX\s+PLUS\b"
    ],

    "Flex": [
        r"\bFLEX\b"
    ],

    "ChoiceNet": [
        r"\bCHOICENET\b"
    ],

    "Choice Plus": [
        r"\bCHOICE\s+PLUS\b"
    ],

    "National Access": [
        r"\bNATIONAL\s+ACCESS\b"
    ],

    "Tiered": [
        r"\bTIERED\b"
    ],

    "Quality": [
        r"\bQUALITY\b"
    ],

    "Focus Network": [
        r"\bFOCUS\s+NETWORK\b"
    ],

    "Network Premier": [
        r"\bNETWORK\s+PREMIER\b"
    ],

    "Domestic and Community": [
        r"\bDOMESTIC\s+AND\s+COMMUNITY\b"
    ],

    "Out of Area": [
        r"\bOUT\s+OF\s+AREA\b"
    ],

    "Explorer": [
        r"\bEXPLORER\b"
    ],

    "Best Buy": [
        r"\bBEST\s+BUY\b"
    ],

    "Maine's Choice Plus": [
        r"\bMAINE['’]S\s+CHOICE\s+PLUS\b"
    ],

    "Littleton Options": [
        r"\bLITTLETON\s+OPTIONS\b"
    ],

    "myClassic": [
        r"\bMYCLASSIC\b"
    ],

    "myAdvantage": [
        r"\bMYADVANTAGE\b"
    ],

    "ElevateHealth": [
        r"\bELEVATEHEALTH\b"
    ],

    "BIDMC Select": [
        r"\bBIDMC\s*[-–]?\s*SELECT\b"
    ],

    "Local Select": [
        r"\bLOCAL\s+\d+\s+SELECT\b"
    ],

    "BILH": [
        r"\bBILH\b"
    ],

    "Bronze": [
        r"\bBRONZE\b"
    ],

    "Silver": [
        r"\bSILVER\b"
    ],

    "Gold": [
        r"\bGOLD\b"
    ],

    "Platinum": [
        r"\bPLATINUM\b"
    ],
}


# ============================================================
# 6. NORMALIZE TEXT
# ============================================================

def normalize_whitespace(
    text: str
) -> str:

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    text = text.replace(
        "\t",
        " "
    )

    text = re.sub(
        r"[ \t]+$",
        "",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# 7. INTERNAL DOCUMENT ID
# ============================================================

def extract_document_id(
    text: str
) -> Optional[str]:

    patterns = [

        (
            r'PageHeader\s*=\s*["\']?'
            r'.*?\bID\s*:\s*'
            r'([A-Z]{2}\d+(?:_[A-Z0-9]+)?)'
        ),

        (
            r'(?im)^\s*[.\-]?\s*'
            r'ID\s*:\s*'
            r'([A-Z]{2}\d+(?:_[A-Z0-9]+)?)\b'
        ),

        (
            r'\bID\s*:\s*'
            r'([A-Z]{2}\d+(?:_[A-Z0-9]+)?)\b'
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            return (
                match.group(1)
                .upper()
                .strip()
            )

    return None


# ============================================================
# 8. EFFECTIVE DATE
# ============================================================

def extract_effective_date(
    text: str
) -> Optional[str]:

    patterns = [

        (
            r'(?im)^\s*'
            r'EFFECTIVE\s+DATE\s*:\s*'
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ),

        (
            r'(?im)^\s*'
            r'DATE\s*:\s*'
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ),

        (
            r'\bEFFECTIVE\s+DATE\s*:\s*'
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            return match.group(1)

    return None


# ============================================================
# 9. FORM NUMBER
# ============================================================

def extract_form_number(
    text: str
) -> Optional[str]:

    pattern = (
        r'(?im)^\s*'
        r'FORM\s*'
        r'(?:NUMBER|NO\.?|#)?'
        r'\s*[:#\-]?\s*'
        r'([A-Z0-9._\-/]{3,})'
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return None


# ============================================================
# 10. STATE
# ============================================================

def extract_state(
    text: str
) -> Optional[str]:

    top_text = (
        text[:6000]
        .upper()
    )

    for (
        state_upper,
        normalized_state
    ) in STATE_PATTERNS.items():

        if re.search(
            rf"\b{re.escape(state_upper)}\b",
            top_text
        ):
            return normalized_state

    return None


# ============================================================
# 11. PLAN NAME HELPERS
# ============================================================

def remove_markdown_markup(
    line: str
) -> str:

    line = line.strip()

    line = re.sub(
        r"^#{1,6}\s*",
        "",
        line
    )

    line = re.sub(
        r"<!--.*?-->",
        "",
        line
    )

    return line.strip()


def clean_plan_name(
    plan_name: str
) -> Optional[str]:

    if not plan_name:
        return None

    plan_name = normalize_whitespace(
        plan_name.replace(
            "\n",
            " "
        )
    )

    for state in STATE_PATTERNS:

        plan_name = re.sub(
            rf"\b{re.escape(state)}\b\s*$",
            "",
            plan_name,
            flags=re.IGNORECASE
        ).strip()

    return (
        plan_name
        if plan_name
        else None
    )


# ============================================================
# 12. PLAN NAME
# ============================================================

def extract_plan_name(
    text: str
) -> Optional[str]:

    lines = [
        remove_markdown_markup(
            line
        )
        for line in text.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    useful = []

    for line in lines[:50]:

        upper = line.upper()

        if upper in {
            "DOCUMENT TEXT",
            "EXTRACTED TABLES",
        }:
            continue

        if re.search(
            r"^\s*\.?\s*ID\s*:",
            upper
        ):
            continue

        if upper.startswith(
            "DATE:"
        ):
            continue

        if upper.startswith(
            "EFFECTIVE DATE:"
        ):
            continue

        if upper.startswith(
            "FORM "
        ):
            continue

        if "PAGEHEADER=" in upper:
            continue

        if "PAGEFOOTER=" in upper:
            continue

        if upper == "X":
            continue

        useful.append(
            line
        )

    if not useful:
        return None

    # --------------------------------------------
    # Schedule of Benefits
    # --------------------------------------------

    for index, line in enumerate(
        useful
    ):

        if (
            "SCHEDULE OF BENEFITS"
            not in line.upper()
        ):
            continue

        after = re.sub(
            r"(?i)^.*?"
            r"SCHEDULE\s+OF\s+BENEFITS\s*",
            "",
            line
        ).strip()

        candidates = []

        if after:
            candidates.append(
                after
            )

        for next_line in useful[
            index + 1:
            index + 7
        ]:

            upper = next_line.upper()

            stop_phrases = [
                "PLEASE NOTE",
                "IMPORTANT INFORMATION",
                "THIS SCHEDULE",
                "THIS PLAN",
                "SERVICES ARE",
                "COVERAGE UNDER",
                "THE FOLLOWING",
                "YOUR BENEFITS",
                "BENEFITS ARE",
            ]

            if any(
                upper.startswith(
                    phrase
                )
                for phrase
                in stop_phrases
            ):
                break

            candidates.append(
                next_line
            )

        candidate = (
            " ".join(
                candidates
            )
            .strip()
        )

        if candidate:

            return clean_plan_name(
                candidate
            )

    # --------------------------------------------
    # Special document fallback
    # --------------------------------------------

    special_pattern = re.compile(
        r"(?i)\b("
        r"PEDIATRIC\s+DENTAL|"
        r"DENTAL\s+RIDER|"
        r"VISIONCARE|"
        r"MEDICARE\s+ENHANCE|"
        r"SENIOR\s+CARE\s+OPTIONS|"
        r"USFHP"
        r")\b"
    )

    for index, line in enumerate(
        useful[:15]
    ):

        if special_pattern.search(
            line
        ):

            candidate = (
                " ".join(
                    useful[
                        index:
                        index + 4
                    ]
                )
            )

            return clean_plan_name(
                candidate
            )

    return clean_plan_name(
        useful[0]
    )


# ============================================================
# 13. PRODUCT TYPE
# ============================================================

def extract_product_type(
    text: str,
    plan_name: Optional[str] = None
) -> str:

    searchable = (
        (plan_name or "")
        + "\n"
        + text[:6000]
    ).upper()

    for (
        product_type,
        patterns
    ) in PRODUCT_PATTERNS:

        for pattern in patterns:

            if re.search(
                pattern,
                searchable,
                flags=re.IGNORECASE
            ):

                return product_type

    return "UNKNOWN"


# ============================================================
# 14. PLAN VARIANT
# ============================================================

def extract_plan_variants(
    text: str,
    plan_name: Optional[str]
) -> List[str]:

    searchable = (
        (plan_name or "")
        + "\n"
        + text[:4000]
    ).upper()

    found = []

    for (
        variant,
        patterns
    ) in PLAN_VARIANT_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                searchable,
                flags=re.IGNORECASE
            ):

                if variant not in found:
                    found.append(
                        variant
                    )

                break

    if (
        "Flex Plus" in found
        and
        "Flex" in found
    ):
        found.remove(
            "Flex"
        )

    return found


# ============================================================
# 15. EXTRACT DOCUMENT METADATA
# ============================================================

def extract_document_metadata(
    text: str,
    source_file: str
) -> Dict:

    document_id = (
        extract_document_id(
            text
        )
    )

    if not document_id:

        print(
            f"WARNING: internal ID "
            f"not found in "
            f"{source_file}"
        )

        document_id = (
            source_file
            .replace(
                ".cleaned.normalized.md",
                ""
            )
        )

    plan_name = (
        extract_plan_name(
            text
        )
    )

    state = (
        extract_state(
            text
        )
    )

    effective_date = (
        extract_effective_date(
            text
        )
    )

    form_number = (
        extract_form_number(
            text
        )
    )

    product_type = (
        extract_product_type(
            text=text,
            plan_name=plan_name
        )
    )

    variants = (
        extract_plan_variants(
            text=text,
            plan_name=plan_name
        )
    )

    plan_variant = (
        " | ".join(
            variants
        )
        if variants
        else None
    )

    return {
        "document_id":
            document_id,

        "plan_name":
            plan_name,

        "state":
            state,

        "effective_date":
            effective_date,

        "form_number":
            form_number,

        "product_type":
            product_type,

        "plan_variant":
            plan_variant,

        "source_file":
            source_file,
    }


# ============================================================
# 16. HIERARCHICAL SECTION PARSER
# ============================================================

def split_into_sections(
    text: str
) -> List[Dict]:

    lines = text.splitlines()

    sections = []

    hierarchy = {
        1: None,
        2: None,
        3: None,
        4: None,
    }

    current = None

    heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$"
    )

    for line in lines:

        heading = heading_pattern.match(
            line
        )

        if heading:

            level = len(
                heading.group(1)
            )

            title = (
                heading.group(2)
                .strip()
            )

            if current:

                section_text = (
                    "\n".join(
                        current["content"]
                    )
                    .strip()
                )

                if section_text:

                    current["text"] = (
                        section_text
                    )

                    del current[
                        "content"
                    ]

                    sections.append(
                        current
                    )

            if level <= 4:

                hierarchy[
                    level
                ] = title

                for lower_level in range(
                    level + 1,
                    5
                ):
                    hierarchy[
                        lower_level
                    ] = None

            current = {
                "section":
                    title,

                "level":
                    level,

                "h1":
                    hierarchy[1],

                "h2":
                    hierarchy[2],

                "h3":
                    hierarchy[3],

                "h4":
                    hierarchy[4],

                "content": [
                    line
                ],
            }

        else:

            if current is None:

                current = {
                    "section":
                        "Document Header",

                    "level":
                        0,

                    "h1":
                        None,

                    "h2":
                        None,

                    "h3":
                        None,

                    "h4":
                        None,

                    "content":
                        [],
                }

            current[
                "content"
            ].append(
                line
            )

    if current:

        section_text = (
            "\n".join(
                current["content"]
            )
            .strip()
        )

        if section_text:

            current[
                "text"
            ] = section_text

            del current[
                "content"
            ]

            sections.append(
                current
            )

    return sections


# ============================================================
# 17. SECTION PATH
# ============================================================

def build_section_path(
    section: Dict
) -> str:

    parts = []

    for key in [
        "h1",
        "h2",
        "h3",
        "h4",
    ]:

        value = section.get(
            key
        )

        if (
            value
            and
            value not in parts
        ):

            parts.append(
                value
            )

    if not parts:

        section_name = (
            section.get(
                "section"
            )
        )

        if section_name:
            parts.append(
                section_name
            )

    return " > ".join(
        parts
    )


# ============================================================
# 18. OVERLAP
# ============================================================

def get_overlap_text(
    previous_text: str,
    overlap: int
) -> str:

    if (
        not previous_text
        or overlap <= 0
    ):
        return ""

    tail = previous_text[
        -overlap:
    ]

    for (
        marker,
        offset
    ) in [
        ("\n\n", 2),
        ("\n", 1),
        (". ", 2),
    ]:

        position = tail.find(
            marker
        )

        if position != -1:

            return tail[
                position + offset:
            ].strip()

    return tail.strip()


# ============================================================
# 19. PROSE CHUNKING
# ============================================================

def split_large_prose(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    min_chunk: int = MIN_CHUNK
) -> List[str]:

    text = text.strip()

    if not text:
        return []

    if len(text) <= chunk_size:
        return [
            text
        ]

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    chunks = []
    current = ""

    for paragraph in paragraphs:

        paragraph = (
            paragraph.strip()
        )

        if not paragraph:
            continue

        candidate = (
            current
            + "\n\n"
            + paragraph
        ).strip()

        if (
            len(candidate)
            <= chunk_size
        ):

            current = candidate
            continue

        if current:

            chunks.append(
                current.strip()
            )

        if (
            len(paragraph)
            > chunk_size
        ):

            start = 0

            while (
                start
                <
                len(paragraph)
            ):

                end = min(
                    start
                    + chunk_size,

                    len(paragraph)
                )

                if (
                    end
                    <
                    len(paragraph)
                ):

                    search_start = max(
                        start,
                        end - 800
                    )

                    sentence_end = max(

                        paragraph.rfind(
                            ". ",
                            search_start,
                            end
                        ),

                        paragraph.rfind(
                            ".\n",
                            search_start,
                            end
                        )
                    )

                    if (
                        sentence_end
                        >
                        start
                    ):
                        end = (
                            sentence_end
                            + 1
                        )

                piece = (
                    paragraph[
                        start:
                        end
                    ]
                    .strip()
                )

                if (
                    len(piece)
                    >= min_chunk
                ):

                    chunks.append(
                        piece
                    )

                elif (
                    piece
                    and chunks
                ):

                    chunks[-1] = (
                        chunks[-1]
                        + " "
                        + piece
                    )

                if (
                    end
                    >=
                    len(paragraph)
                ):
                    break

                start = max(
                    end - overlap,
                    start + 1
                )

            current = ""

        else:

            overlap_text = ""

            if chunks:

                overlap_text = (
                    get_overlap_text(
                        chunks[-1],
                        overlap
                    )
                )

            current = (
                overlap_text
                + "\n\n"
                + paragraph
            ).strip()

    if current:

        if (
            len(current)
            >= min_chunk
        ):

            chunks.append(
                current
            )

        elif chunks:

            chunks[-1] = (
                chunks[-1]
                + "\n\n"
                + current
            ).strip()

        else:

            chunks.append(
                current
            )

    return chunks


# ============================================================
# 20. TABLE HELPERS
# ============================================================

def escape_md_cell(
    value: str
) -> str:

    return (
        str(value or "")
        .replace(
            "|",
            "\\|"
        )
        .replace(
            "\n",
            " "
        )
        .strip()
    )


def rows_to_markdown(
    rows: List[List[str]]
) -> str:

    if not rows:
        return ""

    max_cols = max(
        len(row)
        for row in rows
    )

    normalized_rows = [
        row
        + [""] * (
            max_cols
            - len(row)
        )
        for row in rows
    ]

    header = (
        normalized_rows[0]
    )

    output = [

        "| "
        + " | ".join(
            escape_md_cell(
                cell
            )
            for cell
            in header
        )
        + " |",

        "| "
        + " | ".join(
            "---"
            for _
            in range(max_cols)
        )
        + " |",
    ]

    for row in (
        normalized_rows[1:]
    ):

        output.append(
            "| "
            + " | ".join(
                escape_md_cell(
                    cell
                )
                for cell
                in row
            )
            + " |"
        )

    return "\n".join(
        output
    )


# ============================================================
# 21. ROW-AWARE TABLE CHUNKING
# ============================================================

def chunk_table_rows(
    rows: List[List[str]],
    table_name: str,
    max_chars: int = TABLE_CHUNK_SIZE
) -> List[str]:

    """
    - whole rows only
    - repeat header
    - no overlap
    """

    if not rows:
        return []

    header = rows[0]
    data_rows = rows[1:]

    if not data_rows:

        return [
            (
                f"Table: "
                f"{table_name}"
                f"\n\n"
                + rows_to_markdown(
                    [header]
                )
            )
        ]

    chunks = []
    current_rows = []

    for row in data_rows:

        candidate_rows = (
            [header]
            +
            current_rows
            +
            [row]
        )

        candidate = (
            f"Table: "
            f"{table_name}"
            f"\n\n"
            + rows_to_markdown(
                candidate_rows
            )
        )

        if (
            len(candidate)
            <= max_chars
        ):

            current_rows.append(
                row
            )

        else:

            if current_rows:

                chunks.append(
                    (
                        f"Table: "
                        f"{table_name}"
                        f"\n\n"
                        + rows_to_markdown(
                            [header]
                            + current_rows
                        )
                    ).strip()
                )

            current_rows = [
                row
            ]

    if current_rows:

        chunks.append(
            (
                f"Table: "
                f"{table_name}"
                f"\n\n"
                + rows_to_markdown(
                    [header]
                    + current_rows
                )
            ).strip()
        )

    return chunks


# ============================================================
# 22. EMBEDDING TEXT
# ============================================================

def build_embedding_text(
    chunk_text_value: str,
    metadata: Dict
) -> str:

    parts = []

    if metadata.get(
        "plan_name"
    ):

        parts.append(
            f"Plan: "
            f"{metadata['plan_name']}"
        )

    if (
        metadata.get(
            "product_type"
        )
        and
        metadata[
            "product_type"
        ] != "UNKNOWN"
    ):

        parts.append(
            f"Product Type: "
            f"{metadata['product_type']}"
        )

    if metadata.get(
        "plan_variant"
    ):

        parts.append(
            f"Plan Variant: "
            f"{metadata['plan_variant']}"
        )

    if metadata.get(
        "state"
    ):

        parts.append(
            f"State: "
            f"{metadata['state']}"
        )

    if metadata.get(
        "section_path"
    ):

        parts.append(
            f"Section: "
            f"{metadata['section_path']}"
        )

    if metadata.get(
        "table_name"
    ):

        parts.append(
            f"Table: "
            f"{metadata['table_name']}"
        )

    header = "\n".join(
        parts
    )

    if header:

        return (
            header
            + "\n\n"
            + chunk_text_value
        )

    return chunk_text_value


# ============================================================
# 23. CREATE TEXT CHUNKS
# ============================================================

def create_text_chunks(
    cleaned_text: str,
    document_metadata: Dict,
    start_chunk_number: int = 0
) -> Tuple[
    List[Dict],
    int
]:

    sections = (
        split_into_sections(
            cleaned_text
        )
    )

    records = []

    global_chunk_number = (
        start_chunk_number
    )

    for (
        section_index,
        section
    ) in enumerate(
        sections,
        start=1
    ):

        section_name = (
            section[
                "section"
            ]
        )

        section_text = (
            section[
                "text"
            ]
        )

        section_path = (
            build_section_path(
                section
            )
        )

        body_chunks = (
            split_large_prose(
                section_text
            )
        )

        for (
            section_chunk_index,
            chunk
        ) in enumerate(
            body_chunks,
            start=1
        ):

            global_chunk_number += 1

            document_id = (
                document_metadata[
                    "document_id"
                ]
            )

            chunk_id = (
                f"{document_id}"
                f"_chunk_"
                f"{global_chunk_number:04d}"
            )

            metadata = {

                **document_metadata,

                "chunk_id":
                    chunk_id,

                "section":
                    section_name,

                "section_path":
                    section_path,

                "h1":
                    section.get(
                        "h1"
                    ),

                "h2":
                    section.get(
                        "h2"
                    ),

                "h3":
                    section.get(
                        "h3"
                    ),

                "h4":
                    section.get(
                        "h4"
                    ),

                "section_index":
                    section_index,

                "section_chunk_index":
                    section_chunk_index,

                "chunk_index":
                    global_chunk_number,

                "chunk_type":
                    "text",

                "content_source":
                    "cleaned_document_body",

                "table_id":
                    None,

                "table_name":
                    None,

                "table_index":
                    None,

                "table_chunk_index":
                    None,

                "page_number":
                    None,
            }

            embedding_text = (
                build_embedding_text(
                    chunk_text_value=
                        chunk,

                    metadata=
                        metadata
                )
            )

            record = {

                # Azure AI Search key
                "id":
                    chunk_id,

                **metadata,

                # Original retrieval content
                "text":
                    chunk,

                # Text used to create vector embedding
                "embedding_text":
                    embedding_text,

                "char_count":
                    len(chunk),

                "approx_token_count":
                    round(
                        len(chunk)
                        / 4
                    ),
            }

            records.append(
                record
            )

    return (
        records,
        global_chunk_number
    )


# ============================================================
# 24. TABLE REFERENCE VALIDATION / FILTERING
# ============================================================

TABLE_REFERENCE_PATTERN = re.compile(
    r"\[TABLE:\s*([^\]]+)\]",
    flags=re.IGNORECASE
)


def extract_referenced_table_ids(
    cleaned_text: str
) -> set:
    """
    Extract table IDs that survived cleaning.

    Example:
        [TABLE: MD0000029007_A3_table_0001]

    Only these referenced table IDs are eligible for
    table chunk creation.
    """

    return {
        table_id.strip()
        for table_id in TABLE_REFERENCE_PATTERN.findall(
            cleaned_text
        )
        if table_id.strip()
    }


def validate_and_filter_tables(
    normalized_tables: List[Dict],
    cleaned_text: str,
    document_id: str
) -> Tuple[List[Dict], Dict]:
    """
    Filter normalized JSON tables against the cleaned Markdown.

    Rule:
        A table is chunked ONLY when its table_id is still
        referenced by [TABLE: <table_id>] in cleaned.normalized.md.

    This prevents tables from removed sections from entering
    the final JSONL.
    """

    referenced_table_ids = extract_referenced_table_ids(
        cleaned_text
    )

    normalized_table_ids = {
        table.get("table_id")
        for table in normalized_tables
        if table.get("table_id")
    }

    filtered_tables = []
    skipped_table_ids = []

    for table in normalized_tables:

        table_id = table.get(
            "table_id"
        )

        if not table_id:
            skipped_table_ids.append(
                "<MISSING_TABLE_ID>"
            )
            continue

        if table_id not in referenced_table_ids:
            skipped_table_ids.append(
                table_id
            )
            continue

        filtered_tables.append(
            table
        )

    missing_from_json = sorted(
        referenced_table_ids
        - normalized_table_ids
    )

    validation = {
        "document_id": document_id,
        "referenced_table_count": len(
            referenced_table_ids
        ),
        "normalized_json_table_count": len(
            normalized_table_ids
        ),
        "eligible_table_count": len(
            filtered_tables
        ),
        "skipped_table_count": len(
            skipped_table_ids
        ),
        "missing_from_json_count": len(
            missing_from_json
        ),
        "referenced_table_ids": sorted(
            referenced_table_ids
        ),
        "skipped_table_ids": skipped_table_ids,
        "missing_from_json": missing_from_json,
    }

    return (
        filtered_tables,
        validation
    )


# ============================================================
# 25. CREATE TABLE CHUNKS
# ============================================================

def create_table_chunks(
    normalized_tables: List[Dict],
    document_metadata: Dict,
    start_chunk_number: int
) -> Tuple[
    List[Dict],
    int
]:

    records = []

    global_chunk_number = (
        start_chunk_number
    )

    document_id = (
        document_metadata[
            "document_id"
        ]
    )

    for (
        table_index,
        table
    ) in enumerate(
        normalized_tables,
        start=1
    ):

        rows = table.get(
            "json_rows",
            []
        )

        if not rows:
            continue

        table_id = (
            table.get(
                "table_id"
            )
        )

        table_name = (
            f"Table "
            f"{table_index}"
        )

        table_section = (
            table.get(
                "section"
            )
            or
            "TABLE"
        )

        section_path = (
            f"{table_section}"
            f" > "
            f"{table_name}"
        )

        table_chunks = (
            chunk_table_rows(
                rows=rows,
                table_name=
                    table_name,
                max_chars=
                    TABLE_CHUNK_SIZE
            )
        )

        for (
            table_chunk_index,
            table_chunk
        ) in enumerate(
            table_chunks,
            start=1
        ):

            global_chunk_number += 1

            chunk_id = (
                f"{document_id}"
                f"_chunk_"
                f"{global_chunk_number:04d}"
            )

            # --------------------------------------------
            # Include section/context + Markdown table.
            # --------------------------------------------

            content_parts = []

            content_parts.append(
                f"Section: "
                f"{table_section}"
            )

            if table.get(
                "preceding_context"
            ):

                content_parts.append(
                    "Context before table:\n"
                    + table[
                        "preceding_context"
                    ]
                )

            content_parts.append(
                table_chunk
            )

            if table.get(
                "following_context"
            ):

                content_parts.append(
                    "Context after table:\n"
                    + table[
                        "following_context"
                    ]
                )

            retrieval_text = (
                "\n\n".join(
                    content_parts
                )
            )

            metadata = {

                **document_metadata,

                "chunk_id":
                    chunk_id,

                "section":
                    table_section,

                "section_path":
                    section_path,

                "h1":
                    None,

                "h2":
                    None,

                "h3":
                    None,

                "h4":
                    None,

                "section_index":
                    None,

                "section_chunk_index":
                    None,

                "chunk_index":
                    global_chunk_number,

                "chunk_type":
                    "table",

                "content_source":
                    "normalized_table",

                "table_id":
                    table_id,

                "table_name":
                    table_name,

                "table_index":
                    table_index,

                # Equivalent to table_part
                "table_chunk_index":
                    table_chunk_index,

                "table_part":
                    table_chunk_index,

                "page_number":
                    table.get(
                        "page_number"
                    ),

                "table_source":
                    table.get(
                        "table_source"
                    ),

                "html_match_score":
                    table.get(
                        "html_match_score"
                    ),

                "markdown_match_score":
                    table.get(
                        "markdown_match_score"
                    ),
            }

            embedding_text = (
                build_embedding_text(
                    chunk_text_value=
                        retrieval_text,

                    metadata=
                        metadata
                )
            )

            record = {

                # Azure AI Search key
                "id":
                    chunk_id,

                **metadata,

                # Original retrieval content
                "text":
                    retrieval_text,

                # Input used for embedding
                "embedding_text":
                    embedding_text,

                "char_count":
                    len(
                        retrieval_text
                    ),

                "approx_token_count":
                    round(
                        len(
                            retrieval_text
                        )
                        / 4
                    ),
            }

            records.append(
                record
            )

    return (
        records,
        global_chunk_number
    )


# ============================================================
# 26. PREVIOUS / NEXT CHUNK LINKS
# ============================================================

def add_chunk_links(
    records: List[Dict]
) -> List[Dict]:

    for (
        index,
        record
    ) in enumerate(
        records
    ):

        record[
            "previous_chunk_id"
        ] = (
            records[
                index - 1
            ][
                "chunk_id"
            ]
            if index > 0
            else None
        )

        record[
            "next_chunk_id"
        ] = (
            records[
                index + 1
            ][
                "chunk_id"
            ]
            if (
                index
                <
                len(records) - 1
            )
            else None
        )

    return records


# ============================================================
# 27. PROCESS ONE DOCUMENT
# ============================================================

def process_document(
    normalized_json_file: Path
) -> List[Dict]:

    with normalized_json_file.open(
        "r",
        encoding="utf-8"
    ) as f:

        normalized_document = (
            json.load(f)
        )

    normalized_document_id = (
        normalized_document.get(
            "document_id"
        )
    )

    cleaned_md_file = (
        CLEANED_FOLDER
        /
        (
            f"{normalized_document_id}"
            f".cleaned.normalized.md"
        )
    )

    if not cleaned_md_file.exists():

        raise FileNotFoundError(
            f"Cleaned Markdown "
            f"not found: "
            f"{cleaned_md_file}"
        )

    cleaned_text = (
        cleaned_md_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    )

    cleaned_text = (
        normalize_whitespace(
            cleaned_text
        )
    )

    # --------------------------------------------
    # SOB metadata from document content
    # --------------------------------------------

    document_metadata = (
        extract_document_metadata(
            text=
                cleaned_text,

            source_file=
                cleaned_md_file.name
        )
    )

    # Safety check:
    # normalized ID and cleaned-text internal ID
    # should be identical.
    if (
        normalized_document_id
        and
        document_metadata[
            "document_id"
        ]
        !=
        normalized_document_id
    ):

        print(
            f"WARNING: ID mismatch. "
            f"Normalized JSON="
            f"{normalized_document_id}, "
            f"cleaned MD="
            f"{document_metadata['document_id']}"
        )

    # --------------------------------------------
    # A. Text chunks
    # --------------------------------------------

    (
        text_records,
        last_chunk_number
    ) = create_text_chunks(

        cleaned_text=
            cleaned_text,

        document_metadata=
            document_metadata,

        start_chunk_number=
            0
    )

    # --------------------------------------------
    # B. Validate/filter tables against cleaned Markdown
    # --------------------------------------------

    (
        eligible_tables,
        table_validation
    ) = validate_and_filter_tables(

        normalized_tables=
            normalized_document.get(
                "tables",
                []
            ),

        cleaned_text=
            cleaned_text,

        document_id=
            document_metadata[
                "document_id"
            ]
    )

    print(
        f"    Referenced tables : "
        f"{table_validation['referenced_table_count']}"
    )

    print(
        f"    JSON tables       : "
        f"{table_validation['normalized_json_table_count']}"
    )

    print(
        f"    Eligible tables   : "
        f"{table_validation['eligible_table_count']}"
    )

    print(
        f"    Skipped tables    : "
        f"{table_validation['skipped_table_count']}"
    )

    if table_validation[
        "missing_from_json_count"
    ]:

        print(
            f"    WARNING: cleaned Markdown references "
            f"{table_validation['missing_from_json_count']} "
            f"table ID(s) not found in normalized JSON:"
        )

        for missing_table_id in (
            table_validation[
                "missing_from_json"
            ]
        ):

            print(
                f"      - "
                f"{missing_table_id}"
            )

    # --------------------------------------------
    # C. Table chunks
    # --------------------------------------------

    (
        table_records,
        last_chunk_number
    ) = create_table_chunks(

        normalized_tables=
            eligible_tables,

        document_metadata=
            document_metadata,

        start_chunk_number=
            last_chunk_number
    )

    records = (
        text_records
        +
        table_records
    )

    records = add_chunk_links(
        records
    )

    print(
        f"\nOK: "
        f"{cleaned_md_file.name}"
    )

    print(
        f"    Internal ID   : "
        f"{document_metadata['document_id']}"
    )

    print(
        f"    Plan          : "
        f"{document_metadata['plan_name']}"
    )

    print(
        f"    Product Type  : "
        f"{document_metadata['product_type']}"
    )

    print(
        f"    Variant       : "
        f"{document_metadata['plan_variant']}"
    )

    print(
        f"    State         : "
        f"{document_metadata['state']}"
    )

    print(
        f"    Effective     : "
        f"{document_metadata['effective_date']}"
    )

    print(
        f"    Form          : "
        f"{document_metadata['form_number']}"
    )

    print(
        f"    Text chunks   : "
        f"{len(text_records)}"
    )

    print(
        f"    Table chunks  : "
        f"{len(table_records)}"
    )

    print(
        f"    Total chunks  : "
        f"{len(records)}"
    )

    return records


# ============================================================
# 28. PROCESS ALL DOCUMENTS
# ============================================================

def main():

    normalized_json_files = sorted(
        NORMALIZED_FOLDER.glob(
            "*.normalized.json"
        )
    )

    print("=" * 80)

    print(
        "POINT32HEALTH SOB "
        "NORMALIZED CHUNKING PIPELINE"
    )

    print("=" * 80)

    print(
        f"\nNormalized JSON folder:"
        f"\n{NORMALIZED_FOLDER}"
    )

    print(
        f"\nCleaned Markdown folder:"
        f"\n{CLEANED_FOLDER}"
    )

    print(
        f"\nOutput JSONL:"
        f"\n{OUTPUT_FILE}"
    )

    print(
        f"\nDocuments found: "
        f"{len(normalized_json_files)}"
    )

    all_records = []

    successful = 0
    failed = 0

    product_counts = {}
    state_counts = {}

    for normalized_json_file in (
        normalized_json_files
    ):

        try:

            records = process_document(
                normalized_json_file
            )

            if not records:
                continue

            all_records.extend(
                records
            )

            successful += 1

            product = (
                records[0][
                    "product_type"
                ]
            )

            state = (
                records[0].get(
                    "state"
                )
                or
                "UNKNOWN"
            )

            product_counts[
                product
            ] = (
                product_counts.get(
                    product,
                    0
                )
                + 1
            )

            state_counts[
                state
            ] = (
                state_counts.get(
                    state,
                    0
                )
                + 1
            )

        except Exception as error:

            failed += 1

            print(
                f"\nERROR: "
                f"{normalized_json_file.name}"
            )

            print(
                f"    "
                f"{type(error).__name__}: "
                f"{error}"
            )

    # --------------------------------------------
    # Write final JSONL
    # --------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as writer:

        for record in all_records:

            writer.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    text_chunks = sum(
        1
        for record in all_records
        if (
            record[
                "chunk_type"
            ]
            ==
            "text"
        )
    )

    table_chunks = sum(
        1
        for record in all_records
        if (
            record[
                "chunk_type"
            ]
            ==
            "table"
        )
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "CHUNKING COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        f"Documents processed : "
        f"{successful}"
    )

    print(
        f"Files failed        : "
        f"{failed}"
    )

    print(
        f"Total chunks        : "
        f"{len(all_records)}"
    )

    print(
        f"Text chunks         : "
        f"{text_chunks}"
    )

    print(
        f"Table chunks        : "
        f"{table_chunks}"
    )

    print(
        "\nPRODUCT TYPE DISTRIBUTION"
    )

    for (
        product,
        count
    ) in sorted(

        product_counts.items(),

        key=lambda item:
            -item[1]
    ):

        print(
            f"    "
            f"{product:<30} "
            f"{count}"
        )

    print(
        "\nSTATE DISTRIBUTION"
    )

    for (
        state,
        count
    ) in sorted(

        state_counts.items(),

        key=lambda item:
            -item[1]
    ):

        print(
            f"    "
            f"{state:<30} "
            f"{count}"
        )

    print(
        f"\nJSONL saved to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
