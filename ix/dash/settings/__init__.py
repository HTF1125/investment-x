from typing import Dict, List, Union


class Theme:
    """
    Simple, intuitive Tailwind-inspired theme system.

    Easy Usage:
        theme = TailwindTheme()

        # Get colors
        theme.blue()           # Default blue (500 shade)
        theme.blue(300)        # Light blue
        theme.blue(700)        # Dark blue

        # Get semantic colors
        theme.bg              # Background color
        theme.text            # Text color
        theme.border          # Border color

        # Get sizes
        theme.space(4)        # Spacing: 1rem
        theme.text_xl()       # Font size XL

        # Toggle dark mode
        theme.dark()
        theme.light()
    """

    def __init__(self, dark_mode: bool = False):
        self.is_dark = dark_mode
        self._setup_colors()
        self._setup_spacing()
        self._setup_typography()

    # =========================
    # Color Methods - Super Simple
    # =========================

    def blue(self, shade: int = 500) -> str:
        """Get blue color. Usage: theme.blue() or theme.blue(300)"""
        return self._colors["blue"][shade]

    def red(self, shade: int = 500) -> str:
        """Get red color. Usage: theme.red() or theme.red(300)"""
        return self._colors["red"][shade]

    def green(self, shade: int = 500) -> str:
        """Get green color. Usage: theme.green() or theme.green(300)"""
        return self._colors["green"][shade]

    def yellow(self, shade: int = 500) -> str:
        """Get yellow color. Usage: theme.yellow() or theme.yellow(300)"""
        return self._colors["yellow"][shade]

    def purple(self, shade: int = 500) -> str:
        """Get purple color. Usage: theme.purple() or theme.purple(300)"""
        return self._colors["purple"][shade]

    def pink(self, shade: int = 500) -> str:
        """Get pink color. Usage: theme.pink() or theme.pink(300)"""
        return self._colors["pink"][shade]

    def orange(self, shade: int = 500) -> str:
        """Get orange color. Usage: theme.orange() or theme.orange(300)"""
        return self._colors["orange"][shade]

    def gray(self, shade: int = 500) -> str:
        """Get gray color. Usage: theme.gray() or theme.gray(300)"""
        return self._colors["gray"][shade]

    def cyan(self, shade: int = 500) -> str:
        """Get cyan color. Usage: theme.cyan() or theme.cyan(300)"""
        return self._colors["cyan"][shade]

    def teal(self, shade: int = 500) -> str:
        """Get teal color. Usage: theme.teal() or theme.teal(300)"""
        return self._colors["teal"][shade]

    # Generic color method
    def color(self, name: str, shade: int = 500) -> str:
        """Get any color. Usage: theme.color('blue', 300)"""
        if name in self._colors and shade in self._colors[name]:
            return self._colors[name][shade]
        return "#000000"  # fallback

    # =========================
    # Semantic Colors - Easy Access
    # =========================

    @property
    def bg(self) -> str:
        """Main background color"""
        return "#0f172a" if self.is_dark else "#ffffff"

    @property
    def bg_light(self) -> str:
        """Light background color (for cards, etc.)"""
        return "#1e293b" if self.is_dark else "#f8fafc"

    @property
    def text(self) -> str:
        """Main text color"""
        return "#f1f5f9" if self.is_dark else "#0f172a"

    @property
    def text_light(self) -> str:
        """Light/muted text color"""
        return "#94a3b8" if self.is_dark else "#64748b"

    @property
    def border(self) -> str:
        """Border color"""
        return "#334155" if self.is_dark else "#e2e8f0"

    @property
    def primary(self) -> str:
        """Primary brand color"""
        return self.blue()

    @property
    def success(self) -> str:
        """Success color"""
        return self.green()

    @property
    def warning(self) -> str:
        """Warning color"""
        return self.yellow()

    @property
    def danger(self) -> str:
        """Danger/error color"""
        return self.red()

    # =========================
    # Spacing - Simple Numbers
    # =========================

    def space(self, size: Union[int, float]) -> str:
        """
        Get spacing value.
        Usage: theme.space(4) returns '1rem'
        Common sizes: 1=0.25rem, 2=0.5rem, 4=1rem, 8=2rem
        """
        return self._spacing.get(size, "0")

    # Quick spacing shortcuts
    @property
    def space_xs(self) -> str:
        return self.space(1)  # 0.25rem

    @property
    def space_sm(self) -> str:
        return self.space(2)  # 0.5rem

    @property
    def space_md(self) -> str:
        return self.space(4)  # 1rem

    @property
    def space_lg(self) -> str:
        return self.space(6)  # 1.5rem

    @property
    def space_xl(self) -> str:
        return self.space(8)  # 2rem

    # =========================
    # Typography - Easy Methods
    # =========================

    def text_xs(self) -> Dict[str, str]:
        """Extra small text"""
        return {"font-size": "0.75rem", "line-height": "1rem"}

    def text_sm(self) -> Dict[str, str]:
        """Small text"""
        return {"font-size": "0.875rem", "line-height": "1.25rem"}

    def text_base(self) -> Dict[str, str]:
        """Base text size"""
        return {"font-size": "1rem", "line-height": "1.5rem"}

    def text_lg(self) -> Dict[str, str]:
        """Large text"""
        return {"font-size": "1.125rem", "line-height": "1.75rem"}

    def text_xl(self) -> Dict[str, str]:
        """Extra large text"""
        return {"font-size": "1.25rem", "line-height": "1.75rem"}

    def text_2xl(self) -> Dict[str, str]:
        """2X large text"""
        return {"font-size": "1.5rem", "line-height": "2rem"}

    def text_3xl(self) -> Dict[str, str]:
        """3X large text"""
        return {"font-size": "1.875rem", "line-height": "2.25rem"}

    def text_4xl(self) -> Dict[str, str]:
        """4X large text"""
        return {"font-size": "2.25rem", "line-height": "2.5rem"}

    # =========================
    # Mode Switching - Super Simple
    # =========================

    def dark(self):
        """Switch to dark mode"""
        self.is_dark = True
        return self

    def light(self):
        """Switch to light mode"""
        self.is_dark = False
        return self

    def toggle(self):
        """Toggle between light and dark mode"""
        self.is_dark = not self.is_dark
        return self

    # =========================
    # Chart Colors - Ready to Use
    # =========================

    @property
    def chart_colors(self) -> List[str]:
        """Perfect colors for charts and graphs"""
        return [
            self.blue(),  # Blue
            self.green(),  # Green
            self.orange(),  # Orange
            self.red(),  # Red
            self.purple(),  # Purple
            self.cyan(),  # Cyan
            self.pink(),  # Pink
            self.yellow(),  # Yellow
            self.teal(),  # Teal
            self.gray(),  # Gray
        ]

    # =========================
    # Common UI Helpers
    # =========================

    def button_primary(self) -> Dict[str, str]:
        """Primary button colors"""
        return {"background": self.primary, "color": "#ffffff", "border": self.primary}

    def button_secondary(self) -> Dict[str, str]:
        """Secondary button colors"""
        return {
            "background": "transparent",
            "color": self.primary,
            "border": self.primary,
        }

    def card(self) -> Dict[str, str]:
        """Card styling"""
        return {
            "background": self.bg_light,
            "border": f"1px solid {self.border}",
            "border-radius": "0.5rem",
            "padding": self.space_md,
        }

    def input(self) -> Dict[str, str]:
        """Input field styling"""
        return {
            "background": self.bg,
            "border": f"1px solid {self.border}",
            "color": self.text,
            "padding": self.space_sm,
            "border-radius": "0.375rem",
        }

    # =========================
    # Export for Other Libraries
    # =========================

    def for_plotly(self) -> Dict:
        """Get theme ready for Plotly charts"""
        return {
            "layout": {
                "paper_bgcolor": self.bg,
                "plot_bgcolor": self.bg,
                "font": {"color": self.text},
                "xaxis": {"gridcolor": self.border},
                "yaxis": {"gridcolor": self.border},
                "colorway": self.chart_colors,
            }
        }

    def for_css(self) -> str:
        """Get CSS variables for web use"""
        return f"""
        :root {{
            --bg: {self.bg};
            --bg-light: {self.bg_light};
            --text: {self.text};
            --text-light: {self.text_light};
            --border: {self.border};
            --primary: {self.primary};
            --success: {self.success};
            --warning: {self.warning};
            --danger: {self.danger};
            --space-xs: {self.space_xs};
            --space-sm: {self.space_sm};
            --space-md: {self.space_md};
            --space-lg: {self.space_lg};
            --space-xl: {self.space_xl};
        }}
        """

    # =========================
    # Setup Methods (Internal)
    # =========================

    def _setup_colors(self):
        """Setup the color palette - internal method"""
        self._colors = {
            "gray": {
                50: "#f9fafb",
                100: "#f3f4f6",
                200: "#e5e7eb",
                300: "#d1d5db",
                400: "#9ca3af",
                500: "#6b7280",
                600: "#4b5563",
                700: "#374151",
                800: "#1f2937",
                900: "#111827",
            },
            "blue": {
                50: "#eff6ff",
                100: "#dbeafe",
                200: "#bfdbfe",
                300: "#93c5fd",
                400: "#60a5fa",
                500: "#3b82f6",
                600: "#2563eb",
                700: "#1d4ed8",
                800: "#1e40af",
                900: "#1e3a8a",
            },
            "red": {
                50: "#fef2f2",
                100: "#fee2e2",
                200: "#fecaca",
                300: "#fca5a5",
                400: "#f87171",
                500: "#ef4444",
                600: "#dc2626",
                700: "#b91c1c",
                800: "#991b1b",
                900: "#7f1d1d",
            },
            "green": {
                50: "#f0fdf4",
                100: "#dcfce7",
                200: "#bbf7d0",
                300: "#86efac",
                400: "#4ade80",
                500: "#22c55e",
                600: "#16a34a",
                700: "#15803d",
                800: "#166534",
                900: "#14532d",
            },
            "yellow": {
                50: "#fefce8",
                100: "#fef9c3",
                200: "#fef08a",
                300: "#fde047",
                400: "#facc15",
                500: "#eab308",
                600: "#ca8a04",
                700: "#a16207",
                800: "#854d0e",
                900: "#713f12",
            },
            "purple": {
                50: "#faf5ff",
                100: "#f3e8ff",
                200: "#e9d5ff",
                300: "#d8b4fe",
                400: "#c084fc",
                500: "#a855f7",
                600: "#9333ea",
                700: "#7e22ce",
                800: "#6b21a8",
                900: "#581c87",
            },
            "pink": {
                50: "#fdf2f8",
                100: "#fce7f3",
                200: "#fbcfe8",
                300: "#f9a8d4",
                400: "#f472b6",
                500: "#ec4899",
                600: "#db2777",
                700: "#be185d",
                800: "#9d174d",
                900: "#831843",
            },
            "orange": {
                50: "#fff7ed",
                100: "#ffedd5",
                200: "#fed7aa",
                300: "#fdba74",
                400: "#fb923c",
                500: "#f97316",
                600: "#ea580c",
                700: "#c2410c",
                800: "#9a3412",
                900: "#7c2d12",
            },
            "cyan": {
                50: "#ecfeff",
                100: "#cffafe",
                200: "#a5f3fc",
                300: "#67e8f9",
                400: "#22d3ee",
                500: "#06b6d4",
                600: "#0891b2",
                700: "#0e7490",
                800: "#155e75",
                900: "#164e63",
            },
            "teal": {
                50: "#f0fdfa",
                100: "#ccfbf1",
                200: "#99f6e4",
                300: "#5eead4",
                400: "#2dd4bf",
                500: "#14b8a6",
                600: "#0d9488",
                700: "#0f766e",
                800: "#115e59",
                900: "#134e4a",
            },
        }

    def _setup_spacing(self):
        """Setup spacing scale - internal method"""
        self._spacing = {
            0: "0",
            0.5: "0.125rem",  # 2px
            1: "0.25rem",  # 4px
            1.5: "0.375rem",  # 6px
            2: "0.5rem",  # 8px
            2.5: "0.625rem",  # 10px
            3: "0.75rem",  # 12px
            3.5: "0.875rem",  # 14px
            4: "1rem",  # 16px
            5: "1.25rem",  # 20px
            6: "1.5rem",  # 24px
            7: "1.75rem",  # 28px
            8: "2rem",  # 32px
            9: "2.25rem",  # 36px
            10: "2.5rem",  # 40px
            12: "3rem",  # 48px
            16: "4rem",  # 64px
            20: "5rem",  # 80px
            24: "6rem",  # 96px
            32: "8rem",  # 128px
        }

    def _setup_typography(self):
        """Setup typography scale - internal method"""
        # Typography methods are defined above, no setup needed
        pass


# =========================
# Example Usage - Super Simple!
# =========================

if __name__ == "__main__":
    # Create theme
    theme = TailwindTheme()

    print("=== BASIC USAGE ===")
    print(f"Primary blue: {theme.blue()}")  # #3b82f6
    print(f"Light blue: {theme.blue(300)}")  # #93c5fd
    print(f"Background: {theme.bg}")  # #ffffff
    print(f"Text color: {theme.text}")  # #0f172a
    print(f"Spacing: {theme.space(4)}")  # 1rem

    print("\n=== DARK MODE ===")
    theme.dark()
    print(f"Dark background: {theme.bg}")  # #0f172a
    print(f"Dark text: {theme.text}")  # #f1f5f9

    print("\n=== CHART COLORS ===")
    print("Chart colors:", theme.chart_colors[:3])  # First 3 colors

    print("\n=== COMPONENT STYLES ===")
    button = theme.button_primary()
    print("Primary button:", button)

    print("\n=== EXPORT ===")
    plotly_theme = theme.for_plotly()
    print("Ready for Plotly:", "paper_bgcolor" in plotly_theme["layout"])



theme = Theme(dark_mode=True)
