
import unittest
import pandas as pd

from priority_validation import (
    build_priority_queue,
    active_queue,
    check_queue_order,
    evaluate_recommendation,
    validate_simulation,
)


def make_case(
    case_id,
    risk="Within SLA",
    status="In Progress",
    dependency="None",
    case_type="New Tax Registration",
    deadline="2026-11-11 15:00:00",
    agency_name="Texas Workforce Commission",
    submission_date=None,
):
    return {
        "case_id": case_id,
        "sla_risk": risk,
        "status": status,
        "dependency": dependency,
        "case_type": case_type,
        "sla_deadline": deadline,
        "agency_name": agency_name,
        "agency_submission_date": submission_date,
    }


class TestPriorityQueue(unittest.TestCase):

    def test_breached_before_at_risk(self):
        cases = [
            make_case("TX-1", "At Risk"),
            make_case("TX-2", "Breached"),
        ]
        result = build_priority_queue(cases)
        self.assertEqual(
            result["case_id"].tolist(),
            ["TX-2", "TX-1"],
        )

    def test_at_risk_before_within_sla(self):
        cases = [
            make_case("TX-1", "Within SLA"),
            make_case("TX-2", "At Risk"),
        ]
        result = build_priority_queue(cases)
        self.assertEqual(
            result.iloc[0]["case_id"],
            "TX-2",
        )

    def test_closed_after_active(self):
        cases = [
            make_case(
                "TX-1", "Breached", "Closed"
            ),
            make_case(
                "TX-2", "Within SLA", "In Progress"
            ),
        ]
        result = build_priority_queue(cases)
        self.assertEqual(
            result.iloc[0]["case_id"],
            "TX-2",
        )

    def test_closed_excluded_from_active(self):
        cases = [
            make_case("TX-1", status="Closed"),
            make_case("TX-2", status="Resolved"),
            make_case("TX-3", status="In Progress"),
        ]
        result = active_queue(cases)
        self.assertEqual(
            result["case_id"].tolist(),
            ["TX-3"],
        )

    def test_earlier_deadline_first(self):
        cases = [
            make_case(
                "TX-1",
                deadline="2026-11-12 15:00:00",
            ),
            make_case(
                "TX-2",
                deadline="2026-11-10 15:00:00",
            ),
        ]
        result = build_priority_queue(cases)
        self.assertEqual(
            result.iloc[0]["case_id"],
            "TX-2",
        )

    def test_case_id_breaks_ties(self):
        cases = [
            make_case("TX-2"),
            make_case("TX-1"),
        ]
        result = build_priority_queue(cases)
        self.assertEqual(
            result["case_id"].tolist(),
            ["TX-1", "TX-2"],
        )

    def test_deterministic_order(self):
        cases = [
            make_case("TX-3", "At Risk"),
            make_case("TX-1", "Breached"),
            make_case("TX-2", "Within SLA"),
        ]
        first = build_priority_queue(cases)
        second = build_priority_queue(
            list(reversed(cases))
        )
        self.assertEqual(
            first["case_id"].tolist(),
            second["case_id"].tolist(),
        )

    def test_invalid_duplicate_ids(self):
        cases = [
            make_case("TX-1"),
            make_case("TX-1"),
        ]
        with self.assertRaises(ValueError):
            build_priority_queue(cases)

    def test_order_checker(self):
        cases = [
            make_case("TX-1", "Breached"),
            make_case("TX-2", "Within SLA"),
        ]
        ranked = build_priority_queue(cases)
        self.assertTrue(check_queue_order(ranked))
        self.assertFalse(
            check_queue_order(
                ranked.iloc[::-1].reset_index(drop=True)
            )
        )


class TestRecommendations(unittest.TestCase):

    def test_agency_follow_up(self):
        case = make_case(
            "TX-1051",
            status="Waiting on Agency",
            dependency="Agency",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "Agency Follow-up",
        )
        self.assertIn(
            "submission date",
            result["action"].lower(),
        )

    def test_customer_follow_up(self):
        case = make_case(
            "TX-2",
            status="Waiting on Customer",
            dependency="Customer",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "Customer Follow-up",
        )

    def test_breached_escalation(self):
        case = make_case(
            "TX-3",
            risk="Breached",
            dependency="Agency",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "SLA Escalation",
        )
        self.assertEqual(
            result["urgency"],
            "Critical",
        )

    def test_at_risk_intervention(self):
        case = make_case(
            "TX-4",
            risk="At Risk",
            dependency="Customer",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "Preventive Intervention",
        )
        self.assertEqual(
            result["urgency"],
            "High",
        )

    def test_closed_case_review(self):
        case = make_case(
            "TX-5",
            risk="Breached",
            status="Closed",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "Closure Review",
        )

    def test_unknown_sla(self):
        case = make_case(
            "TX-6",
            risk="Unknown",
        )
        result = evaluate_recommendation(case)

        self.assertEqual(
            result["action_type"],
            "Data Validation",
        )

    def test_agency_information_not_invented(self):
        case = make_case(
            "TX-7",
            status="Waiting on Agency",
            dependency="Agency",
            agency_name=None,
            submission_date=None,
        )
        result = evaluate_recommendation(case)

        self.assertIn(
            "agency name",
            result["action"].lower(),
        )
        self.assertIn(
            "submission date",
            result["action"].lower(),
        )


class TestOriginalSimulation(unittest.TestCase):

    def test_original_simulation(self):
        result = validate_simulation()

        self.assertEqual(result["total_cases"], 50)
        self.assertTrue(
            result["expected_distribution"]
        )
        self.assertTrue(
            result["unique_case_ids"]
        )
        self.assertTrue(
            result["valid_queue_ranks"]
        )
        self.assertTrue(
            result["risk_priority_order_valid"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
