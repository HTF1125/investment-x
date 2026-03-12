"""Create the Macro Research Pipeline whiteboard diagram in the database."""
import random

# ── Excalidraw element builders ──

BASE = {
    "fillStyle": "hachure",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 1,
    "opacity": 100,
    "angle": 0,
    "isDeleted": False,
    "groupIds": [],
    "frameId": None,
    "index": None,
    "link": None,
    "locked": False,
    "version": 1,
    "versionNonce": 1,
}

_id = [0]
def tid():
    _id[0] += 1
    return f"mr_{_id[0]}"


def rect(id, x, y, w, h, bg, stroke, bound_ids=None):
    return {
        **BASE, "id": id, "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": bg,
        "seed": random.randint(0, 2_000_000_000),
        "roundness": {"type": 3},
        "boundElements": [{"id": eid, "type": "text"} for eid in (bound_ids or [])],
    }


def text(id, x, y, w, h, content, fontSize=16, containerId=None, color="#1e1e1e"):
    return {
        **BASE, "id": id, "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": color, "backgroundColor": "transparent",
        "text": content, "fontSize": fontSize, "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle" if containerId else "top",
        "containerId": containerId,
        "originalText": content, "autoResize": True, "lineHeight": 1.25,
        "seed": random.randint(0, 2_000_000_000),
        "roundness": None, "boundElements": None,
    }


def arrow(id, points, x, y, startId=None, endId=None, color="#1e1e1e"):
    return {
        **BASE, "id": id, "type": "arrow",
        "x": x, "y": y,
        "width": abs(points[-1][0] - points[0][0]),
        "height": abs(points[-1][1] - points[0][1]),
        "strokeColor": color, "backgroundColor": "transparent",
        "points": points,
        "seed": random.randint(0, 2_000_000_000),
        "roundness": {"type": 2}, "boundElements": None,
        "startBinding": {"elementId": startId, "focus": 0, "gap": 8, "fixedPoint": None} if startId else None,
        "endBinding": {"elementId": endId, "focus": 0, "gap": 8, "fixedPoint": None} if endId else None,
        "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False,
    }


# ── Layout ──

START_X = 60
START_Y = 100
SRC_W, SRC_H = 140, 90
NLM_W, NLM_H = 500, 100
AN_W, AN_H = 200, 100
OUT_W, OUT_H = 160, 80
GAP_Y = 50

srcX = lambda i: START_X + i * (SRC_W + 14)
srcCenterX = START_X + (7 * (SRC_W + 14) - 14) / 2

mr_srcY = START_Y
mr_procY = START_Y + SRC_H + GAP_Y
mr_analysisY = mr_procY + NLM_H + GAP_Y
mr_outputY = mr_analysisY + AN_H + GAP_Y

nlmX = srcCenterX - NLM_W / 2

anTotalW = 3 * AN_W + 2 * 40
anStartX = srcCenterX - anTotalW / 2
anX = lambda i: anStartX + i * (AN_W + 40)

outTotalW = 4 * OUT_W + 3 * 30
outStartX = srcCenterX - outTotalW / 2
outX = lambda i: outStartX + i * (OUT_W + 30)

# ── Element IDs ──

MR_TITLE = tid()
MR_SRC_LABEL, MR_PROC_LABEL, MR_ANALYSIS_LABEL, MR_OUT_LABEL = tid(), tid(), tid(), tid()

MR_YT, MR_YT_T = tid(), tid()
MR_CB, MR_CB_T = tid(), tid()
MR_NEWS, MR_NEWS_T = tid(), tid()
MR_TG, MR_TG_T = tid(), tid()
MR_DATA, MR_DATA_T = tid(), tid()
MR_DRIVE, MR_DRIVE_T = tid(), tid()
MR_REPORTS, MR_REPORTS_T = tid(), tid()
MR_NLM, MR_NLM_T = tid(), tid()
MR_BRIEF, MR_BRIEF_T = tid(), tid()
MR_RISK, MR_RISK_T = tid(), tid()
MR_TAKE, MR_TAKE_T = tid(), tid()
MR_INFOG, MR_INFOG_T = tid(), tid()
MR_SLIDES, MR_SLIDES_T = tid(), tid()
MR_DB, MR_DB_T = tid(), tid()
MR_VAULT, MR_VAULT_T = tid(), tid()
a = [tid() for _ in range(14)]

# ── Build elements ──

