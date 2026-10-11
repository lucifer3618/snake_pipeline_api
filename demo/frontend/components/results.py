"""Detector-guided pipeline result panels."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image

from config import REASON_LABELS, SAFETY_THRESHOLDS
from utils.standerdize import card, display_species, milliseconds, percentage, decode_artifact

# This function takes in a result dictionary and renders a summary of the pipeline result
def _render_summary(result: dict[str, Any]) -> None:
    # ckeck if the decision is "ACCEPT" and store it in a variable
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

# This function takes a PIL image object and results then map each stage of the pipeline
def _render_stages(image: Image.Image, result: dict[str, Any]) -> None:
    st.markdown("### Pipeline evidence")
    stage = st.radio(
        "Pipeline evidence stage",
        ["Original image", "Mask overlay", "Extracted ROI", "Grad-CAM"],
        horizontal=True,
        label_visibility="collapsed",
        key="pipeline_stage"
    )
    artifact_mapping = {
        "Mask overlay": "mask_overlay", 
        "Extracted ROI": "roi_crop", 
        "Grad-CAM": "gradcam_overlay"
    }
    captions = {
        "Original image": "Original uploaded image",
        "Mask overlay": "Instance-segmentation mask returned by the successful detector stage",
        "Extracted ROI": "Healed-mask crop with 1.30x proportional context",
        "Grad-CAM": "Five-fold averaged attention map; qualitative evidence rather than an accuracy measure",
    }
    # if selected stage is "Original image" then display the original image else decode the artifact and display it
    selected = image if stage == "Original image" else decode_artifact(result.get(artifact_mapping[stage]))
    if selected is None:
        st.info(f"{stage} was not requested. Enable it above and run the pipeline again.")
    else:
        st.image(selected, caption=captions[stage], width="stretch")

def _safety_rows(result: dict[str, Any]) -> list[tuple[str, str, bool]]:
    detector_threshold = (
        SAFETY_THRESHOLDS["secondary_detector_confidence"]
        if result.get("detector_stage") == "secondary_retry"
        else SAFETY_THRESHOLDS["detector_confidence"]
    )
    return [
        ("Detector confidence", f"≥ {detector_threshold:.2f}",
         (result.get("detector_confidence") or 0) >= detector_threshold),
        ("Species confidence", f"≥ {SAFETY_THRESHOLDS['species_confidence']:.2f}",
         (result.get("species_confidence") or 0) >= SAFETY_THRESHOLDS["species_confidence"]),
        ("Prediction margin", f"≥ {SAFETY_THRESHOLDS['species_margin']:.2f}",
         (result.get("species_margin") or 0) >= SAFETY_THRESHOLDS["species_margin"]),
        ("Fold agreement", f"= {SAFETY_THRESHOLDS['agreement']:.2f}",
         (result.get("agreement") or 0) >= SAFETY_THRESHOLDS["agreement"]),
        ("Normalized entropy", f"≤ {SAFETY_THRESHOLDS['maximum_entropy']:.2f}",
         (result.get("normalized_entropy") if result.get("normalized_entropy") is not None else 1)
         <= SAFETY_THRESHOLDS["maximum_entropy"]),
        ("Species–venom consistency", "required", result.get("venom_consistent") is True),
    ]

def _render_safety_gate(result: dict[str, Any]) -> None:
    rows = _safety_rows(result)
    st.markdown(f"### Safety gate · {sum(ok for _, _, ok in rows)} / {len(rows)} passed")
    for label, threshold, condition in rows:
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"**{label}**")
            st.caption(threshold)
        with right:
            st.markdown("✅ **Pass**" if condition else "❌ **Fail**")
        st.divider()

def render_pipeline_result(image: Image.Image, result: dict[str, Any]) -> None:
    with st.container(border=True):
        _render_summary(result)

    left, right = st.columns([2.1, 1], gap="large")
    with left:
        with st.container(border=True):
            _render_stages(image, result)
    with right:
        with st.container(border=True):
            _render_safety_gate(result)
            st.markdown("#### Timing boundary")
            st.metric("Core processing", milliseconds(result.get("processing_ms")))
            if result.get("artifact_processing_ms") is not None:
                st.metric("Optional artifacts", milliseconds(result.get("artifact_processing_ms")))
            st.caption(
                "Runtime depends on the current hardware and includes detection, ROI extraction, "
                "ensemble inference and safety checks."
            )
