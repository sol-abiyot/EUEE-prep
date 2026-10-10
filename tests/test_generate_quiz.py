from quiz import generate_quiz


def test_only_requested_subject_is_returned():
    quiz = generate_quiz("Physics")
    assert len(quiz) == 10
    assert all(q["subject"] == "Physics" for q in quiz)


def test_limit_is_respected():
    assert len(generate_quiz("Mathematics", limit=5)) == 5


def test_limit_larger_than_available_returns_all_matches():
    assert len(generate_quiz("Physics", "Kinematics", limit=50)) == 2


def test_quiz_has_no_duplicate_questions():
    ids = [q["id"] for q in generate_quiz()]
    assert len(ids) == len(set(ids))


def test_same_seed_gives_same_order_and_different_seed_can_differ():
    first = [q["id"] for q in generate_quiz("Mathematics", seed=1)]
    again = [q["id"] for q in generate_quiz("Mathematics", seed=1)]
    other = [q["id"] for q in generate_quiz("Mathematics", seed=2)]
    assert first == again
    assert sorted(first) == sorted(other)


def test_unknown_subject_returns_empty_list():
    assert generate_quiz("Astrology") == []