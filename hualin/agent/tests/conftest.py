import os
import sys
from pathlib import Path

os.environ.setdefault("SHELTERWISE_DATA", "local")
os.environ.setdefault("SHELTERWISE_TODAY", "2026-11-19")  # Thursday intake in the doc's sample
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from shelterwise_hualin.data import LocalRepo  # noqa: E402

FILLMORE = "1000 block of Fillmore St"


@pytest.fixture(scope="session")
def repo():
    return LocalRepo()


@pytest.fixture
def fillmore_case():
    return {"address_text": FILLMORE, "hazards": ["heat"], "hearing_date": "2026-11-23",
            "case_type": "nonpayment", "is_residential_tenant": True, "tenant_has_own_dbi_case": None,
            "tenant_complained_to_city": None, "days_to_hearing": 4,
            "search_query": "no heat in residential dwelling unit, indoor temperature below code minimum"}
