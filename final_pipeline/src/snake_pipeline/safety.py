DEFAULT_THRESHOLDS = {"detector_confidence": .25, "species_confidence": .60, "species_margin": .15,
                      "agreement": .60, "maximum_entropy": .75}


def gate(prediction, thresholds=None):
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}; reasons = []
    if float(prediction.get("detector_confidence", 0)) < thresholds["detector_confidence"]: reasons.append("low_detector_confidence")
    if prediction["species_confidence"] < thresholds["species_confidence"]: reasons.append("low_species_confidence")
    if prediction["species_margin"] < thresholds["species_margin"]: reasons.append("small_species_margin")
    if prediction["agreement"] < thresholds["agreement"]: reasons.append("low_fold_agreement")
    if prediction["normalized_entropy"] > thresholds["maximum_entropy"]: reasons.append("high_predictive_entropy")
    if not prediction["venom_consistent"]: reasons.append("species_venom_contradiction")
    return "WITHHOLD" if reasons else "ACCEPT", reasons
