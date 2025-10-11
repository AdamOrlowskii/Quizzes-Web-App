def send_text_to_llm(text_in_chunks):
    questions = {}

    for chunk in text_in_chunks:
        # send it to the llm and add the return to the questions
        pass

    questions = [
        {
            "Q": "What is the second letter of the alphabet?",
            "A": {"1": "A", "2": "B", "3": "C", "4": "D"},
            "C": "2",
        },
        {
            "Q": "What is the third letter of the alphabet?",
            "A": {"1": "A", "2": "B", "3": "C", "4": "D"},
            "C": "3",
        },
        {
            "Q": "What is the fourth letter of the alphabet?",
            "A": {"1": "A", "2": "B", "3": "C", "4": "D"},
            "C": "4",
        },
    ]
    # json.loads(questions)

    return questions
