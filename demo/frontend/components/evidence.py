import pandas as pd
import streamlit as st

from config import BENCHMARK_METRICS, FOLD_MACRO_F1


def render_research_evidence() -> None:
    with st.container(border=True):
        st.markdown("## Validated research evidence")
        summary = st.columns(4)
        summary[0].metric("Whole-image macro F1", "0.8019")
        summary[1].metric("ROI macro F1", "0.8394", "+3.75 pp")
        summary[2].metric("Whole-image accuracy", "0.7997")
        summary[3].metric("ROI accuracy", "0.8375", "+3.78 pp")
        st.caption(
            "Matched five-fold evaluation using identical source images, fold assignments, architecture, "
            "loss configuration and training conditions. These aggregate results do not imply that ROI "
            "processing performs better on every individual image."
        )
        with st.expander("View five-fold performance charts", expanded=False):
            rows = []
            # Iterate through the benchmark metrics and create rows for the aggregate DataFrame
            for metric, (whole_value, roi_value) in BENCHMARK_METRICS.items():
                rows.extend(
                    [
                        {"Metric": metric, "Strategy": "Whole image", "Score": whole_value},
                        {"Metric": metric, "Strategy": "Detector-extracted ROI", "Score": roi_value},
                    ]
                )
            aggregate = pd.DataFrame(rows)

            # Create a DataFrame for the fold-wise macro F1 scores, with separate columns 
            # for whole image and ROI strategies
            folds = pd.DataFrame(
                {
                    "Whole image": [values[0] for values in FOLD_MACRO_F1.values()],
                    "Detector-extracted ROI": [values[1] for values in FOLD_MACRO_F1.values()],
                },
                index=list(FOLD_MACRO_F1),
            )

            # Create two columns in the Streamlit layout to display seperate charts
            left, right = st.columns(2, gap="large")
          
            with left:
                st.markdown("#### Aggregate five-fold metrics")
                st.bar_chart(aggregate, x="Metric", y="Score", color="Strategy", stack=False, height=330)
                st.caption("ROI classification achieved the higher mean value for every reported metric.")
            with right:
                st.markdown("#### Fold-wise macro F1")
                st.line_chart(folds, height=330)
                st.caption("The ROI strategy improved macro F1 in all five matched folds.")
