
import sys
import os

# Add project root to path
sys.path.append(r"f:\investment-x")

try:
    from ix.cht import oecd
    
    print("Generating Composite...")
    oecd.OecdCliDiffusionIndex_Composite()
    print("Composite OK")

    print("Generating Developed...")
    oecd.OecdCliDiffusionIndex_Developed()
    print("Developed OK")

    print("Generating Emerging...")
    oecd.OecdCliDiffusionIndex_Emerging()
    print("Emerging OK")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
