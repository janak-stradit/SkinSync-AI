from analysis.pipeline import _apply_profile_context


def test_profile_context_adjusts_metric_scores():
    base_scores = {
        'pigmentation': 20.0,
        'acne': 20.0,
        'redness': 20.0,
        'wrinkles': 20.0,
        'pores': 20.0,
    }

    adjusted = _apply_profile_context(base_scores, {
        'skin_profile': {
            'skin_concerns': ['acne', 'pigmentation'],
            'sensitivity_level': 'high',
        }
    })

    assert adjusted['acne'] > base_scores['acne']
    assert adjusted['pigmentation'] > base_scores['pigmentation']
    assert adjusted['redness'] > base_scores['redness']
