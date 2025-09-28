from pydantic import BaseModel
from typing import Dict, Union


class ColorScale(BaseModel):
    colors: Dict[int, str]

    def __getitem__(self, key: int) -> str:
        return self.colors[key]

    def keys(self):
        return self.colors.keys()

    def values(self):
        return self.colors.values()

    def items(self):
        return self.colors.items()


class Colors(BaseModel):
    primary: ColorScale = ColorScale(
        colors={
            100: "#DBEAFE",
            200: "#BFDBFE",
            300: "#93C5FD",
            400: "#60A5FA",
            500: "#3B82F6",
            600: "#2563EB",
            700: "#1D4ED8",
            800: "#1E40AF",
            900: "#1E3A8A",
        }
    )
    secondary: ColorScale = ColorScale(
        colors={
            100: "#F1F5F9",
            200: "#E2E8F0",
            300: "#CBD5E1",
            400: "#94A3B8",
            500: "#64748B",
            600: "#475569",
            700: "#334155",
            800: "#1E293B",
            900: "#0F172A",
        }
    )
    slate: ColorScale = ColorScale(
        colors={
            100: "#F1F5F9",
            200: "#E2E8F0",
            300: "#CBD5E1",
            400: "#94A3B8",
            500: "#64748B",
            600: "#475569",
            700: "#334155",
            800: "#1E293B",
            900: "#0F172A",
        }
    )
    gray: ColorScale = ColorScale(
        colors={
            100: "#F3F4F6",
            200: "#E5E7EB",
            300: "#D1D5DB",
            400: "#9CA3AF",
            500: "#6B7280",
            600: "#4B5563",
            700: "#374151",
            800: "#1F2937",
            900: "#111827",
        }
    )
    zinc: ColorScale = ColorScale(
        colors={
            100: "#F4F4F5",
            200: "#E4E4E7",
            300: "#D4D4D8",
            400: "#A1A1AA",
            500: "#71717A",
            600: "#52525B",
            700: "#3F3F46",
            800: "#27272A",
            900: "#18181B",
        }
    )
    neutral: ColorScale = ColorScale(
        colors={
            100: "#F5F5F5",
            200: "#E5E5E5",
            300: "#D4D4D4",
            400: "#A3A3A3",
            500: "#737373",
            600: "#525252",
            700: "#404040",
            800: "#262626",
            900: "#171717",
        }
    )
    stone: ColorScale = ColorScale(
        colors={
            100: "#FAFAF9",
            200: "#E7E5E4",
            300: "#D6D3D1",
            400: "#A8A29E",
            500: "#78716C",
            600: "#57534E",
            700: "#44403C",
            800: "#292524",
            900: "#1C1917",
        }
    )
    red: ColorScale = ColorScale(
        colors={
            100: "#FEE2E2",
            200: "#FECACA",
            300: "#FCA5A5",
            400: "#F87171",
            500: "#EF4444",
            600: "#DC2626",
            700: "#B91C1C",
            800: "#991B1B",
            900: "#7F1D1D",
        }
    )
    orange: ColorScale = ColorScale(
        colors={
            100: "#FFEDD5",
            200: "#FED7AA",
            300: "#FDBA74",
            400: "#FB923C",
            500: "#F97316",
            600: "#EA580C",
            700: "#C2410C",
            800: "#9A3412",
            900: "#7C2D12",
        }
    )
    amber: ColorScale = ColorScale(
        colors={
            100: "#FEF3C7",
            200: "#FDE68A",
            300: "#FCD34D",
            400: "#FBBF24",
            500: "#F59E0B",
            600: "#D97706",
            700: "#B45309",
            800: "#92400E",
            900: "#78350F",
        }
    )
    yellow: ColorScale = ColorScale(
        colors={
            100: "#FEF9C3",
            200: "#FEF08A",
            300: "#FDE047",
            400: "#FACC15",
            500: "#EAB308",
            600: "#CA8A04",
            700: "#A16207",
            800: "#854D0E",
            900: "#713F12",
        }
    )
    lime: ColorScale = ColorScale(
        colors={
            100: "#ECFCCB",
            200: "#D9F99D",
            300: "#BEF264",
            400: "#A3E635",
            500: "#84CC16",
            600: "#65A30D",
            700: "#4D7C0F",
            800: "#3F6212",
            900: "#365314",
        }
    )
    green: ColorScale = ColorScale(
        colors={
            100: "#DCFCE7",
            200: "#BBF7D0",
            300: "#86EFAC",
            400: "#4ADE80",
            500: "#22C55E",
            600: "#16A34A",
            700: "#15803D",
            800: "#166534",
            900: "#14532D",
        }
    )
    emerald: ColorScale = ColorScale(
        colors={
            100: "#D1FAE5",
            200: "#A7F3D0",
            300: "#6EE7B7",
            400: "#34D399",
            500: "#10B981",
            600: "#059669",
            700: "#047857",
            800: "#065F46",
            900: "#064E3B",
        }
    )
    teal: ColorScale = ColorScale(
        colors={
            100: "#CCFBF1",
            200: "#99F6E4",
            300: "#5EEAD4",
            400: "#2DD4BF",
            500: "#14B8A6",
            600: "#0D9488",
            700: "#0F766E",
            800: "#115E59",
            900: "#134E4A",
        }
    )
    cyan: ColorScale = ColorScale(
        colors={
            100: "#CFFAFE",
            200: "#A5F3FC",
            300: "#67E8F9",
            400: "#22D3EE",
            500: "#06B6D4",
            600: "#0891B2",
            700: "#0E7490",
            800: "#155E75",
            900: "#164E63",
        }
    )
    blue: ColorScale = ColorScale(
        colors={
            100: "#DBEAFE",
            200: "#BFDBFE",
            300: "#93C5FD",
            400: "#60A5FA",
            500: "#3B82F6",
            600: "#2563EB",
            700: "#1D4ED8",
            800: "#1E40AF",
            900: "#1E3A8A",
        }
    )
    indigo: ColorScale = ColorScale(
        colors={
            100: "#E0E7FF",
            200: "#C7D2FE",
            300: "#A5B4FC",
            400: "#818CF8",
            500: "#6366F1",
            600: "#4F46E5",
            700: "#4338CA",
            800: "#3730A3",
            900: "#312E81",
        }
    )
    violet: ColorScale = ColorScale(
        colors={
            100: "#EDE9FE",
            200: "#DDD6FE",
            300: "#C4B5FD",
            400: "#A78BFA",
            500: "#8B5CF6",
            600: "#7C3AED",
            700: "#6D28D9",
            800: "#5B21B6",
            900: "#4C1D95",
        }
    )
    purple: ColorScale = ColorScale(
        colors={
            100: "#F3E8FF",
            200: "#E9D5FF",
            300: "#D8B4FE",
            400: "#C084FC",
            500: "#A855F7",
            600: "#9333EA",
            700: "#7E22CE",
            800: "#6B21A8",
            900: "#581C87",
        }
    )
    fuchsia: ColorScale = ColorScale(
        colors={
            100: "#FAE8FF",
            200: "#F5D0FE",
            300: "#F0ABFC",
            400: "#E879F9",
            500: "#D946EF",
            600: "#C026D3",
            700: "#A21CAF",
            800: "#86198F",
            900: "#701A75",
        }
    )
    pink: ColorScale = ColorScale(
        colors={
            100: "#FCE7F3",
            200: "#FBCFE8",
            300: "#F9A8D4",
            400: "#F472B6",
            500: "#EC4899",
            600: "#DB2777",
            700: "#BE185D",
            800: "#9D174D",
            900: "#831843",
        }
    )

    # Semantic colors
    text: str = "#F8FAFC"
    text_muted: str = "#94A3B8"
    text_subtle: str = "#64748B"
    text_disabled: str = "#475569"

    background: str = "#0F172A"
    background_subtle: str = "#1E293B"
    surface: str = "#334155"
    surface_subtle: str = "#475569"

    border: str = "#334155"
    border_muted: str = "#475569"
    border_subtle: str = "#64748B"

    # Status colors
    success: str = "#22C55E"
    success_bg: str = "#DCFCE7"
    warning: str = "#F59E0B"
    warning_bg: str = "#FEF3C7"
    error: str = "#EF4444"
    error_bg: str = "#FEE2E2"
    info: str = "#3B82F6"
    info_bg: str = "#DBEAFE"

    # Interactive states
    hover: str = "rgba(255, 255, 255, 0.05)"
    active: str = "rgba(255, 255, 255, 0.1)"
    focus: str = "#3B82F6"
    disabled: str = "#475569"


