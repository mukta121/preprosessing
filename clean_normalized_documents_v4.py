# -*- coding: utf-8 -*-
"""
clean_normalized_documents_v3.py

INPUT
-----
normalized_documents/
    <document_id>.normalized.md

OUTPUT
------
cleaned_normalized_documents/
    <document_id>.cleaned.normalized.md

REMOVAL / RETENTION RULES
-------------------------
REMOVE COMPLETE SECTIONS:
- Language Assistance Services
- General Notice About Nondiscrimination
- General List of Exclusions

DO NOT REMOVE PAGE METADATA:
- <!-- PageHeader="..." -->
- <!-- PageFooter="..." -->
- <!-- PageNumber="..." -->
- <!-- PageBreak -->
- [TABLE: ...] placeholders
"""

import re
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

NORMALIZED_FOLDER = Path(
    r"C:\Users\mm7453\OneDrive - Point32Health\p32_workplace\adhoc\SOBs\normalized_documents"
)

CLEANED_FOLDER = (
    NORMALIZED_FOLDER.parent
    / "cleaned_normalized_documents"
)

CLEANED_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. LARGE SECTIONS
# ============================================================

def remove_large_noise_sections(text: str) -> str:
    """
    Remove complete unwanted boilerplate sections.

    Removes:
    - Language Assistance Services
    - General Notice About Nondiscrimination...
    - General List of Exclusions...

    The target heading itself and all nested subsections are removed.
    Removal stops only when a Markdown heading of the SAME or HIGHER
    level is reached.

    Example:
        # General List of Exclusions ...
        ## Exclusion
        ### Alternative Treatments
        ### All Other Exclusions (Continued)

    Everything above is removed until the next level-1 heading.
    """

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    target_patterns = [
        r"Language Assistance Services.*",
        r"General Notice About Nondiscrimination.*",
        r"General List of Exclusions.*",
    ]

    for target in target_patterns:
        removed_count = 0

        heading_pattern = re.compile(
            rf"(?im)^(?P<hashes>#{{1,6}})[ \t]*{target}[ \t]*$"
        )

        while True:
            match = heading_pattern.search(text)

            if not match:
                break

            heading_level = len(match.group("hashes"))
            section_start = match.start()

            remaining_text = text[match.end():]

            next_heading_pattern = re.compile(
                rf"(?m)^#{{1,{heading_level}}}[ \t]+\S"
            )

            next_match = next_heading_pattern.search(remaining_text)

            if next_match:
                section_end = match.end() + next_match.start()
            else:
                section_end = len(text)

            text = text[:section_start] + text[section_end:]
            removed_count += 1

        print(
            f"    {target}: removed {removed_count} occurrence(s)"
        )

    return text


# ============================================================
# 3. REMOVE KNOWN REPEATED HEADERS
# ============================================================

def remove_repeated_headers(text: str) -> str:
    """
    Only remove known repeated page/header artifacts.

    If any of these headings are needed as metadata,
    remove the corresponding regex from this list.
    """

    repeated_header_patterns = [
        r"(?im)^#+\s*PEDIATRIC DENTAL RIDER.*$",
        r"(?im)^#+\s*BEST BUY HMO.*$",
        r"(?im)^#+\s*VISIONCARE.*$",
    ]

    for pattern in repeated_header_patterns:
        text = re.sub(
            pattern,
            "",
            text
        )

    return text


# ============================================================
# 4. REMOVE STANDALONE COMPANY PAGE ARTIFACTS
# ============================================================

def remove_page_artifacts(text: str) -> str:
    """
    Removes standalone company names only.
    Does not remove PageHeader/PageFooter comments.
    """

    patterns = [
        r"(?im)^\s*Harvard Pilgrim Health Care\s*$",
        r"(?im)^\s*Harvard Pilgrim Health Care,\s*Inc\.\s*$",
        r"(?im)^\s*Harvard Pilgrim Health Care of New England,\s*Inc\.\s*$",
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            "",
            text
        )

    return text


