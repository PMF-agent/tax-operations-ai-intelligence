
import unittest
import pandas as pd

from priority_validation import (
    build_priority_queue,
    active_queue,
    check_queue_order,
    evaluate_recommendation,
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
        "business_sla_risk": risk,
        "status": status,
        "dependency": dependency,
        "case_type": case_type,
        "sla_deadline": deadline,
        "agency_name": agency_name,
        "submission_date": submission_date,
    }


class TestPriorityQueue(unittest.TestCase):

    def make_queue(self, cases):
        return build_priority_queue(cases)

    def test_breached_before_at_risk(self):
        cases = [
            make_case("T-1", risk="At Risk"),
            make_case("T-2", risk="Breached"),
        ]
        queue = self.make_queue(cases)
        self.assertEqual(queue.iloc[0]["case_id"], "T-2")

    def test_at_risk_before_within_sla(self):
        cases = [
            make_case("T-1", risk="Within SLA"),
            make_case("T-2", risk="At Risk"),
        ]
        queue = self.make_queue(cases)
        self.assertEqual(queue.iloc[0]["case_id"], "T-2")

    def test_earlier_deadline_first(self):
        cases = [
            make_case("T-1", deadline="2026-11-15 15:00:00"),
            make_case("T-2", deadline="2026-11-10 15:00:00"),
        ]
        queue = self.make_queue(cases)
        self.assertEqual(queue.iloc[0]["case_id"], "T-2")

    def test_case_id_breaks_ties(self):
        cases = [
            make_case("T-2"),
            make_case("T-1"),
        ]
        queue = self.make_queue(cases)
        self.assertEqual(
            queue["case_id"].tolist(),
            ["T-1", "T-2"],
        )

    def test_closed_after_active(self):
        cases = [
            make_case("T-1", status="Closed"),
            make_case("T-2", status="In Progress"),
        ]
        queue = self.make_queue(cases)
        self.assertEqual(queue.iloc[0]["case_id"], "T-2")

    def test_closed_excluded_from_active(self):
        cases = [
            make_case("T-1", status="Closed"),
            make_case("T-2", status="In Progress"),
        ]
        queue = self.make_queue(cases)
        active = active_queue(queue)
        self.assertNotIn("T-1", active["case_id"].tolist())
        self.assertIn("T-2", active["case_id"].tolist())

    def test_deterministic_order(self):
        cases = [
            make_case("T-3"),
            make_case("T-1"),
            make_case("T-2"),
        ]
        first = self.make_queue(cases)
        second = self.make_queue(list(reversed(cases)))

        self.assertEqual(
            first["case_id"].tolist(),
            second["case_id"].tolist(),
        )

    def test_invalid_duplicate_ids(self):
        cases = [
            make_case("T-1"),
            make_case("T-1"),
        ]
        with self.assertRaises(ValueError):
            self.make_queue(cases)

    def test_order_checker(self):
        cases = [
            make_case("T-1", risk="Breached"),
            make_case("T-2", risk="At Risk"),
            make_case("T-3", risk="Within SLA"),
        ]
        queue = self.make_queue(cases)

        self.assertTrue(check_queue_order(queue))
        self.assertFalse(
            check_queue_order(
                queue.iloc[::-1].reset_index(drop=True)
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
            "whether and when submission occurred",
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
        action = result["action"].lower()

        self.assertIn(
            "confirm the correct agency",
            action,
        )
        self.assertIn(
            "whether and when submission occurred",
            action,
        )
        self.assertIn(
            "do not assume a submission was completed",
            action,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
