# Fake News Detector

A credibility scoring system for news articles, built in Python. Combines rule-based NLP analysis with TF-IDF similarity against a labeled reference corpus of ~45,000 articles.

## What it does

Paste any article and get:
- A **score from 0 to 100**
- A verdict: **FAKE**, **DOUTEUX** (uncertain), or **FIABLE** (reliable)
- A **line-by-line breakdown** of what affected the score
- The **most similar reference articles** from the ISOT dataset with match percentages

## How it works

**Layer 1 — NLP analysis**
The `Analyseur` class processes the raw text through a pipeline: cleaning → tokenization → stop word removal → frequency counting → suspect word detection → source detection. It produces 7 indicators that feed the scoring engine.

**Layer 2 — Scoring**
The `Score` class applies transparent rules starting from a base of 50:

| Rule | Effect |
|---|---|
| Sources cited | +20 |
| Long text (≥ 100 words) | +10 |
| Rich vocabulary (≥ 30 unique words) | +10 |
| Per suspect word (max 5) | −8 |
| Very short text (< 20 words) | −15 |
| High suspect ratio (> 15%) | −10 |
| Similarity adjustment | −20 to +20 |

Verdict thresholds: `< 40` → FAKE · `40–69` → DOUTEUX · `≥ 70` → FIABLE

**Layer 3 — Similarity**
The `MoteurSimilarite` class vectorizes the article using TF-IDF and computes cosine similarity against the full ISOT corpus. If the best match is ≥ 70% and the top matches are mostly fake, the score is adjusted downward (and upward for mostly real). The model is built once and cached for the session.

**Layer 4 — Persistence**
SQLite database via `BaseDeDonnees`. Every analysis is saved automatically. The reference corpus is imported in bulk using `executemany` — 44,898 articles in ~1.7 seconds.

## Architecture

```
Interface Web (Flask — app.py)
        ↓
Traitement (Analyseur · Score · MoteurSimilarite)
        ↓
Données (BaseDeDonnees · ImportateurDataset)
        ↓
Modèle (Article)
```

## Running it

**Web interface**
```bash
pip install flask scikit-learn
python app.py
# Open http://127.0.0.1:5000
```

**Console interface**
```bash
python main.py
```

## Reference dataset

The similarity engine uses the [ISOT Fake News Dataset](https://www.uvic.ca/engineering/ece/isot/datasets/fake-news/index.php). Place `Fake.csv` and `True.csv` in `data/dataset/` and use option 3 in the console menu (or it can be triggered from the web interface).

The dataset folder is excluded from the repository (`.gitignore`).

## Tests

```bash
pip install pytest hypothesis scikit-learn
pytest tests/
```

116 tests — unit tests per class, property-based tests with Hypothesis, and end-to-end integration tests.

## Stack

- Python 3.11
- Flask 3.x
- scikit-learn (optional — graceful degradation if absent)
- SQLite (via built-in `sqlite3`)
- pytest + Hypothesis

## Authors

**Ali Chahboubi** & **Mohammed Amine Karmouch**  
ENSIAS — Université Mohammed V de Rabat · 2025–2026
