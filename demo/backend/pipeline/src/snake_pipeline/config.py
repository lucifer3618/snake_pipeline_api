from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = Path(path) if path else ROOT / "config" / "species.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    species = list(data["species"])
    venom = [int(data["venom_labels"][name]) for name in species]
    if len(species) != 8 or len(set(species)) != len(species):
        raise ValueError("Configuration must contain eight unique species")
    if any(value not in (0, 1) for value in venom):
        raise ValueError("Venom labels must be binary")
    return species, venom


SPECIES, VENOM_LOOKUP = load_config()