class FontSizes(BaseModel):
    xs: int = 10
    sm: int = 12
    base: int = 14
    md: int = 16
    lg: int = 18
    xl: int = 20
    x2l: int = 24
    x3l: int = 30
    x4l: int = 36
    x5l: int = 48
    x6l: int = 60


class FontWeights(BaseModel):
    thin: int = 100
    extralight: int = 200
    light: int = 300
    normal: int = 400
    medium: int = 500
    semibold: int = 600
    bold: int = 700
    extrabold: int = 800
    black: int = 900


class LineHeights(BaseModel):
    none: float = 1.0
    tight: float = 1.25
    snug: float = 1.375
    normal: float = 1.5
    relaxed: float = 1.625
    loose: float = 2.0


class LetterSpacing(BaseModel):
    tighter: str = "-0.05em"
    tight: str = "-0.025em"
    normal: str = "0em"
    wide: str = "0.025em"
    wider: str = "0.05em"
    widest: str = "0.1em"


class Fonts(BaseModel):
    base: str = "Inter, Roboto, Arial, sans-serif"
    heading: str = "Poppins, sans-serif"
    monospace: str = "Fira Code, Menlo, Monaco, 'Courier New', monospace"

    size: FontSizes = FontSizes()
    weight: FontWeights = FontWeights()
    line_height: LineHeights = LineHeights()
    letter_spacing: LetterSpacing = LetterSpacing()