# ============================================================
# 5. PRESERVE PAGE METADATA
# ============================================================

def preserve_page_metadata_comments(
    text: str
) -> str:
    """
    Intentionally retain Azure Document Intelligence comments.

    Examples:
        <!-- PageHeader="ID: MD0000028999_A4 X" -->
        <!-- PageFooter="..." -->
        <!-- PageNumber="15" -->
        <!-- PageBreak -->
    """

    return text


# ============================================================
# 6. REMOVE MARKDOWN URL, KEEP LABEL
# ============================================================

def remove_markdown_links(text: str) -> str:
    """
    [Member Portal](https://example.com)
    ->
    Member Portal
    """

    return re.sub(
        r"\[([^\]]+)\]\((.*?)\)",
        r"\1",
        text
    )


# ============================================================
# 7. REMOVE ONLY IMMEDIATE DUPLICATE PROSE LINES
# ============================================================

def remove_duplicate_lines(text: str) -> str:
    """
    Preserve:
    - HTML comments
    - HTML tables
    - Markdown table rows
    - [TABLE: ...] placeholders
    """

    lines = text.splitlines()

    deduped = []
    inside_html_table = False

    for line in lines:
        stripped = line.strip()

        # Preserve metadata comments exactly.
        if (
            stripped.startswith("<!--")
            and stripped.endswith("-->")
        ):
            deduped.append(line)
            continue

        # Preserve HTML table blocks if unmatched table remains.
        if re.search(
            r"<table\b",
            stripped,
            flags=re.IGNORECASE
        ):
            inside_html_table = True

        if inside_html_table:
            deduped.append(line)

            if re.search(
                r"</table>",
                stripped,
                flags=re.IGNORECASE
            ):
                inside_html_table = False

            continue

        # Preserve Markdown table rows.
        if stripped.startswith("|"):
            deduped.append(line)
            continue

        # Preserve table placeholders.
        if re.fullmatch(
            r"\[TABLE:\s*[^\]]+\]",
            stripped,
            flags=re.IGNORECASE
        ):
            deduped.append(line)
            continue

        if not deduped:
            deduped.append(line)
            continue

        previous_line = (
            deduped[-1].strip()
        )

        if stripped != previous_line:
            deduped.append(line)

    return "\n".join(deduped)


# ============================================================
# 8. CLEAN WHITESPACE
# ============================================================

def clean_whitespace(text: str) -> str:

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
# 9. MAIN CLEANING FUNCTION
# ============================================================

def clean_normalized_markdown(
    text: str
) -> str:

    text = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    text = remove_large_noise_sections(
        text
    )

    text = preserve_page_metadata_comments(
        text
    )

    text = remove_page_artifacts(
        text
    )

    text = remove_repeated_headers(
        text
    )

    text = remove_markdown_links(
        text
    )

    text = remove_duplicate_lines(
        text
    )

    text = clean_whitespace(
        text
    )

    return text


# ============================================================
# 10. VALIDATION
# ============================================================

def validate_cleaning(
    original_text: str,
    cleaned_text: str
) -> dict:

    placeholder_pattern = re.compile(
        r"\[TABLE:\s*[^\]]+\]",
        flags=re.IGNORECASE
    )

    page_comment_pattern = re.compile(
        r"<!--\s*"
        r"(?:PageHeader|PageFooter|PageNumber|PageBreak)"
        r"\b.*?-->",
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        )
    )

    original_placeholders = (
        placeholder_pattern.findall(
            original_text
        )
    )

    cleaned_placeholders = (
        placeholder_pattern.findall(
            cleaned_text
        )
    )

    original_page_comments = (
        page_comment_pattern.findall(
            original_text
        )
    )

    cleaned_page_comments = (
        page_comment_pattern.findall(
            cleaned_text
        )
    )

    return {
        "original_placeholders":
            len(original_placeholders),

        "cleaned_placeholders":
            len(cleaned_placeholders),

        "table_placeholders_preserved": (
            original_placeholders
            ==
            cleaned_placeholders
        ),

        "original_page_comments":
            len(original_page_comments),

        "cleaned_page_comments":
            len(cleaned_page_comments),

        "page_comments_preserved": (
            len(original_page_comments)
            ==
            len(cleaned_page_comments)
        ),
    }


