# Final bemchmart metrics
BENCHMARK_METRICS = {
    "Accuracy": (0.7997, 0.8375), "Macro precision": (0.8069, 0.8472),
    "Macro recall": (0.8005, 0.8375), "Macro F1": (0.8019, 0.8394),
}

# Foldwise macro F1 scores for the five-fold evaluation, with separate values for whole-image and ROI strategies
FOLD_MACRO_F1 = {
    "Fold 0": (0.8056, 0.8518), "Fold 1": (0.7832, 0.8522),
    "Fold 2": (0.7794, 0.8036), "Fold 3": (0.8067, 0.8478),
    "Fold 4": (0.8344, 0.8416),
}

# Mapping of reason codes to readable lables
REASON_LABELS = {
    "low_detector_confidence": "Detector confidence was below the configured threshold.",
    "low_secondary_detector_confidence": "Secondary-detector confidence was below its stricter threshold.",
    "low_species_confidence": "Species confidence was below the configured threshold.",
    "small_species_margin": "The two leading species predictions were too close.",
    "low_fold_agreement": "The five classifier folds did not fully agree.",
    "high_predictive_entropy": "The ensemble prediction was too uncertain.",
    "species_venom_contradiction": "Species and auxiliary venom predictions were inconsistent.",
}

# Safety thresholds for the pipeline
SAFETY_THRESHOLDS = {
    "detector_confidence": 0.35, "secondary_detector_confidence": 0.40,
    "species_confidence": 0.40, "species_margin": 0.05,
    "agreement": 1.00, "maximum_entropy": 0.55,
}

SPECIES = {
    "Bungarus caeruleus": "Common krait",
    "Coelognathus helena": "Trinket snake",
    "Craspedocephalus trigonocephalus": "Sri Lankan green pit viper",
    "Daboia russelii": "Russell's viper",
    "Hypnale hypnale": "Hump-nosed viper",
    "Lycodon anamallensis": "Flowery wolf snake",
    "Naja naja": "Indian cobra",
    "Oligodon arnensis": "Banded kukri snake",
}
