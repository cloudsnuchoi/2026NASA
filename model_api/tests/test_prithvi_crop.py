"""Unit tests for the pure-PyTorch Prithvi crop forward pass (random weights; checkpoint not required)."""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from model_api.vision import prithvi_crop as P  # noqa: E402


def test_classes_official_order():
    assert len(P.CLASSES) == 13
    assert P.CLASSES[2] == "Corn" and P.CLASSES[3] == "Soybeans" and P.CLASSES[0] == "Natural Vegetation"


def test_preprocess_matches_released_pipeline():
    x = np.tile(P.MEANS, (224, 224, 1))
    x[..., 6] += P.STDS[6]  # channel 6 = t2 Blue in the (t, band) stacked input
    t = P.preprocess(x)
    assert tuple(t.shape) == (1, 6, 3, 224, 224)
    # plain reshape(18 -> 6x3): flat channel 6 lands at [2, 0]
    assert torch.allclose(t[0, 2, 0], torch.ones(224, 224))
    assert float(t.abs().sum()) == pytest.approx(224 * 224)


def test_forward_shape_and_state_dict_keys():
    m = P.PrithviCrop().eval()
    keys = set(m.state_dict())
    assert "backbone.pos_embed" in keys and "neck.fpn1.1.ln.weight" in keys and "decode_head.conv_seg.weight" in keys
    cls, prob = P.predict(m, np.tile(P.MEANS, (224, 224, 1)))
    assert cls.shape == (224, 224) and prob.shape == (13, 224, 224)
    assert np.allclose(prob.sum(0), 1, atol=1e-4)
