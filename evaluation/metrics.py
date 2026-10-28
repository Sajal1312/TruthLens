"""Small dependency-free metrics used by the TruthLens offline evaluation."""

LABELS = ("SUPPORTED", "CONTRADICTED", "INCONCLUSIVE")
STANCE_LABELS = ("SUPPORTS", "CONTRADICTS", "NOT ENOUGH INFORMATION")
RELEVANCE_LABELS = ("relevant", "weakly_related", "unrelated")


def classification_metrics(expected, predicted, labels):
    """Return confusion matrix and metrics with undefined classes represented as None.

    Macro-F1 averages only labels present in the expected (gold) data. This
    prevents absent classes from silently depressing the score; the included
    class count and supports make that averaging choice explicit.
    """
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")
    matrix = {actual: {guess: 0 for guess in labels} for actual in labels}
    for actual, guess in zip(expected, predicted):
        if actual not in matrix or guess not in matrix:
            raise ValueError("unknown classification label")
        matrix[actual][guess] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in labels if actual != label)
        fn = sum(matrix[label][guess] for guess in labels if guess != label)
        support = sum(matrix[label].values())
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if support else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and precision + recall else
              0.0 if support else None)
        per_class[label] = {"support": support, "precision": precision,
                            "recall": recall, "f1": f1}
    supported_f1 = [item["f1"] for item in per_class.values()
                    if item["support"] and item["f1"] is not None]
    return {"count": len(expected), "labels": list(labels), "confusion_matrix": matrix,
            "per_class": per_class,
            "macro_f1": sum(supported_f1) / len(supported_f1) if supported_f1 else None,
            "macro_f1_class_count": len(supported_f1),
            "macro_f1_labels": [label for label, item in per_class.items()
                                if item["support"] and item["f1"] is not None],
            "accuracy": sum(a == p for a, p in zip(expected, predicted)) / len(expected) if expected else None}


def selective_metrics(expected, predicted):
    """Final-label exact match plus directional accuracy, coverage and abstention."""
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")
    total = len(predicted)
    directional = [(a, p) for a, p in zip(expected, predicted) if p != "INCONCLUSIVE"]
    correct_directional = sum(a == p for a, p in directional)
    return {
        "count": total,
        "selective_count": len(directional),
        "selective_accuracy": correct_directional / len(directional) if directional else None,
        "coverage": len(directional) / total if total else None,
        "abstention_rate": sum(p == "INCONCLUSIVE" for p in predicted) / total if total else None,
    }
