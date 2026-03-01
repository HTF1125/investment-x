import traceback
from io import BytesIO
from xhtml2pdf import pisa
import sys

try:
    buf = BytesIO()
    html = """
    <html><body><img src="data:image/png;base64,invalid" /></body></html>
    """
    pisa.CreatePDF(html, dest=buf)
    print("FINISHED")
except Exception as e:
    print(f"CAUGHT Exception: {type(e)}")
except BaseException as e:
    print(f"CAUGHT BaseException: {type(e)}")
