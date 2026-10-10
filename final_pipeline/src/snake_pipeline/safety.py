DEFAULT_THRESHOLDS = {
    "detector_confidence": .25,
    "species_confidence": .60,
    "secondary_detector_confidence": 0.40,
    "species_margin": .15,
    "agreement": .60, 
    "maximum_entropy": .75
    }


def gate(prediction, thresholds=None):
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    reasons = []

    # Extract the detector stage from the prediction
    detector_stage = prediction.get("detector_stage")

    # Determine the minimum detector confidence based on the detector stage
    if detector_stage == "secondary_retry":
        minimum_detector_confidence = thresholds[
            "secondary_detector_confidence"
        ]
    else:
        minimum_detector_confidence = thresholds[
            "detector_confidence"
        ]

    # Check if the detector confidence is below the minimum threshold according to the detector stage
    if float(prediction.get("detector_confidence", 0)) < minimum_detector_confidence:
        reason = (
            "low_secondary_detector_confidence"
            if detector_stage == "secondary_retry"
            else "low_detector_confidence"
        )
        reasons.append(reason)

    # Check the other safety thresholds
    if prediction["species_confidence"] < thresholds["species_confidence"]:
        reasons.append("low_species_confidence")
    if prediction["species_margin"] < thresholds["species_margin"]:
        reasons.append("small_species_margin")
    if prediction["agreement"] < thresholds["agreement"]:
        reasons.append("low_fold_agreement")
    if prediction["normalized_entropy"] > thresholds["maximum_entropy"]:
        reasons.append("high_predictive_entropy")
    if not prediction["venom_consistent"]:
        reasons.append("species_venom_contradiction")

    return "WITHHOLD" if reasons else "ACCEPT", reasons
