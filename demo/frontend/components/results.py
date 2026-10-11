"""Detector-guided pipeline result panels."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image

from config import REASON_LABELS
from utils.standerdize import card, display_species, milliseconds, percentage


def _render_summary(result: dict[str, Any]) -> None:
    accepted = result.get("decision") == "ACCEPT"
    columns = st.columns(4)
    with columns[0]:
        card("Candidate species", display_species(result.get("predicted_species")), "Eight-class ensemble output")
    with columns[1]:
        card("Species confidence", percentage(result.get("species_confidence"), 2), "Mean ensemble probability")
    with columns[2]:
        card("Core pipeline latency", milliseconds(result.get("processing_ms")), "Artifacts excluded")
    with columns[3]:
        card(
            "Safety decision",
            "Passed safety checks" if accepted else "Identification withheld",
            "Candidate may be displayed" if accepted else "Candidate remains diagnostic only",
        )
    if not accepted:
        reasons = result.get("reasons") or ["The configured safety conditions were not satisfied."]
        st.warning("Prediction withheld: " + " ".join(REASON_LABELS.get(reason, reason) for reason in reasons))


def render_pipeline_result(image: Image.Image, result: dict[str, Any]) -> None:
    with st.container(border=True):
        _render_summary(result)
