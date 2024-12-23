from openai import OpenAI
from io import BytesIO
import fitz
import json
import re
from typing import Optional


class PDFSummarizer:
    """
    A class that summarizes PDF content into a structured JSON format suitable for investment insights.

    Attributes:
        PROMPT (str): The instruction prompt for the language model.
        client (OpenAI): An OpenAI client instance.
        model (str): The OpenAI model to use.
    """

    PROMPT = """
Provide a one to three paragraph, professional investment insight that offers a
forward-looking market analysis, clearly identifies key drivers and assumptions,
and includes specific, actionable recommendations with potential returns,
associated risks, alignment to different risk tolerances, time horizons, and
sector or geographic focuses. Incorporate a brief but robust risk assessment
outlining how these strategies might underperform under certain economic or
geopolitical conditions, and suggest mitigation approaches.
Ensure the language is concise, avoids special symbols, and is suitable for
seasoned investors seeking practical, data-driven strategies and tactical
insights aligned with evolving market dynamics.
Content :
"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initializes the PDFSummarizer class.

        Args:
            api_key (str): API key for OpenAI.
            model (str): The model to use for summarization.
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def pdf_bytes_to_text(self, pdf_bytes: bytes) -> str:
        """
        Converts a PDF in bytes format to text.

        Args:
            pdf_bytes (bytes): The PDF file content.

        Returns:
            str: Extracted text from the PDF.
        """
        try:
            pdf_stream = BytesIO(pdf_bytes)
            pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
            extracted_text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                extracted_text += page.get_text()
            pdf_document.close()
            return extracted_text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def summarize_text(self, content: str) -> Optional[str]:
        """
        Summarizes the provided text using OpenAI's chat completions.

        Args:
            content (str): Text to be summarized.

        Returns:
            str: Summary response from OpenAI.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.PROMPT + content}],
            )
            response = completion.choices[0].message.content
            if response is None:
                return None
            return response.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return ""

    def process_insights(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Process the PDF and extract structured summary data.

        Args:
            pdf_bytes (bytes): The PDF content as bytes.

        Returns:
            dict: The parsed JSON data from the model's summary or None if parsing fails.
        """
        text = self.pdf_bytes_to_text(pdf_bytes)
        if not text:
            print("No text extracted from PDF.")
            return None

        response = self.summarize_text(text)
        if not response:
            print("No response from the model.")
            return None

        return response
