from __future__ import annotations
import streamlit as st
import traceback
from ix.db.conn import Session
from ix.db.models.chart import Chart

# Page configuration
st.set_page_config(layout="wide", page_title="Investment-X Labs")

st.title("Investment-X Research Library")


def get_charts_by_category():
    """Fetches all charts from the database and groups them by category."""
    charts_by_cat = {}
    with Session() as s:
        charts = s.query(Chart).all()
        for chart in charts:
            s.expunge(chart)  # Detach from session so we can use it after close

            cat = chart.category or "Uncategorized"
            if cat not in charts_by_cat:
                charts_by_cat[cat] = {}

            # Use 'code' as the identifier name since it's the PK
            # If you have a separate display name column, use that instead.
            charts_by_cat[cat][chart.code] = chart

    return charts_by_cat


# Load categories dynamically from DB
try:
    categories = get_charts_by_category()
except Exception as e:
    st.error(f"Failed to load charts from database: {e}")
    categories = {}

if not categories:
    st.warning("No charts found in the database.")

# Sidebar navigation
show_all = st.sidebar.checkbox("Show All Charts", value=False)
refresh_data = st.sidebar.checkbox("Force Data Refresh", value=False)

# Prepare flat list of charts for navigation
flat_charts = []
# Sort categories for consistent order
sorted_cats = sorted(categories.keys())
for cat in sorted_cats:
    # Sort charts within category
    sorted_chart_names = sorted(categories[cat].keys())
    for name in sorted_chart_names:
        flat_charts.append((cat, name))

if "chart_idx" not in st.session_state:
    st.session_state.chart_idx = 0


def update_idx(new_idx):
    if not flat_charts:
        st.session_state.chart_idx = 0
    else:
        st.session_state.chart_idx = new_idx % len(flat_charts)


if not show_all and flat_charts:
    st.sidebar.markdown("### Chart Navigation")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("← Previous", use_container_width=True):
        update_idx(st.session_state.chart_idx - 1)
    if col2.button("Next →", use_container_width=True):
        update_idx(st.session_state.chart_idx + 1)

    # Sync selectboxes with current_idx
    curr_cat, curr_name = flat_charts[st.session_state.chart_idx]

    cat_list = sorted_cats
    try:
        cat_idx = cat_list.index(curr_cat)
    except ValueError:
        cat_idx = 0

    cat_selection = st.sidebar.selectbox(
        "Select Category", options=cat_list, index=cat_idx
    )

    # Handle category change via selectbox
    if cat_selection != curr_cat:
        # Move to first chart of new category
        if categories[cat_selection]:
            new_name = sorted(categories[cat_selection].keys())[0]
            try:
                st.session_state.chart_idx = flat_charts.index(
                    (cat_selection, new_name)
                )
            except ValueError:
                pass
            curr_name = new_name

    chart_list = sorted(categories[cat_selection].keys())
    try:
        chart_idx = chart_list.index(curr_name)
    except ValueError:
        chart_idx = 0

    chart_selection = st.sidebar.selectbox(
        "Select Chart", options=chart_list, index=chart_idx
    )

    # Handle chart change via selectbox
    if chart_selection != curr_name:
        try:
            st.session_state.chart_idx = flat_charts.index(
                (cat_selection, chart_selection)
            )
        except ValueError:
            pass

    if chart_selection:
        chart_inst = categories[cat_selection][chart_selection]

        # In-page navigation buttons
        mcol1, mcol2, mcol3 = st.columns([1, 4, 1])
        if mcol1.button("←", key="prev_main", use_container_width=True):
            update_idx(st.session_state.chart_idx - 1)
            st.rerun()
        if mcol3.button("→", key="next_main", use_container_width=True):
            update_idx(st.session_state.chart_idx + 1)
            st.rerun()

        st.subheader(f"{chart_selection}")

        if chart_inst.description:
            st.caption(chart_inst.description)

        with st.spinner(f"Rendering {chart_selection}..."):
            try:
                # render method returns a Plotly Figure
                fig = chart_inst.render(force_update=refresh_data)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error rendering {chart_selection}: {e}")
                st.code(traceback.format_exc())

        # Description editor
        with st.expander("📝 Edit Description", expanded=False):
            new_description = st.text_area(
                "Description",
                value=chart_inst.description or "",
                height=100,
                key=f"desc_{chart_selection}",
                label_visibility="collapsed",
            )

            if st.button("💾 Save Description", key=f"save_desc_{chart_selection}"):
                try:
                    with Session() as s:
                        db_chart = (
                            s.query(Chart).filter(Chart.code == chart_inst.code).first()
                        )
                        if db_chart:
                            db_chart.description = new_description
                            s.commit()
                            chart_inst.description = new_description
                            st.success("Description saved!")
                            st.rerun()
                        else:
                            st.error("Chart not found in database")
                except Exception as e:
                    st.error(f"Failed to save: {e}")

        # Optional save button for figure
        if st.sidebar.button("Save Figure to Database"):
            try:
                with Session() as s:
                    # Re-attach object to session
                    merged_chart = s.merge(chart_inst)
                    # Update figure (renders and sets .figure)
                    merged_chart.update_figure()
                    s.commit()
                    # Update local instance to reflect changes
                    chart_inst.figure = merged_chart.figure
                st.sidebar.success(f"Saved {chart_selection} to DB!")
            except Exception as e:
                st.sidebar.error(f"Failed to save: {e}")

else:
    if not flat_charts:
        st.info("No charts available.")
    else:
        st.info(
            "Investment-X Research Gallery: Displaying all available analytical charts."
        )

        # Categorical Sidebar Navigation (Anchor shortcuts)
        st.sidebar.markdown("### Navigation")

        for cat_name in sorted_cats:
            st.sidebar.markdown(
                f"- [{cat_name}](#{cat_name.lower().replace(' ', '-').replace('&', '')})"
            )

        for cat_name in sorted_cats:
            charts_map = categories[cat_name]

            # Create an anchor for navigation
            anchor_name = cat_name.lower().replace(" ", "-").replace("&", "")
            st.header(cat_name, anchor=anchor_name)
            st.divider()

            for chart_name in sorted(charts_map.keys()):
                chart_inst = charts_map[chart_name]

                with st.container():
                    st.markdown(f"### {chart_name}")

                    if chart_inst.description:
                        st.caption(chart_inst.description)

                    try:
                        # Rendering with unique keys and container optimization
                        fig = chart_inst.render(force_update=refresh_data)

                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key=f"all_chart_{cat_name}_{chart_name}",
                        )

                    except Exception as e:
                        st.error(f"Failed to render {chart_name}: {e}")

                    st.divider()
