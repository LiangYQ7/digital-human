"""个性化路线推荐 测试。"""
from unittest.mock import patch

from brain.skills.route_recommender import recommend, list_interests, list_pois


# 测试用 POI 数据
_MOCK_POIS = [
    {"id": "p1", "name": "灵山大佛", "tags": ["佛教文化", "历史", "建筑"], "dwell_min": 40, "must_see": True},
    {"id": "p2", "name": "梵宫", "tags": ["建筑", "佛教文化", "艺术"], "dwell_min": 50, "must_see": True},
    {"id": "p3", "name": "拈花湾", "tags": ["自然风光", "禅意", "休闲"], "dwell_min": 90, "must_see": True},
    {"id": "p4", "name": "五印坛城", "tags": ["建筑", "佛教文化"], "dwell_min": 30, "must_see": False},
    {"id": "p5", "name": "灵山花海", "tags": ["自然风光", "休闲", "拍照"], "dwell_min": 30, "must_see": False},
]


class TestRecommend:
    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_by_interest_history(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        r = recommend(interest="历史", duration_hours=3)

        assert len(r["route"]) >= 1
        assert r["duration_hours"] == 3
        assert r["interest"] == "历史"
        # 历史兴趣下，灵山大佛（有历史标签）应排在前面
        names = [p["name"] for p in r["route"]]
        assert names[0] == "灵山大佛"  # must_see + 历史标签 = 最高分

    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_by_interest_nature(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        r = recommend(interest="自然风光", duration_hours=4)

        names = [p["name"] for p in r["route"]]
        # 拈花湾和灵山花海有自然风光标签，应优先
        assert "拈花湾" in names
        assert "灵山花海" in names

    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_respects_time_budget(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        r = recommend(interest="综合", duration_hours=1)

        total = sum(p["dwell_min"] for p in r["route"])
        assert total <= 60  # 1小时 = 60分钟

    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_minimum_two_if_possible(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        r = recommend(interest="综合", duration_hours=3)

        # 3小时预算下至少应有2个景点
        assert len(r["route"]) >= 2

    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_each_has_reason(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        r = recommend(interest="建筑", duration_hours=2)

        for p in r["route"]:
            assert "name" in p
            assert "reason" in p
            assert "dwell_min" in p
            assert len(p["reason"]) > 0

    @patch("brain.skills.route_recommender._load_pois")
    def test_recommend_no_pois_returns_fallback(self, mock_load):
        mock_load.return_value = []
        r = recommend(interest="历史", duration_hours=2)

        assert r["route"] == []
        assert r.get("fallback") is True


class TestListInterests:
    @patch("brain.skills.route_recommender._load_pois")
    def test_list_interests_aggregates_tags(self, mock_load):
        mock_load.return_value = _MOCK_POIS
        tags = list_interests()
        assert "佛教文化" in tags
        assert "自然风光" in tags
        assert "历史" in tags
        assert "建筑" in tags
