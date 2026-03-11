"""Create a sample whiteboard with Investment Thesis Framework template."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ix.db.conn import Session
from ix.db.models import Whiteboard, User

template = {
    "elements": [
        {"id": "tmpl_title", "type": "text", "x": 100, "y": 50, "width": 600, "height": 36,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "Investment Thesis Framework", "fontSize": 28, "fontFamily": 1,
         "textAlign": "center", "verticalAlign": "top", "containerId": None,
         "originalText": "Investment Thesis Framework", "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 12345, "roundness": None, "boundElements": None},

        {"id": "box_macro", "type": "rectangle", "x": 100, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff",
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 22345, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_macro", "type": "text"}]},

        {"id": "txt_macro", "type": "text", "x": 100, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "MACRO OUTLOOK\n\n\u2022 GDP / CPI\n\u2022 Fed Policy\n\u2022 Credit Spreads",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_macro",
         "originalText": "MACRO OUTLOOK\n\n\u2022 GDP / CPI\n\u2022 Fed Policy\n\u2022 Credit Spreads",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 32345, "roundness": None, "boundElements": None},

        {"id": "box_signals", "type": "rectangle", "x": 400, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 42345, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_signals", "type": "text"}]},

        {"id": "txt_signals", "type": "text", "x": 400, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "SIGNALS\n\n\u2022 Trend (40w SMA)\n\u2022 Macro Composite\n\u2022 VIX Regime",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_signals",
         "originalText": "SIGNALS\n\n\u2022 Trend (40w SMA)\n\u2022 Macro Composite\n\u2022 VIX Regime",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 52345, "roundness": None, "boundElements": None},

        {"id": "box_alloc", "type": "rectangle", "x": 700, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#e8590c", "backgroundColor": "#ffd8a8",
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 62345, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_alloc", "type": "text"}]},

        {"id": "txt_alloc", "type": "text", "x": 700, "y": 120, "width": 220, "height": 150,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "ALLOCATION\n\n90% Risk-On\n50% Neutral\n10% Risk-Off",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_alloc",
         "originalText": "ALLOCATION\n\n90% Risk-On\n50% Neutral\n10% Risk-Off",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 72345, "roundness": None, "boundElements": None},

        {"id": "box_data", "type": "rectangle", "x": 100, "y": 330, "width": 220, "height": 150,
         "strokeColor": "#7048e8", "backgroundColor": "#d0bfff",
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 82345, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_data", "type": "text"}]},

        {"id": "txt_data", "type": "text", "x": 100, "y": 330, "width": 220, "height": 150,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "DATA SOURCES\n\n\u2022 FRED\n\u2022 Yahoo Finance\n\u2022 Bloomberg",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_data",
         "originalText": "DATA SOURCES\n\n\u2022 FRED\n\u2022 Yahoo Finance\n\u2022 Bloomberg",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 92345, "roundness": None, "boundElements": None},

        {"id": "box_exec", "type": "rectangle", "x": 700, "y": 330, "width": 220, "height": 150,
         "strokeColor": "#e03131", "backgroundColor": "#ffc9c9",
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 10345, "roundness": {"type": 3},
         "boundElements": [{"id": "txt_exec", "type": "text"}]},

        {"id": "txt_exec", "type": "text", "x": 700, "y": 330, "width": 220, "height": 150,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "text": "EXECUTION\n\n\u2022 Rebalance\n\u2022 Backtest\n\u2022 Monitor",
         "fontSize": 16, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
         "containerId": "box_exec",
         "originalText": "EXECUTION\n\n\u2022 Rebalance\n\u2022 Backtest\n\u2022 Monitor",
         "autoResize": True, "lineHeight": 1.25,
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 11345, "roundness": None, "boundElements": None},

        {"id": "arr_1", "type": "arrow", "x": 320, "y": 195, "width": 80, "height": 0,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [80, 0]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 12346, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_macro", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_signals", "focus": 0, "gap": 8, "fixedPoint": None},
         "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False},

        {"id": "arr_2", "type": "arrow", "x": 620, "y": 195, "width": 80, "height": 0,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [80, 0]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 22346, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_signals", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_alloc", "focus": 0, "gap": 8, "fixedPoint": None},
         "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False},

        {"id": "arr_3", "type": "arrow", "x": 210, "y": 270, "width": 0, "height": 60,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [0, 60]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 32346, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_macro", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_data", "focus": 0, "gap": 8, "fixedPoint": None},
         "startArrowhead": None, "endArrowhead": "arrow", "elbowed": False},

        {"id": "arr_4", "type": "arrow", "x": 810, "y": 270, "width": 0, "height": 60,
         "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
         "points": [[0, 0], [0, 60]],
         "fillStyle": "hachure", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
         "opacity": 100, "angle": 0, "isDeleted": False, "groupIds": [], "frameId": None,
         "index": None, "link": None, "locked": False, "version": 1, "versionNonce": 1,
         "seed": 42346, "roundness": {"type": 2}, "boundElements": None,
         "startBinding": {"elementId": "box_alloc", "focus": 0, "gap": 8, "fixedPoint": None},
         "endBinding": {"elementId": "box_exec", "focus": 0, "gap": 8, "fixedPoint": None},
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
        title="Investment Thesis Framework",
        scene_data=template,
    )
    s.add(wb)
    s.commit()
    s.refresh(wb)
    print(f"Created whiteboard: {wb.id}")
    print(f"Title: {wb.title}")
    print(f"Elements: {len(wb.scene_data.get('elements', []))}")
    print("Done! Navigate to /whiteboard to see it.")
