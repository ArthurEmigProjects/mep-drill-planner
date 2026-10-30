# Generating mounting-element statistics

The statistics report counts the mounting catalogue, the Zenodo duplex inventory, and the coverage mapper. One command writes the same tables as Markdown, plain text, Word, PDF, and Excel.

The reports already in the repository can be opened without running anything. Regenerate them after `data/mounting_elements/products.json` or `data/inventory/zenodo_duplex_mountable.json` changes.

## Setup

From the repository root:

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install python-docx openpyxl reportlab
```

macOS and Linux:

```bash
source .venv/bin/activate
pip install python-docx openpyxl reportlab
```

`requirements.txt` only lists `ifcopenshell`, which this command does not import. The three packages above are the writers for `.docx`, `.xlsx`, and `.pdf`. Markdown and plain text use the Python standard library, but the command writes all five files in one run, so install all three before starting.

PDF text uses DejaVu Sans and DejaVu Sans Bold. The generator loads these two files:

- `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
- `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`

On Debian or Ubuntu, `fonts-dejavu-core` provides them. A Windows checkout does not have that path. Opening the PDF that is already committed does not need the fonts. Regenerating the PDF does, and it fails with a missing-font error until those two files exist at the paths above.

## Run

Stay in the repository root:

```bash
python -m src.mounting_statistics
```

The command reads:

- `data/mounting_elements/products.json`
- `data/inventory/zenodo_duplex_mountable.json`

It recalculates coverage with `feasible_mountings`. It does not read `data/inventory/coverage.json`. Concrete anchors are counted only as companions when the substrate is concrete, which this report does not assume for the duplex model.

A successful run prints a one-line summary and the five paths, for example:

```text
products 23, elements 1163, matched 777, assumption 290, unmatched 96
md: .../data/mounting_elements/statistics/mounting_elements_statistics.md
txt: .../data/mounting_elements/statistics/mounting_elements_statistics.txt
docx: .../data/mounting_elements/statistics/mounting_elements_statistics.docx
pdf: .../data/mounting_elements/statistics/mounting_elements_statistics.pdf
xlsx: .../data/mounting_elements/statistics/mounting_elements_statistics.xlsx
```

Files are overwritten in place. The Excel workbook has a Contents sheet and one sheet per table. The PDF is landscape A4.

To write the five files somewhere else:

```bash
python -m src.mounting_statistics --out path/to/directory
```

The file names stay `mounting_elements_statistics.md`, `.txt`, `.docx`, `.pdf`, and `.xlsx`. The directory is created if it is missing.

## Refresh the inventory first

Do this only when the IFC models or the inventory script changed. Statistics generation itself does not open the IFC files.

```bash
pip install -r requirements.txt
python -m src.inventory_elements
python -m src.mounting_statistics
```

`python -m src.inventory_elements` rewrites `data/inventory/zenodo_duplex_mountable.json` from the duplex IFCs under `examples/`. `python -m src.mounting` rewrites `data/inventory/coverage.json` for the coverage file; the statistics command does not need that file.

## Check

```bash
python -m unittest tests.test_mounting_statistics -v
```

That test rebuilds the report from the shipped JSON and writes all five formats into a temporary directory. It does not replace the files under `data/mounting_elements/statistics/`.
