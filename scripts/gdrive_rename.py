"""
Google Drive file renamer for the 0. Research folder.
Renames files to YYYYMMDD_ISSUER_NAME.pdf format.

Setup:
1. Go to https://console.cloud.google.com/
2. Create a project (or select existing)
3. Enable "Google Drive API" (APIs & Services > Library)
4. Create OAuth 2.0 credentials (APIs & Services > Credentials > Create > OAuth client ID > Desktop App)
5. Download the JSON and save as credentials.json in this directory
6. Run: python scripts/gdrive_rename.py --list    (to see all files)
7. Run: python scripts/gdrive_rename.py --rename  (to execute renames)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"
TOKEN_PATH = Path(__file__).parent / "token.json"
CREDS_PATH = Path(__file__).parent / "credentials.json"


def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                print(f"ERROR: {CREDS_PATH} not found.")
                print("Download OAuth credentials from Google Cloud Console.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def list_files(service):
    """List all files in the research folder."""
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, size, createdTime, mimeType)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return sorted(results, key=lambda f: f["name"])


def build_rename_map():
    """
    Returns dict of {current_name: new_name}.
    Based on file content identified during browsing session.
    """
    renames = {}

    # === NUMERIC NAME FILES (identified by opening them) ===
    renames["1772983351951.pdf"] = "20260307_RaymondZucaro_FebruaryMarketThoughtsPart2.pdf"
    # The other 113KB files are likely from the same author (Raymond Zucaro series)
    # They need to be opened to confirm - leaving for manual review

    # === KOREAN RESEARCH ===
    # This long Korean title needs reformatting
    # [주간 퀀틴전시 플랜] = Weekly Quantitative Plan

    # === ALREADY WELL-NAMED FILES - just need YYYYMMDD_ISSUER_NAME format ===

    # Morgan Stanley
    renames["Morgan Stanley Investment Management _ The BEAT.pdf"] = "20260309_MorganStanley_TheBEAT.pdf"
    renames["Morgan Stanley - Churn And Burn.pdf"] = "20260220_MorganStanley_ChurnAndBurn.pdf"
    renames["Morgan Stanley Investment Management _ Key Themes for 2026.pdf"] = "20260213_MorganStanley_KeyThemes2026.pdf"

    # Goldman Sachs
    renames["GS Commodities Note_ Hard Assets Rotation (Feb 2026).pdf"] = "20260200_GS_CommoditiesHardAssetsRotation.pdf"
    renames["Goldman Sachs _ Portfolio Strategy Research.pdf"] = "20260220_GS_PortfolioStrategyResearch.pdf"
    renames["Goldman Sachs - Commodities.pdf"] = "20260220_GS_Commodities.pdf"
    renames["GS EM.pdf"] = "20260220_GS_EmergingMarkets.pdf"
    renames["GS - FX.pdf"] = "20260220_GS_FX.pdf"
    renames["Goldman Sachs - Market Know How Q1 2026.pdf"] = "20260213_GS_MarketKnowHowQ12026.pdf"
    renames["GS SUSTAIN AIData Center Power Demand How rising hyperscaler reinvestment impac..."] = "20260308_GS_AIDataCenterPowerDemand.pdf"

    # UBS
    renames["UBS Global Investment Returns Yearbook: Public summary edition 2026"] = "20260200_UBS_GlobalInvestmentReturnsYearbook2026.pdf"
    renames["UBS Chief Investment Office (CIO) GWM Investment Research report dated 27 Februar..."] = "20260227_UBS_CIOGWMInvestmentResearch.pdf"

    # HSBC
    renames["HSBC Asset Management Investment Weekly"] = "20260308_HSBC_InvestmentWeekly.pdf"
    renames["HSBC AM Investment Management Weekly (Feb 6 2026).pdf"] = "20260206_HSBC_InvestmentWeeklyFeb6.pdf"

    # Standard Chartered
    renames["Standard Chartered Weekly Market View (Feb 20 2026).pdf"] = "20260220_StandardChartered_WeeklyMarketView.pdf"
    renames["Standard Chartered Global Market Outlook (March 2026).pdf"] = "20260300_StandardChartered_GlobalMarketOutlook.pdf"
    renames["Standard Chartered _ WS Global CIO Office _ 6 February 202.pdf"] = "20260206_StandardChartered_GlobalCIOOffice.pdf"

    # Barron's
    renames["Barron's _ Vol. CVI, No. 8 \u2014 February 23, 2026.pdf"] = "20260223_Barrons_VolCVINo8.pdf"

    # Bain
    renames["Bain_ Global M&A Report 2026.pdf"] = "20260309_Bain_GlobalMAReport2026.pdf"

    # ING
    renames["ING THINK | PDF | War in the Middle East \u2013 implications for markets and macro"] = "20260308_ING_WarMiddleEastImplications.pdf"
    renames["ING Think _ Economic and Financial Analysis \u2014 February 202.pdf"] = "20260200_ING_EconomicFinancialAnalysis.pdf"

    # Mizuho
    renames['Mizuho EMEA "US-Iran: The Quick Take"'] = "20260303_Mizuho_USIranQuickTake.pdf"
    renames["Mizuho EMEA G4 Rates & FX Monthly.pdf"] = "20260220_Mizuho_G4RatesFXMonthly.pdf"

    # Syz Group
    renames["20260221_Syzgroup"] = "20260221_SyzGroup_MarketUpdate.pdf"
    renames["Syz Group"] = "20260213_SyzGroup_MarketOutlook.pdf"
    renames["Syz Group -1"] = "20260213_SyzGroup_MarketOutlook2.pdf"
    renames["FOCUS note Syz Group SMRs .pdf"] = "20260220_SyzGroup_FocusNoteSMRs.pdf"

    # J.P.Morgan
    renames["J.P.Morgan _ Corporate Compass State of the Art vs. The S.pdf"] = "20260213_JPMorgan_CorporateCompass.pdf"

    # BNP Paribas
    renames["BNP Paribas - Investment Strategy Focus.pdf"] = "20260220_BNPParibas_InvestmentStrategyFocus.pdf"

    # Piraeus
    renames["Piraeus _ Global Macro Trends \u2014 February 2026.pdf"] = "20260200_Piraeus_GlobalMacroTrends.pdf"

    # UOB
    renames["UOB Commodities Strategy - Iran Crisis Brent Crude and Gold Forecasts - Mar 2026"] = "20260300_UOB_IranCrisisCommodities.pdf"

    # KPMG
    renames["KPMG - China Macroeconomic Trends in 2026.pdf"] = "20260220_KPMG_ChinaMacroTrends2026.pdf"

    # BMI
    renames["BMI Political and Geopolitical Risks_ 2026 and Beyond.pdf"] = "20260220_BMI_PoliticalGeopoliticalRisks2026.pdf"

    # Stifel
    renames["Stifel _ Investment Strategy Brief \u2014 February 2026 .pdf"] = "20260200_Stifel_InvestmentStrategyBrief.pdf"

    # LGT
    renames["LGT Wealth Management _ Navigating noisy geo-politics.pdf"] = "20260220_LGT_NavigatingNoisyGeopolitics.pdf"

    # CreditSights
    renames["CreditSights - Utility Credit: Ten Themes for 2026"] = "20260308_CreditSights_UtilityCredit10Themes2026.pdf"

    # FT Partners
    renames["FT Partners - Global FinTech Coverage February 2026.pdf"] = "20260200_FTPartners_GlobalFinTechCoverage.pdf"

    # World Gold Council
    renames["World Gold Council_ Gold Demand Trends.pdf"] = "20260213_WorldGoldCouncil_GoldDemandTrends.pdf"
    renames["FS Super World Gold Council Gold outlook 2026 \u2014 Push a.pdf"] = "20260213_WorldGoldCouncil_GoldOutlook2026.pdf"

    # Man Group
    renames["Man_Group_Insights_The_Road_Ahead__10_for_10_One_(And_a_Bit)_Years_On_Englis..."] = "20260226_ManGroup_TheRoadAhead10for10.pdf"

    # Pakistan State Oil
    renames["Pakistan State Oil (PSO) \u2013 The Road Back to Growth.pdf"] = "20260309_PSO_RoadBackToGrowth.pdf"

    # Pinnacle
    renames["Pinnacle - The Opportunity in the Noise.pdf"] = "20260309_Pinnacle_OpportunityInTheNoise.pdf"

    # Week in 7 charts
    renames["Week in 7 charts 23 February.pdf"] = "20260223_FT_WeekIn7Charts.pdf"
    renames["Week in 7 charts - 9 February 2026.pdf"] = "20260209_FT_WeekIn7Charts.pdf"

    # Various others
    renames["Quick comments on FOMC and Market Volatility.pdf"] = "20260309_Unknown_FOMCMarketVolatility.pdf"
    renames["How Much Is $646 Billion_.pdf"] = "20260309_Unknown_HowMuchIs646Billion.pdf"
    renames["IEEPA Tariffs Asia Implications.pdf"] = "20260309_Unknown_IEEPATariffsAsiaImplications.pdf"
    renames["Iran impact - still contained"] = "20260308_Unknown_IranImpactStillContained.pdf"
    renames["Global Economics Comment Global Economic Impacts of the War in Iran"] = "20260308_Unknown_GlobalEconomicImpactsWarIran.pdf"
    renames["Transaction Banking: Bankable Insights - Issue 1, 2026"] = "20260305_Unknown_BankableInsightsIssue1.pdf"
    renames["Iran War At a Glance"] = "20260305_Unknown_IranWarAtAGlance.pdf"
    renames["Commodity Analyst The Risks to Energy Prices From Iran"] = "20260305_Unknown_RisksEnergyPricesIran.pdf"
    renames["Ignore tariff noise, focus on fundamentals"] = "20260302_Unknown_IgnoreTariffNoise.pdf"
    renames["Saudi Weekly Market Update.pdf"] = "20260223_SaudiExchange_WeeklyMarketUpdate.pdf"
    renames["Hierarchical AI Multi-Agent Fundamental Investing.pdf"] = "20260223_Unknown_HierarchicalAIMultiAgent.pdf"
    renames["Truflation Focus note.pdf"] = "20260223_Truflation_FocusNote.pdf"
    renames["4 levers, 1 risk budget.pdf"] = "20260220_Unknown_4Levers1RiskBudget.pdf"
    renames["The Garrison - South Korean Startup Ecosystem Report.pdf"] = "20260220_TheGarrison_SKStartupEcosystem.pdf"
    renames["KEVIN WARSH & THE FED BALANCE SHEET.pdf"] = "20260220_Unknown_KevinWarshFedBalanceSheet.pdf"
    renames["GEM _ 2026 Outlook \u2014 The Market's Reprise .pdf"] = "20260220_GEM_2026OutlookMarketsReprise.pdf"
    renames["Nethermind - Quantum Risk. Blockchain Strategy.pdf"] = "20260220_Nethermind_QuantumRiskBlockchain.pdf"
    renames["GECB Feb26.pdf"] = "20260220_GECB_Feb26.pdf"
    renames["Global Macro Outlook .pdf"] = "20260220_Unknown_GlobalMacroOutlook.pdf"
    renames["February 2026 Macro Moves.pdf"] = "20260220_Unknown_Feb2026MacroMoves.pdf"
    renames["Geoeconomic views_ Dedollarisation and the New Cold War.pdf"] = "20260220_Unknown_DedollarisationNewColdWar.pdf"
    renames["Nicolas_Cid_Dynamic_Tactical_Asset_Allocation_Model.pdf"] = "20260220_NicolasCid_DynamicTacticalAssetAllocation.pdf"
    renames["Macro Update - Georgia.pdf"] = "20260213_Unknown_MacroUpdateGeorgia.pdf"
    renames["Broadening Out in 2026.pdf"] = "20260213_Unknown_BroadeningOut2026.pdf"
    renames["Monthly Newsletter .pdf"] = "20260213_Unknown_MonthlyNewsletter.pdf"
    renames["US Equity L_S Squeeze.pdf"] = "20260213_Unknown_USEquityLSSqueeze.pdf"
    renames["Week Ahead_ Taking advantage of higher volatility.pdf"] = "20260213_Unknown_WeekAheadHigherVolatility.pdf"
    renames["PowerPoint Presentation"] = "20260308_Unknown_PowerPointPresentation.pdf"
    renames["a.pdf"] = "20260309_Unknown_a.pdf"

    return renames


def do_list(service):
    """List all files and show which ones will be renamed."""
    files = list_files(service)
    rename_map = build_rename_map()

    print(f"\n{'='*100}")
    print(f"Files in 0. Research folder: {len(files)}")
    print(f"{'='*100}\n")

    renamed_count = 0
    unknown_count = 0

    for f in files:
        name = f["name"]
        size = int(f.get("size", 0))
        created = f["createdTime"][:10]
        fid = f["id"]

        new_name = rename_map.get(name)
        if new_name:
            status = f"  -> {new_name}"
            renamed_count += 1
        elif name.startswith("2026") or name.startswith("2025"):
            status = "  [ALREADY FORMATTED]"
        else:
            status = "  [NO MAPPING - needs manual review]"
            unknown_count += 1

        print(f"{name}")
        print(f"  size={size:,} bytes | created={created} | id={fid}")
        print(f"{status}\n")

    print(f"\n{'='*100}")
    print(f"Total: {len(files)} | Will rename: {renamed_count} | No mapping: {unknown_count}")
    print(f"{'='*100}")


def do_rename(service, dry_run=False):
    """Execute the renames."""
    files = list_files(service)
    rename_map = build_rename_map()

    # Build lookup by name
    name_to_file = {f["name"]: f for f in files}

    renamed = 0
    skipped = 0
    errors = 0

    for old_name, new_name in sorted(rename_map.items()):
        if old_name not in name_to_file:
            print(f"SKIP (not found): {old_name}")
            skipped += 1
            continue

        fid = name_to_file[old_name]["id"]
        if dry_run:
            print(f"DRY RUN: {old_name} -> {new_name}")
            renamed += 1
        else:
            try:
                service.files().update(
                    fileId=fid,
                    body={"name": new_name},
                ).execute()
                print(f"RENAMED: {old_name} -> {new_name}")
                renamed += 1
            except Exception as e:
                print(f"ERROR renaming {old_name}: {e}")
                errors += 1

    print(f"\nDone. Renamed: {renamed} | Skipped: {skipped} | Errors: {errors}")


def main():
    parser = argparse.ArgumentParser(description="Rename files in Google Drive 0. Research folder")
    parser.add_argument("--list", action="store_true", help="List all files and planned renames")
    parser.add_argument("--rename", action="store_true", help="Execute renames")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be renamed without doing it")
    args = parser.parse_args()

    if not args.list and not args.rename and not args.dry_run:
        parser.print_help()
        return

    service = get_service()

    if args.list:
        do_list(service)
    elif args.dry_run:
        do_rename(service, dry_run=True)
    elif args.rename:
        print("This will rename files. Proceed? (y/n): ", end="")
        if input().strip().lower() == "y":
            do_rename(service, dry_run=False)
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
