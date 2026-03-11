"""Create a 'Market Regime Dashboard' whiteboard."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ix.db.conn import Session
from ix.db.models import Whiteboard, User

template = {
    "elements": [
        # Title
        {"id": "reg_title", "type": "text", "x": 80, "y": 30, "width": 700, "height": 40,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "Market Regime Dashboard", "fontSize": 32, "fontFamily": 1,
         "textAlign": "left", "verticalAlign": "top", "containerId": None,
         "originalText": "Market Regime Dashboard", "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99001, "roundness": None, "boundElements": None},

        # ── Row 1: Risk-On / Neutral / Risk-Off ──

        # Risk-On box
        {"id": "box_risk_on", "type": "rectangle", "x": 80, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
         "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99010, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_risk_on", "type": "text"}]},
        {"id": "txt_risk_on", "type": "text", "x": 80, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "RISK-ON\n90% Equity\n\nTrend UP + Macro UP",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_risk_on",
         "originalText": "RISK-ON\n90% Equity\n\nTrend UP + Macro UP",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99011, "roundness": None, "boundElements": None},

        # Neutral box
        {"id": "box_neutral", "type": "rectangle", "x": 330, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#e8590c", "backgroundColor": "#ffd8a8",
         "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99020, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_neutral", "type": "text"}]},
        {"id": "txt_neutral", "type": "text", "x": 330, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "NEUTRAL\n50% Equity\n\nMixed Signals",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_neutral",
         "originalText": "NEUTRAL\n50% Equity\n\nMixed Signals",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99021, "roundness": None, "boundElements": None},

        # Risk-Off box
        {"id": "box_risk_off", "type": "rectangle", "x": 580, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#e03131", "backgroundColor": "#ffc9c9",
         "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99030, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_risk_off", "type": "text"}]},
        {"id": "txt_risk_off", "type": "text", "x": 580, "y": 100, "width": 200, "height": 120,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "RISK-OFF\n10% Equity\n\nTrend DN + Macro DN",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_risk_off",
         "originalText": "RISK-OFF\n10% Equity\n\nTrend DN + Macro DN",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99031, "roundness": None, "boundElements": None},

        # ── Arrows between regime boxes ──
        {"id": "arr_on_neut", "type": "arrow", "x": 280, "y": 160, "width": 50, "height": 0,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [50, 0]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99040, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_risk_on", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_neutral", "focus": 0, "gap": 8, "fixedPoint": None},
         "startArrowhead": "arrow", "endArrowhead": "arrow", "elbowed": False},

        {"id": "arr_neut_off", "type": "arrow", "x": 530, "y": 160, "width": 50, "height": 0,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [50, 0]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99041, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_neutral", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_risk_off", "focus": 0, "gap": 8, "fixedPoint": None},
         "startArrowhead": "arrow", "endArrowhead": "arrow", "elbowed": False},

        # ── Row 2: Key Indicators ──

        # Indicators box
        {"id": "box_indicators", "type": "rectangle", "x": 80, "y": 280, "width": 350, "height": 160,
         "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff",
         "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99050, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_indicators", "type": "text"}]},
        {"id": "txt_indicators", "type": "text", "x": 80, "y": 280, "width": 350, "height": 160,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "KEY INDICATORS (by IC)\n\n1. CESI Breadth (+0.247)\n2. HY/IG Ratio (-0.195)\n3. VIX (+0.157)\n4. Fed Net Liquidity (+0.148)\n5. OECD CLI EM (+0.143)",
         "fontSize": 16, "fontFamily": 1, "textAlign": "left", "verticalAlign": "middle",
         "containerId": "box_indicators",
         "originalText": "KEY INDICATORS (by IC)\n\n1. CESI Breadth (+0.247)\n2. HY/IG Ratio (-0.195)\n3. VIX (+0.157)\n4. Fed Net Liquidity (+0.148)\n5. OECD CLI EM (+0.143)",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99051, "roundness": None, "boundElements": None},

        # Performance box
        {"id": "box_perf", "type": "rectangle", "x": 480, "y": 280, "width": 300, "height": 160,
         "strokeColor": "#7048e8", "backgroundColor": "#d0bfff",
         "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99060, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_perf", "type": "text"}]},
        {"id": "txt_perf", "type": "text", "x": 480, "y": 280, "width": 300, "height": 160,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "BACKTEST RESULTS\n\nAvg Sharpe: 0.57\nAvg Alpha: +3.4%/yr\nRolling IC+: 87%\n\nAll 9 indices positive alpha",
         "fontSize": 16, "fontFamily": 1, "textAlign": "left", "verticalAlign": "middle",
         "containerId": "box_perf",
         "originalText": "BACKTEST RESULTS\n\nAvg Sharpe: 0.57\nAvg Alpha: +3.4%/yr\nRolling IC+: 87%\n\nAll 9 indices positive alpha",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99061, "roundness": None, "boundElements": None},

        # Vertical arrow from regime row to indicators
        {"id": "arr_down", "type": "arrow", "x": 430, "y": 220, "width": 0, "height": 60,
         "strokeColor": "#868e96", "backgroundColor": "transparent",
         "points": [[0, 0], [0, 60]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "dashed", "roughness": 0,
         "opacity": 70, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 99070, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": None, "endBinding": None,
         "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False},
    ],
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {}
}

with Session() as s:
    user = s.query(User).first()
    if not user:
        print("ERROR: No users found in DB")
        sys.exit(1)

    print(f"Creating whiteboard for user: {user.email} (id: {user.id})")
    wb = Whiteboard(
        user_id=str(user.id),
        title="Market Regime Dashboard",
        scene_data=template,
    )
    s.add(wb)
    s.commit()
    s.refresh(wb)
    print(f"Created whiteboard: {wb.id}")
    print(f"Title: {wb.title}")
    print(f"Elements: {len(wb.scene_data.get('elements', []))}")
    print("Done!")
