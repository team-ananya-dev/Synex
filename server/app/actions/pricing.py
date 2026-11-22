"""The quoted price of a case, in rupees. A display figure only: the service takes no payment."""
from ..core import config

LABEL = "quoted price, no payment taken"


def quote(n_subquestions: int) -> dict:
    price = config.price_per_subquestion_inr()
    return {"subquestions": n_subquestions, "price_per_subquestion_inr": price,
            "quoted_price_inr": round(n_subquestions * price, 2), "label": LABEL}