class Spacing(BaseModel):
    """Spacing scale for margins, padding, and gaps"""

    px: str = "1px"
    x0_5: str = "2px"
    x1: str = "4px"
    x1_5: str = "6px"
    x2: str = "8px"
    x2_5: str = "10px"
    x3: str = "12px"
    x3_5: str = "14px"
    x4: str = "16px"
    x5: str = "20px"
    x6: str = "24px"
    x7: str = "28px"
    x8: str = "32px"
    x9: str = "36px"
    x10: str = "40px"
    x11: str = "44px"
    x12: str = "48px"
    x14: str = "56px"
    x16: str = "64px"
    x20: str = "80px"
    x24: str = "96px"
    x28: str = "112px"
    x32: str = "128px"
    x36: str = "144px"
    x40: str = "160px"
    x44: str = "176px"
    x48: str = "192px"
    x52: str = "208px"
    x56: str = "224px"
    x60: str = "240px"
    x64: str = "256px"
    x72: str = "288px"
    x80: str = "320px"
    x96: str = "384px"


class BorderRadius(BaseModel):
    """Border radius scale"""

    none: str = "0px"
    sm: str = "2px"
    base: str = "4px"
    md: str = "6px"
    lg: str = "8px"
    xl: str = "12px"
    x2l: str = "16px"
    x3l: str = "24px"
    full: str = "9999px"


class Shadows(BaseModel):
    """Box shadow definitions"""

    sm: str = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    base: str = "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)"
    md: str = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
    lg: str = "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
    xl: str = (
        "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
    )
    x2l: str = "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
    inner: str = "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)"
    none: str = "none"


class ZIndex(BaseModel):
    """Z-index scale for layering"""

    auto: str = "auto"
    x0: int = 0
    x10: int = 10
    x20: int = 20
    x30: int = 30
    x40: int = 40
    x50: int = 50
    dropdown: int = 1000
    sticky: int = 1020
    fixed: int = 1030
    modal_backdrop: int = 1040
    modal: int = 1050
    popover: int = 1060
    tooltip: int = 1070


class Breakpoints(BaseModel):
    """Responsive breakpoints"""

    sm: str = "640px"
    md: str = "768px"
    lg: str = "1024px"
    xl: str = "1280px"
    x2l: str = "1536px"


class Transitions(BaseModel):
    """Transition timing and easing"""

    duration_75: str = "75ms"
    duration_100: str = "100ms"
    duration_150: str = "150ms"
    duration_200: str = "200ms"
    duration_300: str = "300ms"
    duration_500: str = "500ms"
    duration_700: str = "700ms"
    duration_1000: str = "1000ms"

    ease_linear: str = "linear"
    ease_in: str = "cubic-bezier(0.4, 0, 1, 1)"
    ease_out: str = "cubic-bezier(0, 0, 0.2, 1)"
    ease_in_out: str = "cubic-bezier(0.4, 0, 0.2, 1)"


class Theme(BaseModel):
    colors: Colors = Colors()
    fonts: Fonts = Fonts()
    spacing: Spacing = Spacing()
    border_radius: BorderRadius = BorderRadius()
    shadows: Shadows = Shadows()
    z_index: ZIndex = ZIndex()
    breakpoints: Breakpoints = Breakpoints()
    transitions: Transitions = Transitions()


# Example usage and helper methods
def get_theme() -> Theme:
    """Get the default theme instance"""
    return Theme()


def create_custom_theme(**overrides) -> Theme:
    """Create a custom theme with overrides"""
    theme_dict = Theme().dict()

    def deep_update(base_dict, override_dict):
        for key, value in override_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    deep_update(theme_dict, overrides)
    return Theme(**theme_dict)


# Example of creating a light theme variant
def create_light_theme() -> Theme:
    """Create a light theme variant"""
    return create_custom_theme(
        colors={
            "text": "#0F172A",
            "text_muted": "#475569",
            "text_subtle": "#64748B",
            "text_disabled": "#94A3B8",
            "background": "#FFFFFF",
            "background_subtle": "#F8FAFC",
            "surface": "#FFFFFF",
            "surface_subtle": "#F1F5F9",
            "border": "#E2E8F0",
            "border_muted": "#CBD5E1",
            "border_subtle": "#94A3B8",
            "hover": "rgba(0, 0, 0, 0.05)",
            "active": "rgba(0, 0, 0, 0.1)",
        }
    )



theme = get_theme()

