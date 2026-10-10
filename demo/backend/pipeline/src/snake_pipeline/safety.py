DEFAULT_THRESHOLDS = {
    "primary_detector_confidence": .25,
    "secondary_detector_confidence": .40,
    "species_confidence": .60,
    "species_margin": .15,
    "agreement": .60,
    "maximum_entropy": .75
    }


def gate(prediction, thresholds=None):
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}; 
    reasons = []

    # Setup the minimum detector confidence based on the detector stage
    detector_stage = prediction.get("detector_stage")

    if detector_stage == "secondary_retry":
        minimum_detector_confidence = thresholds["secondary_detector_confidence"]
    else:
        minimum_detector_confidence = thresholds["detector_confidence"]

    if float(prediction.get("detector_confidence", 0)) < minimum_detector_confidence:
        reason = (
            "low_secondary_detector_confidence" if detector_stage == "secondary_retry"
            else "low_detector_confidence"
        )
        reasons.append(reason)
    
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
