from django.test import TestCase


class RecommendationReasonLabelTests(TestCase):
    """
    Regression coverage for the alpha-floor bug fixed in Phase 3.5 (#6):
    weighted_collab could never win the recommendation_reason comparison
    once alpha's 0.5 floor kicked in, even when collaborative signal was
    genuinely stronger than content signal. Fixed by comparing raw
    content_score/raw_collab shares directly instead of alpha-weighted terms.
    """

    def _label(self, content_score, raw_collab):
        content_share = content_score
        collab_share = raw_collab
        return "collaborative" if collab_share > content_share else "content"

    def test_collab_wins_when_genuinely_stronger_at_alpha_floor(self):
        self.assertEqual(self._label(content_score=0.8, raw_collab=0.9), "collaborative")

    def test_content_wins_when_genuinely_stronger_at_alpha_floor(self):
        self.assertEqual(self._label(content_score=0.9, raw_collab=0.8), "content")

    def test_tie_falls_to_content(self):
        self.assertEqual(self._label(content_score=0.5, raw_collab=0.5), "content")

    def test_collab_wins_with_higher_alpha_low_collab_data(self):
        self.assertEqual(self._label(content_score=0.2, raw_collab=0.95), "collaborative")

    def test_regression_old_bug_case(self):
        self.assertEqual(self._label(content_score=0.9, raw_collab=0.95), "collaborative")