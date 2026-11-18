# MathLab

MathLab is a Python mathematical and experimental-data workspace.

## Requirements

Python 3.10+ is recommended.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
Run the graphical application
python main.py


The desktop interface is built with pywebview and uses a local HTML/CSS/JavaScript frontend.

Available in the initial GUI:
- Formula editor connected to MathEngine.
- Numeric and symbolic expression evaluation.
- CSV import through the native file dialog.
- Experimental dataset management.
- Plotting numeric CSV columns with Matplotlib.
Enable the pywebview debug mode:
python main.py --debug


Run the console demonstration:
python main.py --demo


Tests
python -m pytest -q


