import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
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
        description="Convert PPTX files to PDF in parallel (no LibreOffice needed)."
    )
    parser.add_argument(
        "input", 
        nargs="+", 
        help="Path to the input .pptx or .ppt file(s)"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Path for the output .pdf file (ignored if using --batch or multiple inputs)", 
        default=None
    )
    parser.add_argument(
        "--batch", 
        action="store_true", 
        help="Explicitly flag that multiple files are being processed"
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        help="Number of parallel workers (defaults to CPU count)"
    )
    args = parser.parse_args()

    if len(args.input) > 1 and not args.batch:
        print("Error: Multiple files provided. Use --batch flag to confirm batch processing.", file=sys.stderr)
        sys.exit(1)

    has_errors = False

    if len(args.input) == 1:
        try:
            convert_pptx_to_pdf(args.input[0], args.output)
        except Exception as e:
            print(f"Error converting {args.input[0]}: {e}", file=sys.stderr)
            has_errors = True
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            future_to_file = {
                executor.submit(convert_pptx_to_pdf, file_path, None): file_path 
                for file_path in args.input
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error converting {file_path}: {e}", file=sys.stderr)
                    has_errors = True

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