# ============================================================
# 11. PROCESS ONE FILE
# ============================================================

def process_single_file(
    file_path: Path
) -> None:

    print("\n" + "=" * 70)
    print(
        f"Cleaning: "
        f"{file_path.name}"
    )

    original_text = (
        file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    )

    cleaned_text = (
        clean_normalized_markdown(
            original_text
        )
    )

    validation = validate_cleaning(
        original_text,
        cleaned_text
    )

    if file_path.name.endswith(
        ".normalized.md"
    ):
        document_id = (
            file_path.name[
                :-len(".normalized.md")
            ]
        )
    else:
        document_id = file_path.stem

    output_file = (
        CLEANED_FOLDER
        /
        f"{document_id}"
        f".cleaned.normalized.md"
    )

    output_file.write_text(
        cleaned_text,
        encoding="utf-8"
    )

    print(
        f"    Original characters : "
        f"{len(original_text):,}"
    )

    print(
        f"    Cleaned characters  : "
        f"{len(cleaned_text):,}"
    )

    print(
        f"    Removed characters  : "
        f"{len(original_text) - len(cleaned_text):,}"
    )

    print(
        f"    Table placeholders  : "
        f"{validation['original_placeholders']} "
        f"-> "
        f"{validation['cleaned_placeholders']}"
    )

    print(
        f"    Page comments       : "
        f"{validation['original_page_comments']} "
        f"-> "
        f"{validation['cleaned_page_comments']}"
    )

    if validation[
        "table_placeholders_preserved"
    ]:
        print(
            "    Table linkage       : OK"
        )
    else:
        print(
            "    WARNING: table placeholders changed"
        )

    if validation[
        "page_comments_preserved"
    ]:
        print(
            "    Page metadata       : OK"
        )
    else:
        print(
            "    WARNING: page comments changed"
        )

    print(
        f"    Saved to: "
        f"{output_file}"
    )


# ============================================================
# 12. PROCESS ALL FILES
# ============================================================

def process_files() -> None:

    normalized_files = sorted(
        NORMALIZED_FOLDER.glob(
            "*.normalized.md"
        )
    )

    print("=" * 70)
    print(
        "NORMALIZED MARKDOWN CLEANING"
    )
    print("=" * 70)

    print(
        f"\nInput folder:\n"
        f"{NORMALIZED_FOLDER}"
    )

    print(
        f"\nOutput folder:\n"
        f"{CLEANED_FOLDER}"
    )

    print(
        f"\nFound "
        f"{len(normalized_files)} "
        f"normalized Markdown files."
    )

    if not normalized_files:
        print(
            "\nNo normalized Markdown files found."
        )
        return

    successful = 0
    failed = 0

    for file_path in normalized_files:
        try:
            process_single_file(
                file_path
            )
            successful += 1

        except Exception as error:
            failed += 1

            print(
                f"\nERROR: "
                f"{file_path.name}"
            )

            print(
                f"    "
                f"{type(error).__name__}: "
                f"{error}"
            )

    print("\n" + "=" * 70)
    print("CLEANING COMPLETE")
    print("=" * 70)

    print(
        f"Total      : "
        f"{len(normalized_files)}"
    )

    print(
        f"Successful : "
        f"{successful}"
    )

    print(
        f"Failed     : "
        f"{failed}"
    )

    print(
        f"\nCleaned files:\n"
        f"{CLEANED_FOLDER}"
    )


if __name__ == "__main__":
    process_files()
