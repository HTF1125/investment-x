"""
Enhanced Insights Page Layout
Modern design with improved UX, incorporating features from wx implementation.
"""

from dash import html, dcc
import dash
from ix.dash.pages.insights.callbacks_minimal import *
from ix.dash.pages.insights.summary_modal import summary_modal
from ix.dash.pages.insights import sources

# Register Page
dash.register_page(__name__, path="/insights", title="Insights", name="Insights")


# Simple icon function
def Icon(icon_name, width=16):
    """Simple icon replacement using Font Awesome"""
    icon_map = {
        "tabler:search": "fas fa-search",
        "tabler:filter-off": "fas fa-times",
        "tabler:refresh": "fas fa-sync-alt",
        "tabler:file-text": "fas fa-file-text",
        "tabler:clock": "fas fa-clock",
        "tabler:check": "fas fa-check",
        "tabler:calendar": "fas fa-calendar",
        "tabler:upload": "fas fa-upload",
        "tabler:cloud-upload": "fas fa-cloud-upload-alt",
    }
    return html.I(
        className=icon_map.get(icon_name, "fas fa-question"),
        style={"fontSize": f"{width}px", "marginRight": "8px"},
    )


# Main Layout
layout = html.Div(
    [
        # Compact File Upload Section
        html.Div(
            [
                html.Div(
                    [
                        Icon("tabler:upload", width=20),
                        html.H5(
                            "📁 Upload Documents",
                            style={
                                "color": "#ffffff",
                                "margin": "0",
                                "fontSize": "16px",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "marginBottom": "12px",
                    },
                ),
                dcc.Upload(
                    html.Div(
                        [
                            Icon("tabler:cloud-upload", width=24),
                            html.Span(
                                "Drop PDF files here or click to browse",
                                style={
                                    "color": "#ffffff",
                                    "fontSize": "14px",
                                    "marginLeft": "8px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "PDF only",
                                        style={
                                            "color": "#10b981",
                                            "fontSize": "11px",
                                            "marginRight": "8px",
                                        },
                                    ),
                                    html.Span(
                                        "Max 10MB",
                                        style={"color": "#3b82f6", "fontSize": "11px"},
                                    ),
                                ],
                                style={"marginLeft": "8px", "opacity": "0.8"},
                            ),
                        ],
                        style={
                            "padding": "16px 20px",
                            "border": "2px dashed #475569",
                            "borderRadius": "8px",
                            "backgroundColor": "rgba(59, 130, 246, 0.05)",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "flexWrap": "wrap",
                        },
                        className="upload-hover-effect",
                    ),
                    id="upload-pdf",
                    multiple=False,
                    accept=".pdf",
                ),
                html.Div(id="output-pdf-upload", style={"marginTop": "12px"}),
            ],
            style={
                "backgroundColor": "#1e293b",
                "padding": "16px",
                "borderRadius": "8px",
                "border": "1px solid #475569",
                "marginBottom": "16px",
            },
        ),
        # Search and Filters Section - Now at the top
        html.Div(
            [
                html.H4(
                    "🔍 Search & Filter Insights",
                    style={"color": "#ffffff", "margin": "0 0 20px 0"},
                ),
                # Search bar
                html.Div(
                    [
                        html.Div(
                            Icon("tabler:search", width=16),
                            style={
                                "position": "absolute",
                                "left": "12px",
                                "top": "50%",
                                "transform": "translateY(-50%)",
                                "color": "#888",
                            },
                        ),
                        dcc.Input(
                            placeholder="Search insights...",
                            id="insights-search",
                            style={
                                "backgroundColor": "#0f172a",
                                "border": "1px solid #475569",
                                "borderRadius": "8px",
                                "color": "#ffffff",
                                "fontSize": "14px",
                                "width": "100%",
                                "padding": "8px 12px 8px 35px",
                                "outline": "none",
                                "marginBottom": "15px",
                            },
                        ),
                    ],
                    style={"position": "relative"},
                ),
                # Filter controls in horizontal layout
                html.Div(
                    [
                        html.Div(
                            [
                                html.Button(
                                    [Icon("tabler:search", width=16), "Search"],
                                    id="search-button",
                                    style={
                                        "backgroundColor": "#3b82f6",
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "color": "#ffffff",
                                        "padding": "8px 16px",
                                        "cursor": "pointer",
                                        "fontSize": "14px",
                                        "display": "inline-flex",
                                        "alignItems": "center",
                                        "width": "100%",
                                    },
                                ),
                            ],
                            style={"flex": "0 0 120px", "marginRight": "10px"},
                        ),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    options=[
                                        {
                                            "label": "Date (Newest)",
                                            "value": "date_desc",
                                        },
                                        {
                                            "label": "Date (Oldest)",
                                            "value": "date_asc",
                                        },
                                        {
                                            "label": "Name (A-Z)",
                                            "value": "name_asc",
                                        },
                                        {
                                            "label": "Name (Z-A)",
                                            "value": "name_desc",
                                        },
                                    ],
                                    placeholder="Sort by",
                                    id="sort-dropdown",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={"flex": "1", "marginRight": "10px"},
                        ),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    options=[
                                        {"label": "All", "value": "all"},
                                        {
                                            "label": "Goldman Sachs",
                                            "value": "gs",
                                        },
                                        {"label": "JP Morgan", "value": "jpm"},
                                        {
                                            "label": "Morgan Stanley",
                                            "value": "ms",
                                        },
                                    ],
                                    placeholder="All issuers",
                                    id="issuer-filter",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={"flex": "1", "marginRight": "10px"},
                        ),
                        html.Div(
                            [
                                dcc.DatePickerRange(
                                    id="date-range-filter",
                                    display_format="YYYY-MM-DD",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                    },
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "10px",
                        "flexWrap": "wrap",
                    },
                ),
            ],
            style={
                "backgroundColor": "#1e293b",
                "padding": "20px",
                "borderRadius": "12px",
                "border": "1px solid #475569",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
                "marginBottom": "20px",
            },
        ),
        # Insights Section - Now with scrollable container
        html.Div(
            [
                html.Div(
                    [
                        html.H4(
                            "📄 Recent Insights",
                            style={"color": "#ffffff", "margin": "0"},
                        ),
                        html.Button(
                            [Icon("tabler:refresh", width=16), "Load More"],
                            id="load-more-insights",
                            style={
                                "backgroundColor": "transparent",
                                "border": "1px solid #475569",
                                "borderRadius": "8px",
                                "color": "#ffffff",
                                "padding": "8px 16px",
                                "cursor": "pointer",
                                "fontSize": "14px",
                                "display": "inline-flex",
                                "alignItems": "center",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "20px",
                    },
                ),
                # Scrollable insights container
                html.Div(
                    [
                        html.Div(id="insights-container-wrapper"),
                        html.Div(id="insights-container"),
                    ],
                    style={
                        "maxHeight": "600px",
                        "overflowY": "auto",
                        "overflowX": "hidden",
                        "paddingRight": "10px",
                        "scrollbarWidth": "thin",
                        "scrollbarColor": "#475569 #1e293b",
                    },
                ),
            ],
            style={
                "backgroundColor": "#1e293b",
                "padding": "20px",
                "borderRadius": "12px",
                "border": "1px solid #475569",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
                "marginBottom": "20px",
            },
        ),
        # Enhanced Sources Section - Now at the bottom
        sources.layout,
        # Enhanced modal for summary viewing
        summary_modal,
        # Hidden stores for callback state management
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        dcc.Store(id="filter-state", data={}),
        # Enhanced Text-to-Speech functionality
        html.Script(
            """
            // Enhanced Text-to-Speech functionality with improved error handling
            document.addEventListener("DOMContentLoaded", function() {
                let currentUtterance = null;
                let isReading = false;

                function initializeSpeechButtons() {
                    const readBtn = document.getElementById("read-summary");
                    const stopBtn = document.getElementById("stop-summary");

                    if (readBtn && stopBtn) {
                        readBtn.addEventListener("click", function() {
                            const modalBody = document.getElementById("modal-body-content");
                            const summary = modalBody ? modalBody.innerText.trim() : "";

                            if (summary.length > 0 && window.speechSynthesis) {
                                // Stop any current speech
                                window.speechSynthesis.cancel();

                                // Update button states
                                readBtn.disabled = true;
                                readBtn.innerHTML = '<i class="fas fa-pause" style="margin-right: 8px;"></i>Reading...';
                                readBtn.className = readBtn.className.replace('btn-success', 'btn-warning');

                                // Create and configure utterance
                                currentUtterance = new SpeechSynthesisUtterance(summary);
                                currentUtterance.rate = 0.9;
                                currentUtterance.pitch = 1.0;
                                currentUtterance.volume = 1.0;

                                // Set up event handlers
                                currentUtterance.onend = function() {
                                    resetSpeechUI();
                                };

                                currentUtterance.onerror = function(event) {
                                    console.error('Speech synthesis error:', event);
                                    resetSpeechUI();
                                    alert('Speech synthesis failed. Please try again.');
                                };

                                // Start speaking
                                window.speechSynthesis.speak(currentUtterance);
                                isReading = true;
                            } else if (!window.speechSynthesis) {
                                alert("Text-to-speech is not supported in your browser.");
                            } else {
                                alert("No content to read.");
                            }
                        });

                        stopBtn.addEventListener("click", function() {
                            if (window.speechSynthesis) {
                                window.speechSynthesis.cancel();
                                resetSpeechUI();
                            }
                        });
                    }
                }

                function resetSpeechUI() {
                    const readBtn = document.getElementById("read-summary");

                    if (readBtn) {
                        readBtn.disabled = false;
                        readBtn.innerHTML = '<i class="fas fa-play" style="margin-right: 8px;"></i>Read Aloud';
                        readBtn.className = readBtn.className.replace('btn-warning', 'btn-success');
                    }

                    isReading = false;
                    currentUtterance = null;
                }

                // Initialize on page load
                setTimeout(initializeSpeechButtons, 1000);

                // Re-initialize when modal opens
                const modal = document.getElementById("insight-modal");
                if (modal) {
                    // For Bootstrap 5 modals
                    modal.addEventListener("shown.bs.modal", function() {
                        setTimeout(initializeSpeechButtons, 200);
                    });

                    modal.addEventListener("hidden.bs.modal", function() {
                        if (window.speechSynthesis && isReading) {
                            window.speechSynthesis.cancel();
                        }
                        resetSpeechUI();
                    });
                }

                // Add CSS for upload hover effects
                const style = document.createElement('style');
                style.textContent = `
                    .upload-hover-effect:hover {
                        border-color: #3b82f6 !important;
                        background-color: rgba(59, 130, 246, 0.1) !important;
                        transform: translateY(-2px);
                        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
                    }

                    .insight-card-hover:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
                        border-color: #3b82f6 !important;
                    }

                    .source-item-hover:hover {
                        background-color: rgba(59, 130, 246, 0.08) !important;
                        border-left: 3px solid #3b82f6 !important;
                        padding-left: 13px !important;
                    }

                    .source-item-hover:hover button {
                        background-color: #2563eb !important;
                        transform: scale(1.05);
                    }

                    /* Custom scrollbar styling for webkit browsers */
                    #insights-container::-webkit-scrollbar {
                        width: 8px;
                    }

                    #insights-container::-webkit-scrollbar-track {
                        background: #1e293b;
                        border-radius: 4px;
                    }

                    #insights-container::-webkit-scrollbar-thumb {
                        background: #475569;
                        border-radius: 4px;
                    }

                    #insights-container::-webkit-scrollbar-thumb:hover {
                        background: #64748b;
                    }

                    /* Modern modal styling */
                    .modern-modal .modal-content {
                        background: linear-gradient(135deg, #1e293b 0%, #334155 100%) !important;
                        border: 1px solid #475569 !important;
                        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
                    }

                    .modern-modal .modal-backdrop {
                        background-color: rgba(0, 0, 0, 0.8) !important;
                        backdrop-filter: blur(4px) !important;
                    }

                    .modern-modal .modal-dialog {
                        animation: modalSlideIn 0.3s ease-out !important;
                    }

                    @keyframes modalSlideIn {
                        from {
                            transform: translateY(-50px) translateX(-50%) scale(0.95);
                            opacity: 0;
                        }
                        to {
                            transform: translateY(0) translateX(-50%) scale(1);
                            opacity: 1;
                        }
                    }
                `;
                document.head.appendChild(style);
            });
            """
        ),
    ],
    style={
        "backgroundColor": "#0f172a",
        "color": "#ffffff",
        "minHeight": "100vh",
        "paddingTop": "90px",  # Account for fixed navbar
        "paddingBottom": "40px",
        "paddingLeft": "20px",
        "paddingRight": "20px",
    },
)
