import pytest

from app.stages.s2_decomposer import validate


def sub(**kw):
    base = {"text": "t", "expertise": "e", "title_keywords": ["ops", "supply chain"],
            "target_companies": [{"name": "Acme", "basis": "named"}]}
    return {**base, **kw}


def reply(n=3, **kw):
    return {"subquestions": [sub(**kw) for _ in range(n)]}


def test_accepts_valid_reply():
    validate("What does Acme do?", reply())


@pytest.mark.parametrize("r,msg", [
    (reply(2), "between 3 and 5"),
    (reply(6), "between 3 and 5"),
    (reply(title_keywords=["ops"]), "2 to 6"),
    (reply(title_keywords=["a", "b c d e"]), "at most 3 words"),
    (reply(target_companies=[]), "at least one"),
    (reply(text=" "), "empty"),
])
def test_rejects_bad_shapes(r, msg):
    with pytest.raises(ValueError, match=msg):
        validate("What does Acme do?", r)


def test_named_company_must_appear_in_question():
    with pytest.raises(ValueError, match="not in the question"):
        validate("What does a rival do?", reply())
    validate("What does a rival do?", reply(target_companies=[{"name": "Acme", "basis": "inferred"}]))
