"""Create a comprehensive 24-slide macro report with real charts."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ix.db.conn import conn
conn.connect()

from sqlalchemy.orm import Session
from ix.db.models import Charts
from ix.db.models.report import Report
from datetime import datetime, timezone

YOUR_ID = "096862b7-b643-40a5-9f58-e41a39520fc0"  # roberthan1125@gmail.com

CHARTS = {
    "cli": "11457596-32c2-4977-bba6-caaf396674bb",
    "inflation": "fa064bdb-54c9-4af4-9d53-9ee8aff8fae5",
    "credit_impulse": "9f983490-8cc4-46b4-a404-4a8387d22e5a",
    "bank_credit": "f740b80a-a418-45b6-a0a1-6e16ba6d2cee",
    "fci": "ffa28120-7c4c-4fa4-b4b9-c867f0a1d84f",
    "ism": "8a371ae7-5300-44a9-8d83-d437caf48e40",
    "earnings": "3a10776b-dbcd-409c-8f92-c171be92e2b9",
    "liquidity": "afed00d4-bbe7-4df4-9700-f77fa0efd956",
    "fed_liq": "3086adda-1683-4191-8d85-c4ae10cbe124",
    "oecd_regime": "0f3ac260-8c15-432e-a104-3b393b1bb78f",
    "sp_crude": "99b35f06-7773-41dc-a6f4-b63f91014c7f",
    "global_eq": "297e775c-7f3e-49fe-a5b4-536305104a9a",
    "commodities": "061da5eb-f300-42c6-8669-710cca3cb977",
    "semis": "5fe7540a-c39d-4283-b259-10f751e221d7",
    "earnings_rev": "5aa1d287-5c8f-4667-9ff7-82e0869d3746",
    "market_comp": "7a271e62-f9b7-4c90-8fd3-520f580676da",
}

with Session(conn.engine) as s:
    # Load chart figures
    figs = {}
    for key, cid in CHARTS.items():
        chart = s.query(Charts).filter(Charts.id == cid, Charts.is_deleted == False).first()
        if chart and chart.figure:
            figs[key] = chart.figure
            print(f"  Loaded: {key} ({chart.name})")
        else:
            figs[key] = None
            print(f"  MISSING figure: {key}")

    def cd(key, title=None):
        """Chart data helper."""
        fig = figs.get(key)
        return {"figure": fig, "chartId": CHARTS.get(key), "chartTitle": title or key}

    def rt(html):
        """Rich text helper."""
        return {"richText": None, "html": html}

    slides = [
        # 1. Title
        {"id": "s-001", "layout": "title",
         "title": "Global Macro Regime Monitor",
         "subtitle": "Investment Strategy Group  |  Q2 2026"},

        # 2. Agenda
        {"id": "s-002", "layout": "agenda",
         "title": "Agenda",
         "agendaItems": [
             "Growth & Activity",
             "Inflation & Monetary Policy",
             "Credit & Liquidity",
             "Equity Markets",
             "Commodities & Cross-Asset",
             "Outlook & Positioning",
         ]},

        # 3. KPI Row
        {"id": "s-003", "layout": "kpi_row",
         "title": "Headline Indicators",
         "kpis": [
             {"label": "US GDP QoQ", "value": "2.8%", "change": "+0.3pp", "direction": "up"},
             {"label": "Core PCE YoY", "value": "2.6%", "change": "-0.2pp", "direction": "down"},
             {"label": "Fed Funds", "value": "4.25%", "change": "-50bps YTD", "direction": "down"},
             {"label": "US 10Y", "value": "4.15%", "change": "-20bps", "direction": "down"},
             {"label": "S&P 500", "value": "5,840", "change": "+12% YTD", "direction": "up"},
         ]},

        # 4. Section: Growth
        {"id": "s-004", "layout": "section",
         "title": "Growth & Activity",
         "subtitle": "Leading indicators suggest continued expansion with deceleration risks"},

        # 5. CLI + commentary
        {"id": "s-005", "layout": "chart_text",
         "title": "Composite Leading Indicator",
         "chart": cd("cli", "Composite Leading Indicator"),
         "body": rt(
             "<p><strong>Key observations:</strong></p>"
             "<ul>"
             "<li>CLI has inflected upward from cycle lows, suggesting economic momentum is rebuilding</li>"
             "<li>Breadth of improvement across sub-components is widening</li>"
             "<li>Historical pattern: CLI turning points lead GDP inflections by 6-9 months</li>"
             "<li>Watch for: ISM new orders / inventories ratio as confirming indicator</li>"
             "</ul>"
         )},

        # 6. OECD Regime
        {"id": "s-006", "layout": "chart_full",
         "title": "OECD G20 CLI Regime Classification",
         "chart": cd("oecd_regime", "OECD G20 CLI Regime")},

        # 7. ISM + Semis
        {"id": "s-007", "layout": "two_charts",
         "title": "Manufacturing Sector Health",
         "chart": cd("ism", "ISM PMI Manufacturing Components"),
         "chart2": cd("semis", "Semiconductor Billings YoY")},

        # 8. Section: Inflation
        {"id": "s-008", "layout": "section",
         "title": "Inflation & Monetary Policy",
         "subtitle": "Disinflationary trend intact \u2014 bond market expectations well-anchored"},

        # 9. Inflation expectations
        {"id": "s-009", "layout": "chart_text",
         "title": "Bond Market Inflation Expectations",
         "chart": cd("inflation", "Bond Market Inflation Expectations"),
         "body": rt(
             "<p><strong>Assessment:</strong></p>"
             "<ul>"
             "<li>Breakeven inflation rates anchoring around 2.3% \u2014 consistent with Fed targets</li>"
             "<li>5Y5Y forward rate showing stability \u2014 no de-anchoring risk</li>"
             "<li>TIPS market pricing supports continued disinflation narrative</li>"
             "<li>Key risk: services inflation stickiness above 3% could delay rate cuts</li>"
             "</ul>"
         )},

        # 10. Financial Conditions
        {"id": "s-010", "layout": "chart_full",
         "title": "Financial Conditions Index",
         "chart": cd("fci", "Financial Conditions Index"),
         "body": rt("<p>Financial conditions remain accommodative despite restrictive policy rate.</p>")},

        # 11. Section: Credit
        {"id": "s-011", "layout": "section",
         "title": "Credit & Liquidity",
         "subtitle": "Credit impulse turning positive \u2014 historically leads GDP acceleration"},

        # 12. Credit Impulse + Bank Credit
        {"id": "s-012", "layout": "two_charts",
         "title": "Credit Cycle Positioning",
         "chart": cd("credit_impulse", "US Credit Impulse (GDP %)"),
         "chart2": cd("bank_credit", "US Bank Credit Outlook")},

        # 13. Fed Liquidity + KPIs
        {"id": "s-013", "layout": "chart_kpi",
         "title": "Fed Liquidity & Balance Sheet",
         "chart": cd("fed_liq", "Fed Net Liquidity"),
         "kpis": [
             {"label": "Fed Balance Sheet", "value": "$6.8T", "change": "-$0.9T from peak", "direction": "down"},
             {"label": "RRP Facility", "value": "$0.4T", "change": "-$1.9T from peak", "direction": "down"},
             {"label": "Net Liquidity", "value": "$6.1T", "change": "+$0.3T QoQ", "direction": "up"},
         ]},

        # 14. Global Liquidity
        {"id": "s-014", "layout": "chart_full",
         "title": "Global Liquidity (Central Bank Assets vs M2)",
         "chart": cd("liquidity", "Global Liquidity")},

        # 15. Section: Equity
        {"id": "s-015", "layout": "section",
         "title": "Equity Markets",
         "subtitle": "Earnings growth broadening beyond mega-cap tech"},

        # 16. Earnings + Revisions
        {"id": "s-016", "layout": "two_charts",
         "title": "Earnings Cycle",
         "chart": cd("earnings", "Major Indices Earnings Growth"),
         "chart2": cd("earnings_rev", "S&P500 Earnings Revision Breadth")},

        # 17. Market Composite + commentary
        {"id": "s-017", "layout": "chart_text",
         "title": "Market Composite View",
         "chart": cd("market_comp", "Market Composite View"),
         "body": rt(
             "<p><strong>Multi-factor signal summary:</strong></p>"
             "<ul>"
             "<li>Macro regime: <strong>Expansion</strong> \u2014 CLI above trend and rising</li>"
             "<li>Earnings momentum: <strong>Positive</strong> \u2014 revision breadth above 50%</li>"
             "<li>Liquidity: <strong>Neutral</strong> \u2014 QT drag offset by RRP unwind</li>"
             "<li>Positioning: <strong>Stretched</strong> \u2014 CFTC net long near extremes</li>"
             "<li>Valuation: <strong>Expensive</strong> \u2014 forward P/E above 20x</li>"
             "</ul>"
         )},

        # 18. Section: Commodities
        {"id": "s-018", "layout": "section",
         "title": "Commodities & Cross-Asset",
         "subtitle": "Energy and metals diverging \u2014 structural vs cyclical demand"},

        # 19. Performance views
        {"id": "s-019", "layout": "two_charts",
         "title": "Cross-Asset Performance",
         "chart": cd("global_eq", "Global Equity Performance"),
         "chart2": cd("commodities", "Commodities Performance")},

        # 20. S&P vs Crude
        {"id": "s-020", "layout": "chart_full",
         "title": "S&P 500 vs Crude Oil (YoY)",
         "chart": cd("sp_crude", "S&P500 vs Crude YoY")},

        # 21. Section: Outlook
        {"id": "s-021", "layout": "section",
         "title": "Outlook & Positioning",
         "subtitle": "Balancing expansion signals against late-cycle risks"},

        # 22. Comparison: Bull vs Bear
        {"id": "s-022", "layout": "comparison",
         "title": "Bull Case vs Bear Case",
         "columns": [
             rt(
                 "<p><strong>Bull Case (60%)</strong></p>"
                 "<ul>"
                 "<li>CLI reacceleration broadens to EM</li>"
                 "<li>Fed delivers 100bps of cuts by year-end</li>"
                 "<li>Earnings growth broadens beyond Mag7</li>"
                 "<li>Credit impulse turns decisively positive</li>"
                 "<li>China stimulus gains traction in H2</li>"
                 "<li>AI capex translates to productivity gains</li>"
                 "</ul>"
                 "<p><em>Target: S&P 6,200 (+6%)</em></p>"
             ),
             rt(
                 "<p><strong>Bear Case (40%)</strong></p>"
                 "<ul>"
                 "<li>Services inflation reaccelerates above 4%</li>"
                 "<li>Fed forced to pause or reverse cuts</li>"
                 "<li>Credit conditions tighten \u2014 CRE stress</li>"
                 "<li>Earnings miss on margin compression</li>"
                 "<li>Geopolitical escalation (Taiwan, ME)</li>"
                 "<li>Liquidity withdrawal overwhelms risk assets</li>"
                 "</ul>"
                 "<p><em>Target: S&P 4,800 (-18%)</em></p>"
             ),
         ]},

        # 23. Key Takeaways
        {"id": "s-023", "layout": "text_full",
         "title": "Key Takeaways & Positioning",
         "body": rt(
             "<ol>"
             "<li><strong>Macro regime remains expansionary</strong> \u2014 CLI, ISM new orders, and credit impulse all point to continued growth.</li>"
             "<li><strong>Inflation risk is fading, not gone</strong> \u2014 Breakevens anchored but services CPI remains sticky. Fed likely delivers 2-3 more cuts.</li>"
             "<li><strong>Credit cycle turning positive</strong> \u2014 Credit impulse inflected Q4 2025. Leads GDP acceleration by 2-3 quarters.</li>"
             "<li><strong>Equities: constructive but selective</strong> \u2014 Earnings breadth improving. Overweight cyclicals and rate-sensitives.</li>"
             "<li><strong>Key risk: liquidity inflection</strong> \u2014 QT continues. RRP cushion nearly depleted. Monitor TGA drawdowns.</li>"
             "<li><strong>Positioning: 65/25/10</strong> \u2014 65% equities, 25% bonds, 10% alternatives. Gold as tail-risk hedge.</li>"
             "</ol>"
         )},

        # 24. Closing
        {"id": "s-024", "layout": "closing",
         "title": "Thank You",
         "subtitle": "Investment Strategy Group  |  Investment-X",
         "body": rt("<p>For questions or further analysis, contact the research team.</p>")},
    ]

    # Delete old reports
    old = s.query(Report).filter(Report.user_id == YOUR_ID, Report.is_deleted == False).all()
    for r in old:
        r.is_deleted = True
        r.deleted_at = datetime.now(timezone.utc)
        print(f"  Deleted old: {r.name}")

    # Create new report
    report = Report(
        user_id=YOUR_ID,
        name="Q2 2026 Global Macro Regime Monitor",
        description="Comprehensive 24-slide macro research report",
        slides=slides,
        settings={
            "theme": "dark",
            "brandName": "Investment-X",
            "classification": "For Internal Use Only",
            "author": "Investment Strategy Group",
            "showSlideNumbers": True,
            "showDateFooter": True,
        },
    )
    s.add(report)
    s.commit()
    s.refresh(report)

    charts_loaded = sum(1 for v in figs.values() if v is not None)
    print(f"\nReport created: {report.name}")
    print(f"ID: {report.id}")
    print(f"Slides: {len(slides)}")
    print(f"Charts with live data: {charts_loaded}/{len(CHARTS)}")
