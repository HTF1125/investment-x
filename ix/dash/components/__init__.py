import dash_mantine_components as dmc


def ChartGrid(children):
    """
    Renders a responsive grid for chart cards using Mantine's SimpleGrid.

    Args:
        children (list or component): The chart cards or components to display in the grid.

    Returns:
        dmc.SimpleGrid: A responsive grid layout for the provided children.
    """
    # Use fixed values for cols, spacing, and verticalSpacing to avoid type errors.
    # These values can be adjusted as needed for responsiveness.
    return dmc.SimpleGrid(
        cols={"base": 1, "sm": 2, "md": 2, "lg": 3},
        spacing={"base": 10, "sm": "xl", "md": "xl", "lg": "xl"},
        verticalSpacing={"base": "md", "sm": "xl", "md": "xl", "lg": "xl"},
        children=children,
    )
