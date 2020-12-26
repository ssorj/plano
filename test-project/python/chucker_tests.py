from plano import *

@test
def test_hello():
    print("Hello")

@test
def test_goodbye():
    print("Goodbye")

@test(disabled=True)
def test_badbye():
    assert False, "Badbye"
