def mark_quiz(questions, answers):
    """Mark a quiz.

    questions: list of question dictionaries.
    answers: dictionary of {question_id: chosen_letter}.
    Returns a dictionary with score, total, percentage and per-question results.
    """
    results = []
    score = 0

    for q in questions:
        raw = answers.get(q["id"])
        chosen = raw.strip().upper() if isinstance(raw, str) else ""

        if chosen == "":
            status = "unanswered"
        elif chosen not in q["choices"]:
            status = "invalid"
        elif chosen == q["answer"]:
            status = "correct"
            score += 1
        else:
            status = "incorrect"

        results.append({
            "id": q["id"],
            "question": q["question"],
            "choices": q["choices"],
            "chosen": chosen or None,
            "correct_answer": q["answer"],
            "status": status,
            "explanation": q["explanation"],
        })

    total = len(questions)
    percentage = round(score / total * 100, 1) if total else 0.0

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
    }