elements = [
    # Title + section labels
    text(MR_TITLE, START_X, START_Y - 60, 800, 36, "Macro Research Pipeline", 28),
    text(MR_SRC_LABEL, START_X, mr_srcY - 24, 200, 20, "SOURCES", 14, None, "#868e96"),
    text(MR_PROC_LABEL, START_X, mr_procY - 24, 200, 20, "PROCESSING", 14, None, "#868e96"),
    text(MR_ANALYSIS_LABEL, START_X, mr_analysisY - 24, 200, 20, "ANALYSIS", 14, None, "#868e96"),
    text(MR_OUT_LABEL, START_X, mr_outputY - 24, 200, 20, "OUTPUTS", 14, None, "#868e96"),

    # Sources
    rect(MR_YT, srcX(0), mr_srcY, SRC_W, SRC_H, "#a5d8ff", "#1971c2", [MR_YT_T]),
    text(MR_YT_T, srcX(0), mr_srcY, SRC_W, SRC_H, "YouTube\n\n35 channels\n20 top videos", 13, MR_YT),
    rect(MR_CB, srcX(1), mr_srcY, SRC_W, SRC_H, "#b2f2bb", "#2f9e44", [MR_CB_T]),
    text(MR_CB_T, srcX(1), mr_srcY, SRC_W, SRC_H, "Central Banks\n\nFed, BoE, ECB\nMinutes & Stmts", 13, MR_CB),
    rect(MR_NEWS, srcX(2), mr_srcY, SRC_W, SRC_H, "#ffd8a8", "#e8590c", [MR_NEWS_T]),
    text(MR_NEWS_T, srcX(2), mr_srcY, SRC_W, SRC_H, "News RSS\n\n176 articles\nMultiple feeds", 13, MR_NEWS),
    rect(MR_TG, srcX(3), mr_srcY, SRC_W, SRC_H, "#d0bfff", "#7048e8", [MR_TG_T]),
    text(MR_TG_T, srcX(3), mr_srcY, SRC_W, SRC_H, "Telegram\n\n536 messages\nMacro channels", 13, MR_TG),
    rect(MR_DATA, srcX(4), mr_srcY, SRC_W, SRC_H, "#ffc9c9", "#e03131", [MR_DATA_T]),
    text(MR_DATA_T, srcX(4), mr_srcY, SRC_W, SRC_H, "Macro Data\n\n29 indicators\nTimeseries DB", 13, MR_DATA),
    rect(MR_DRIVE, srcX(5), mr_srcY, SRC_W, SRC_H, "#99e9f2", "#0c8599", [MR_DRIVE_T]),
    text(MR_DRIVE_T, srcX(5), mr_srcY, SRC_W, SRC_H, "Google Drive\n\nRecent files\nResearch docs", 13, MR_DRIVE),
    rect(MR_REPORTS, srcX(6), mr_srcY, SRC_W, SRC_H, "#eebefa", "#9c36b5", [MR_REPORTS_T]),
    text(MR_REPORTS_T, srcX(6), mr_srcY, SRC_W, SRC_H, "Reports\n\n80 research URLs\nBuyside/Sellside", 13, MR_REPORTS),

    # NotebookLM
    rect(MR_NLM, nlmX, mr_procY, NLM_W, NLM_H, "#fff3bf", "#f08c00", [MR_NLM_T]),
    text(MR_NLM_T, nlmX, mr_procY, NLM_W, NLM_H,
         "Google NotebookLM\n\nIngest all sources \u2192 Generate briefing, risk scorecard, takeaways\nGenerate infographic & slide deck",
         14, MR_NLM),

    # Analysis
    rect(MR_BRIEF, anX(0), mr_analysisY, AN_W, AN_H, "#d3f9d8", "#37b24d", [MR_BRIEF_T]),
    text(MR_BRIEF_T, anX(0), mr_analysisY, AN_W, AN_H, "Briefing\n\nMarket state, themes\ngeopolitics, policy", 13, MR_BRIEF),
    rect(MR_RISK, anX(1), mr_analysisY, AN_W, AN_H, "#ffe3e3", "#f03e3e", [MR_RISK_T]),
    text(MR_RISK_T, anX(1), mr_analysisY, AN_W, AN_H, "Risk Scorecard\n\nGeopolitical, Credit\nLiquidity, Inflation", 13, MR_RISK),
    rect(MR_TAKE, anX(2), mr_analysisY, AN_W, AN_H, "#e7f5ff", "#1c7ed6", [MR_TAKE_T]),
    text(MR_TAKE_T, anX(2), mr_analysisY, AN_W, AN_H, "Takeaways\n\nAsset positioning\nActionable insights", 13, MR_TAKE),

    # Outputs
    rect(MR_INFOG, outX(0), mr_outputY, OUT_W, OUT_H, "#fff4e6", "#e8590c", [MR_INFOG_T]),
    text(MR_INFOG_T, outX(0), mr_outputY, OUT_W, OUT_H, "Infographic\nPNG", 13, MR_INFOG),
    rect(MR_SLIDES, outX(1), mr_outputY, OUT_W, OUT_H, "#f3f0ff", "#7048e8", [MR_SLIDES_T]),
    text(MR_SLIDES_T, outX(1), mr_outputY, OUT_W, OUT_H, "Slide Deck\nPDF", 13, MR_SLIDES),
    rect(MR_DB, outX(2), mr_outputY, OUT_W, OUT_H, "#e6fcf5", "#0ca678", [MR_DB_T]),
    text(MR_DB_T, outX(2), mr_outputY, OUT_W, OUT_H, "PostgreSQL\nDB Storage", 13, MR_DB),
    rect(MR_VAULT, outX(3), mr_outputY, OUT_W, OUT_H, "#f8f0fc", "#ae3ec9", [MR_VAULT_T]),
    text(MR_VAULT_T, outX(3), mr_outputY, OUT_W, OUT_H, "Obsidian Vault\nMarkdown", 13, MR_VAULT),

    # Arrows: Sources -> NLM
    arrow(a[0], [[0,0],[0,GAP_Y]], srcX(0)+SRC_W/2, mr_srcY+SRC_H, MR_YT, MR_NLM),
    arrow(a[1], [[0,0],[0,GAP_Y]], srcX(1)+SRC_W/2, mr_srcY+SRC_H, MR_CB, MR_NLM),
    arrow(a[2], [[0,0],[0,GAP_Y]], srcX(2)+SRC_W/2, mr_srcY+SRC_H, MR_NEWS, MR_NLM),
    arrow(a[3], [[0,0],[0,GAP_Y]], srcX(3)+SRC_W/2, mr_srcY+SRC_H, MR_TG, MR_NLM),
    arrow(a[4], [[0,0],[0,GAP_Y]], srcX(4)+SRC_W/2, mr_srcY+SRC_H, MR_DATA, MR_NLM),
    arrow(a[5], [[0,0],[0,GAP_Y]], srcX(5)+SRC_W/2, mr_srcY+SRC_H, MR_DRIVE, MR_NLM),
    arrow(a[6], [[0,0],[0,GAP_Y]], srcX(6)+SRC_W/2, mr_srcY+SRC_H, MR_REPORTS, MR_NLM),

    # NLM -> Analysis
    arrow(a[7], [[0,0],[0,GAP_Y]], nlmX+NLM_W*0.25, mr_procY+NLM_H, MR_NLM, MR_BRIEF),
    arrow(a[8], [[0,0],[0,GAP_Y]], nlmX+NLM_W*0.5, mr_procY+NLM_H, MR_NLM, MR_RISK),
    arrow(a[9], [[0,0],[0,GAP_Y]], nlmX+NLM_W*0.75, mr_procY+NLM_H, MR_NLM, MR_TAKE),

    # Analysis -> Outputs
    arrow(a[10], [[0,0],[0,GAP_Y]], anX(0)+AN_W/2, mr_analysisY+AN_H, MR_BRIEF, MR_DB),
    arrow(a[11], [[0,0],[0,GAP_Y]], anX(1)+AN_W/2, mr_analysisY+AN_H, MR_RISK, MR_INFOG),
    arrow(a[12], [[0,0],[0,GAP_Y]], anX(2)+AN_W/2, mr_analysisY+AN_H, MR_TAKE, MR_SLIDES),
    arrow(a[13], [[0,0],[0,GAP_Y]], anX(2)+AN_W/2+60, mr_analysisY+AN_H, MR_TAKE, MR_VAULT),
]

scene_data = {
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {},
}

# ── Save to DB ──

from ix.db.conn import conn as db_conn, Session as DBSession
from ix.db.models import Whiteboard

db_conn.connect(max_retries=3, retry_delay=3)
owner_id = "096862b7-b643-40a5-9f58-e41a39520fc0"

with DBSession() as db:
    # Check if one already exists
    existing = db.query(Whiteboard).filter(
        Whiteboard.user_id == owner_id,
        Whiteboard.title == "Macro Research Pipeline",
        Whiteboard.is_deleted == False,
    ).first()

    if existing:
        existing.scene_data = scene_data
        db.flush()
        print(f"Updated existing whiteboard: {existing.id}")
    else:
        wb = Whiteboard(user_id=owner_id, title="Macro Research Pipeline", scene_data=scene_data)
        db.add(wb)
        db.flush()
        db.refresh(wb)
        print(f"Created whiteboard: {wb.id}")

    print(f"Elements: {len(elements)}")

print("Done!")
