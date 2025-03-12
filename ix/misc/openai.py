from openai import OpenAI
from io import BytesIO
import fitz
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
Provide a comprehensive, forward-looking market analysis in 2-3 paragraphs,
focusing on tactical investment opportunities. Identify 3-5 key market drivers
and underlying assumptions, citing specific economic indicators, industry trends,
and geopolitical factors. Incorporate recent data from reputable financial sources
such as Bloomberg, Reuters, or S&P Global Market Intelligence to support your analysis.

Based on this analysis, offer 2-3 actionable investment recommendations.
For each recommendation, specify the target sector or geographic region,
expected time horizon (short, medium, or long-term), and potential return range.
Clearly articulate the investment thesis, including catalysts that could drive
outperformance. Address associated risks, both systematic and idiosyncratic,
and suggest risk mitigation strategies.
Tailor your language for sophisticated investors, using industry-standard financial
terminology and metrics (e.g., P/E ratios, EBITDA margins, yield curves).
Emphasize how these tactical ideas align with or diverge from current market consensus,
and explain how they can be implemented within a broader portfolio strategy.
Conclude with a brief discussion on how these recommendations may evolve
under different economic scenarios.

use not bullet points, just use normal text foramt.

Content :
    """

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        """
        Initializes the PDFSummarizer class.

        Args:
            api_key (str): API key for OpenAI.
            model (str): The model to use for summarization.
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
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


from typing import Dict, Any, Optional


class TaaViews:

    PROMPT = """
Role and Objective:
You are a Chief Investment Officer at a top-tier global asset management firm.
Using the provided market insights, and your expertise, deliver a
tactical asset allocation report.

The analysis must include quantitative metrics and qualitative reasoning to support each recommendation.
with detailed reasoning and facts to back up your allocation.
________________________________________
Task Breakdown:
1.	Macroeconomic Analysis:
    Review key global economic indicators (GDP growth, inflation, unemployment).
    Analyze central bank policies (interest rates, QE/QT) and their market impact.
    Assess geopolitical factors (trade tensions, wars, regional stability) and their influence on market sentiment.
2.	Investment Views Across Asset Classes:
    Provide actionable Tactical Outlook (Overweight, Neutral, Underweight) with detailed rationale for:
        Asset Classes: Equities, Fixed Income, Alternatives.
        Regions: Developed Markets (US, Europe, Japan, Korea) and Emerging Markets.
        Sectors: Deliver sector-specific views (e.g., Technology, Healthcare, Energy).
        Include Risks for each view and suggest mitigation strategies.
3.	Key Investment Themes:
    Identify 5 major investment themes shaping the strategy. For each theme:
        Explain its influence on asset allocation.
        Highlight specific opportunities and risks aligned with the theme.
4.	Implementation Ideas:
    Offer detailed implementation strategies for each asset class:
        Preferred instruments: ETFs, derivatives, sectors, security types.
        Allocations or ranges: Specify target exposure (e.g., 5%-10%).
5.	Catalysts and Risks:
    Identify major positive/negative catalysts that may impact your outlook.
    Conduct scenario analysis for key risks and provide hedging strategies to mitigate downside exposure.
________________________________________
Deliverable Format:
Structure your output precisely as follows:
{
    "Global Economic Outlook": "<Concise summary of global macroeconomic trends and their impact>",
    "Key Investment Themes": ["<Theme 1>", "<Theme 2>", "<Theme 3>", "<Theme 4>", "<Theme 5>"],
    "Asset Class Views": {
        "Equities": {
            "Overall": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-backed reasoning>"},
            "United States": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
            "Europe": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
            "Japan": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
            "Korea": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
            "India": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
            "China": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed reasoning>"},
        },
        "GICS Sector (US)": {
            "Real Estate": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"},
            "Materials": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"},
            "Industrials": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"},
            "Technology": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"},
            "Healthcare": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"},
            "Energy": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
            "Staples": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
            "Discretionary": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
            "Communications": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
            "Utilities": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
            "Financials": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-driven analysis>"}
        },
        "Fixed Income": {
            "Overall": {"view": "Overweight/Neutral/Underweight", "rationale": "<Data-backed reasoning>"},
            "Government2Y": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "Government30Y": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "Investment Grade": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "High Yield": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "Emerging Market Debt": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"}
            "Korea Treasuries": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"}
        },
        "Alternatives": {
            "Gold": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "Silver": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "REITs(US)": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "REITs(KR)": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "Bitcoin": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"},
            "USD": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"}
            "KRW": {"view": "Overweight/Neutral/Underweight", "rationale": "<Detailed analysis>"}
        }
    },
    "Top Tactical Ideas": [
        {"idea": "<Implementation strategy 1>", "rationale": "<Supporting analysis>"},
        {"idea": "<Implementation strategy 2>", "rationale": "<Supporting analysis>"},
        {"idea": "<Implementation strategy 3>", "rationale": "<Supporting analysis>"}
    ],
    "Key Risks": ["<Risk 1>", "<Risk 2>", "<Risk 3>"]
}
* Please keep in mind to include every asset class and sectors in the format!!

Provided Insights:

    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initializes the PDFSummarizer class.

        Args:
            api_key (str): API key for OpenAI.
            model (str): The model to use for summarization.
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        self.model = model

    def generate_tactical_views(self, insights: str) -> Optional[Dict[str, Any]]:
        """
        Generate tactical views using the OpenAI API.

        Args:
            api_key (str): The OpenAI API key.
            prompt (str): The generated prompt for the API.

        Returns:
            Optional[Dict[str, Any]]: Parsed tactical views or None if an error occurs.
        """
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": self.PROMPT + insights}],
        )
        return completion.choices[0].message.content.strip()
