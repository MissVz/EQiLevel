from app.services.reward import shape_with_reply

class DummyMCP:
    def __init__(self, next_step):
        self.next_step = next_step

def test_shape_with_reply_one_question_good():
    base = 0.0
    m = DummyMCP('quiz')
    r = shape_with_reply(base, m, "What is 2+2?")
    assert r > base  # bonus applied

def test_shape_with_reply_missing_question_penalized():
    base = 0.0
    m = DummyMCP('prompt')
    r = shape_with_reply(base, m, "Please try the next step.")
    assert r < base  # penalty for zero '?'

def test_shape_with_reply_multiple_questions_penalized():
    base = 0.0
    m = DummyMCP('quiz')
    r = shape_with_reply(base, m, "Ready? What is 3+4?")
    assert r < 0  # penalized for extra question before the final one

