
"""
STEP 31A — SYNTHETIC AI CLASSIFICATION EVALUATION

Reads existing CSV files without modifying them.
Does not call Ollama or modify SQLite.

Run:
    python evaluate_ai.py
"""

from pathlib import Path
from datetime import datetime
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
OUTPUT = ROOT / "Output"

GROUND_TRUTH_FILE = DATA / "ground_truth.csv"
PREDICTION_CANDIDATES = [
    OUTPUT / "hybrid_predictions.csv",
    OUTPUT / "ai_predictions.csv",
]

# Use hybrid predictions when available because the
# earlier prototype produced a hybrid output.
# Hybrid dependency agreement must be reported separately
# from raw Ollama agreement.
PRIMARY_PREDICTION_FILE = next(
    (p for p in PREDICTION_CANDIDATES if p.exists()),
    None
)

CATEGORY_ALIASES = {
    "case_type": [
        "case_type",
        "category",
        "true_category",
        "actual_category",
        "ground_truth_category",
        "expected_category",
        "category_ground_truth",
        "case_type_ground_truth",
        "case_type_gt",
        "category_gt",
        "label_category",
        "gt_category",
    ],
    "state": [
        "state",
        "true_state",
        "actual_state",
        "ground_truth_state",
        "expected_state",
        "state_ground_truth",
        "state_gt",
        "label_state",
        "gt_state",
    ],
    "dependency": [
        "dependency",
        "true_dependency",
        "actual_dependency",
        "ground_truth_dependency",
        "expected_dependency",
        "dependency_ground_truth",
        "dependency_gt",
        "label_dependency",
        "gt_dependency",
    ],
}

PREDICTION_ALIASES = {
    "case_type": [
        "predicted_case_type",
        "predicted_category",
        "ai_category",
        "ai_case_type",
        "hybrid_case_type",
        "final_case_type",
        "case_type_prediction",
        "category_prediction",
    ],
    "state": [
        "predicted_state",
        "ai_state",
        "hybrid_state",
        "final_state",
        "state_prediction",
    ],
    "dependency": [
        "hybrid_dependency",
        "final_dependency",
        "rule_based_dependency",
        "predicted_dependency",
        "ai_dependency",
        "dependency_prediction",
    ],
}

FIELDS = ["case_type", "state", "dependency"]


def read_csv(path):
    if path is None or not path.exists():
        raise FileNotFoundError(
            f"Required input not found: {path}"
        )

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig"
    )

    df.columns = [
        str(col).strip().lower()
        .replace(" ", "_")
        .replace("-", "_")
        for col in df.columns
    ]

    if "case_id" not in df.columns:
        raise ValueError(
            f"{path.name} has no case_id column.\n"
            f"Available columns: {list(df.columns)}"
        )

    df["case_id"] = df["case_id"].str.strip()

    if df["case_id"].eq("").any():
        raise ValueError(
            f"{path.name} contains blank case IDs."
        )

    duplicate_ids = df.loc[
        df["case_id"].duplicated(keep=False),
        "case_id"
    ].unique().tolist()

    if duplicate_ids:
        raise ValueError(
            f"Duplicate case IDs in {path.name}: "
            f"{duplicate_ids[:10]}"
        )

    return df


