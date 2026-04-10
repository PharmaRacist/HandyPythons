import argparse
import sys
from pathlib import Path


def convert_pptx_to_pdf(input_path: str, output_path: str = None) -> str:
    try:
        from spire.presentation import FileFormat, Presentation
    except ImportError:
        raise ImportError(
            "Required library not found. Install it with:\n"
            "  pip install spire.presentation"
        )

    input_path = Path(input_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() not in (".pptx", ".ppt"):
        raise ValueError(
            f"Input must be a .pptx or .ppt file, got: {input_path.suffix}"
        )

    if output_path:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.with_suffix(".pdf")

    print(f"Converting: {input_path}")

    prs = Presentation()
    prs.LoadFromFile(str(input_path))
    prs.SaveToFile(str(output_path), FileFormat.PDF)
    prs.Dispose()

    if not output_path.exists():
        raise RuntimeError(f"Conversion failed — output not created: {output_path}")

    print(f"Output:     {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PPTX file to PDF (no LibreOffice needed)."
    )
    parser.add_argument("input", help="Path to the input .pptx or .ppt file")
    parser.add_argument(
        "-o", "--output", help="Path for the output .pdf file (optional)", default=None
    )
    args = parser.parse_args()

    try:
        convert_pptx_to_pdf(args.input, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
