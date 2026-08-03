import pytest

from app.classifier import ClassifierUnavailable, LABELS, ToxicityClassifier


def test_expected_model_labels_are_preserved():
    mapping = {index: label for index, label in enumerate(LABELS)}
    assert ToxicityClassifier._resolve_label_order(mapping) == LABELS


def test_generic_transformer_labels_use_verified_checkpoint_order():
    mapping = {index: f"LABEL_{index}" for index in range(6)}
    assert ToxicityClassifier._resolve_label_order(mapping) == LABELS


def test_label_order_can_differ_without_changing_canonical_api_order():
    mapping = {
        0: "insult",
        1: "toxic",
        2: "threat",
        3: "obscene",
        4: "identity_hate",
        5: "severe_toxic",
    }
    assert ToxicityClassifier._resolve_label_order(mapping) == tuple(mapping.values())


def test_incompatible_checkpoint_fails_closed():
    with pytest.raises(ClassifierUnavailable, match="label contract"):
        ToxicityClassifier._resolve_label_order({0: "negative", 1: "positive"})


@pytest.mark.parametrize("threshold", [0, 1, -0.1, 1.1])
def test_invalid_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        ToxicityClassifier(threshold=threshold)
