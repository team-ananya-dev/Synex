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


def test_company_in_question_is_named_and_first():
    from app.stages.s2_decomposer import _order_companies
    q = "How is the delivery business doing at Acme Foods?"
    got = _order_companies(q, [{"name": "Rival Co", "basis": "inferred"}, {"name": "Acme Foods", "basis": "inferred"}])
    assert got == [{"name": "Acme Foods", "basis": "named"}, {"name": "Rival Co", "basis": "inferred"}]


def test_company_name_must_match_as_a_whole_word():
    from app.stages.s2_decomposer import _order_companies
    got = _order_companies("What is Coca-Cola doing?", [{"name": "Ola", "basis": "named"}, {"name": "Coca-Cola", "basis": "inferred"}])
    assert got == [{"name": "Coca-Cola", "basis": "named"}, {"name": "Ola", "basis": "inferred"}]
    with pytest.raises(ValueError, match="not in the question"):
        validate("What is Coca-Cola doing?", reply(target_companies=[{"name": "Ola", "basis": "named"}]))
