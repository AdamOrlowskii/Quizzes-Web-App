import json

def send_text_to_llm(text_in_chunks):

    questions = {}
    
    for chunk in text_in_chunks:
        #send it to the llm and add the return to the questions
        pass
        


    questions = {"What is the second letter of the alphabet?": {1: "A", 2: "B", 3: "C", 4: "D"},
                 "What is the third letter of the alphabet?": {1: "A", 2: "B", 3: "C", 4: "D"},
                 "What is the fourth letter of the alphabet?": {1: "A", 2: "B", 3: "C", 4: "D"}
                 }
    #json.loads(questions)

    return questions