def find_column(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    return None


def normalize(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in {
        "", "nan", "null", "not specified",
        "unknown", "not available"
    }:
        return ""

    return " ".join(value.split()).casefold()


def make_comparison(truth, predictions):
    truth_ids = set(truth["case_id"])
    prediction_ids = set(predictions["case_id"])

    matched_ids = truth_ids & prediction_ids

    if not matched_ids:
        raise ValueError(
            "No matching case IDs between ground truth "
            "and predictions."
        )

    merged = truth.merge(
        predictions,
        on="case_id",
        how="left",
        suffixes=("_truth_source", "_prediction_source"),
        indicator=True,
        validate="one_to_one"
    )

    result = pd.DataFrame({
        "case_id": merged["case_id"],
        "prediction_record_found": (
            merged["_merge"] == "both"
        )
    })

    source_columns = {}
    field_coverage = {}

    for field in FIELDS:
        true_col = find_column(
            truth,
            CATEGORY_ALIASES[field]
        )

        pred_col = find_column(
            predictions,
            PREDICTION_ALIASES[field]
        )

        if true_col is None:
            raise ValueError(
                f"No reference column for '{field}'.\n"
                f"ground_truth.csv columns: "
                f"{list(truth.columns)}"
            )

        if pred_col is None:
            raise ValueError(
                f"No prediction column for '{field}'.\n"
                f"{PRIMARY_PREDICTION_FILE.name} columns: "
                f"{list(predictions.columns)}"
            )

        # Identify columns after merge, including cases
        # where both files contain the same column name.
        def merged_name(name, source):
            if name in truth.columns and name in predictions.columns:
                suffix = (
                    "_truth_source"
                    if source == "truth"
                    else "_prediction_source"
                )
                return name + suffix
            return name

        true_values = merged[
            merged_name(true_col, "truth")
        ].fillna("")

        pred_values = merged[
            merged_name(pred_col, "prediction")
        ].fillna("")

        result[f"reference_{field}"] = true_values
        result[f"predicted_{field}"] = pred_values

        valid_truth = true_values.map(normalize).ne("")
        valid_prediction = pred_values.map(normalize).ne("")

        result[f"{field}_evaluable"] = (
            valid_truth & valid_prediction
        )

        result[f"{field}_agreement"] = (
            true_values.map(normalize)
            == pred_values.map(normalize)
        ) & result[f"{field}_evaluable"]

        result[f"{field}_result"] = "Not Evaluable"

        result.loc[
            result[f"{field}_evaluable"]
            & result[f"{field}_agreement"],
            f"{field}_result"
        ] = "Agree"

        result.loc[
            result[f"{field}_evaluable"]
            & ~result[f"{field}_agreement"],
            f"{field}_result"
        ] = "Disagree"

        source_columns[field] = {
            "reference": true_col,
            "prediction": pred_col
        }

        field_coverage[field] = {
            "reference_count": int(valid_truth.sum()),
            "prediction_count": int(valid_prediction.sum())
        }

    result["any_disagreement"] = result[
        [f"{f}_result" for f in FIELDS]
    ].eq("Disagree").any(axis=1)

    result["needs_review"] = (
        result["any_disagreement"]
        | result[
            [f"{f}_evaluable" for f in FIELDS]
        ].eq(False).any(axis=1)
    )

    return (
        result,
        source_columns,
        field_coverage,
        len(matched_ids),
        sorted(truth_ids - prediction_ids),
        sorted(prediction_ids - truth_ids)
    )


def make_summary(details):
    rows = []

    for field in FIELDS:
        evaluable = details[f"{field}_evaluable"]
        agree = details[f"{field}_agreement"]

        count = int(evaluable.sum())
        agreements = int(agree.sum())
        disagreements = count - agreements

        percentage = (
            round(100 * agreements / count, 2)
            if count > 0
            else None
        )

        rows.append({
            "metric": field,
            "reference_cases": len(details),
            "evaluable_cases": count,
            "agreements": agreements,
            "disagreements": disagreements,
            "not_evaluable": len(details) - count,
            "agreement_percent": percentage
        })

    return pd.DataFrame(rows)


def make_confusion_matrix(details):
    subset = details[
        details["case_type_evaluable"]
    ].copy()

    if subset.empty:
        return pd.DataFrame()

    subset["reference_normalized"] = subset[
        "reference_case_type"
    ].map(normalize)

    subset["prediction_normalized"] = subset[
        "predicted_case_type"
    ].map(normalize)

    return pd.crosstab(
        subset["reference_normalized"],
        subset["prediction_normalized"],
        rownames=["Reference Category"],
        colnames=["Predicted Category"]
    )


def write_report(
    summary,
    details,
    sources,
    coverage,
    matched_count,
    missing_predictions,
    extra_predictions
):
    lines = [
        "AI CLASSIFICATION EVALUATION REPORT",
        "=" * 45,
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "DATA SOURCES",
        f"Reference: {GROUND_TRUTH_FILE.name}",
        f"Predictions: {PRIMARY_PREDICTION_FILE.name}",
        f"Reference cases: {len(details)}",
        f"Matched case IDs: {matched_count}",
        f"Missing prediction records: {len(missing_predictions)}",
        f"Extra prediction records: {len(extra_predictions)}",
        "",
        "AGREEMENT RESULTS",
    ]

    for _, row in summary.iterrows():
        pct = row["agreement_percent"]
        display = (
            "N/A"
            if pd.isna(pct)
            else f"{pct:.2f}%"
        )

        lines.append(
            f"{row['metric']}: {display} "
            f"({row['agreements']}/"
            f"{row['evaluable_cases']} evaluable)"
        )

        lines.append(
            f"  Not evaluable: {row['not_evaluable']}"
        )

    lines += [
        "",
        "SOURCE COLUMN MAPPING",
    ]

    for field, mapping in sources.items():
        lines.append(
            f"{field}: "
            f"reference={mapping['reference']}, "
            f"prediction={mapping['prediction']}"
        )

    lines += [
        "",
        "QUALITY CONTROL",
        f"Cases needing review: "
        f"{int(details['needs_review'].sum())}",
        f"Cases with disagreement: "
        f"{int(details['any_disagreement'].sum())}",
        "",
        "Missing prediction IDs: "
        + (", ".join(missing_predictions) or "None"),
        "Extra prediction IDs: "
        + (", ".join(extra_predictions) or "None"),
        "",
        "INTERPRETATION",
        "These results measure agreement with provisional",
        "synthetic reference labels, not real-world accuracy.",
        "The reference labels may be derived from existing",
        "case attributes or statuses.",
        "",
        "If hybrid_predictions.csv was selected, dependency",
        "results may include rule-based corrections and",
        "must not be presented as raw Ollama performance.",
        "",
        "The original dataset is synthetic.",
        "No government agency deadlines are validated here.",
        "No model training or real customer data is involved.",
    ]

    path = OUTPUT / "ai_evaluation_report.txt"
    path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return path


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("\nSTEP 31A — AI CLASSIFICATION EVALUATION")
    print("-" * 45)

    truth = read_csv(GROUND_TRUTH_FILE)

    if PRIMARY_PREDICTION_FILE is None:
        raise FileNotFoundError(
            "Neither hybrid_predictions.csv nor "
            "ai_predictions.csv exists in Output."
        )

    predictions = read_csv(PRIMARY_PREDICTION_FILE)

    print(f"Reference file: {GROUND_TRUTH_FILE.name}")
    print(
        f"Prediction file: "
        f"{PRIMARY_PREDICTION_FILE.name}"
    )

    (
        details,
        sources,
        coverage,
        matched_count,
        missing_predictions,
        extra_predictions
    ) = make_comparison(truth, predictions)

    summary = make_summary(details)
    confusion = make_confusion_matrix(details)

    summary_path = OUTPUT / "ai_evaluation_summary.csv"
    details_path = OUTPUT / "ai_evaluation_case_details.csv"
    confusion_path = (
        OUTPUT / "ai_category_confusion_matrix.csv"
    )

    summary.to_csv(summary_path, index=False)
    details.to_csv(details_path, index=False)
    confusion.to_csv(confusion_path)

    report_path = write_report(
        summary,
        details,
        sources,
        coverage,
        matched_count,
        missing_predictions,
        extra_predictions
    )

    print("\nAGREEMENT SUMMARY")
    print(summary.to_string(index=False))

    print("\nSOURCE COLUMN MAPPING")
    for field, mapping in sources.items():
        print(
            f"{field}: "
            f"{mapping['reference']} -> "
            f"{mapping['prediction']}"
        )

    print("\nQUALITY CHECKS")
    print(f"Matched case IDs: {matched_count}")
    print(
        "Cases needing review:",
        int(details["needs_review"].sum())
    )
    print(
        "Missing prediction records:",
        len(missing_predictions)
    )
    print(
        "Extra prediction records:",
        len(extra_predictions)
    )

    print("\nREPORTS CREATED")
    for path in [
        summary_path,
        details_path,
        confusion_path,
        report_path
    ]:
        print(path)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"\nEVALUATION FAILED: {exc}",
            file=sys.stderr
        )
        sys.exit(1)
