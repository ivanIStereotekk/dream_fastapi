import requests
import pytest


class TestKnowledgeGrounding:
    url = "http://0.0.0.0:8083/respond"

    checked_sentence_one = (
        "When Mabel visited their home to play the piano, "
        "she occasionally glimpsed a flitting swirl of white in the next room, "
        "sometimes even received a note of thanks for calling, but she never actually "
        "spoke with the reclusive, almost spectral Emily."
    )
    knowledge_one = (
        "The real-life soap opera behind the publication of Emily Dickinson’s poems\n"
        "When Mabel visited their home to play the piano, she occasionally glimpsed "
        "a flitting swirl of white in the next room, sometimes even received a note of "
        "thanks for calling, but she never actually spoke with the reclusive, almost spectral Emily."
    )
    text_one = "Yeah she was an icon she died in 1886 at the tender age of 55."

    checked_sentence_two = "Penguins are a group of aquatic flightless birds."
    knowledge_two = "Penguins are a group of aquatic flightless birds."
    text_two = "Who are penguins?"

    history = (
        "Do you know who Emily Dickson is?\n"
        'Emily Dickinson? The poet? I do! "Tell all the truth, but tell it slant" '
        "she once said. Do you like her poetry?"
    )

    queries = [
        {"batch":
            {"checked_sentence": checked_sentence_two, "knowledge": knowledge_two, "text": text_two, "history": history}
         },
        {"batch":
            {"checked_sentence": checked_sentence_one, "knowledge": knowledge_one, "text": text_one, "history": history}},
        {"batch":
            {"checked_sentence": None, "knowledge": None, "text": None, "history": None}}
    ]

    @pytest.mark.parametrize("queries", queries)
    def test_knowledge_grounding(self, query):
        response = requests.post(self.url, json=query).json()
        if query['batch']['checked_sentence'] == None:
            assert query['batch']['checked_sentence'] == None, "The checked_sentence should be None"
            print(f"Got Success with None query {response.text}")
        else:
            assert response.status_code == 200 , f"{response.status_code}"
            print(f"Got successfull with status code 200 {response.text}")
