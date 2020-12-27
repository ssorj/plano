from plano import *

@test
def test_hello():
    print("Hello")

@test
def test_goodbye():
    print("Goodbye")

@test(disabled=True)
def test_badbye():
    print("Badbye")
    assert False

@test(disabled=True)
def test_keyboard_interrupt():
    raise KeyboardInterrupt()

@test
def test_test_skipped():
    raise PlanoTestSkipped("Test coverage")

@test(disabled=True, timeout=1)
def test_timeout_expired():
    sleep(10)
    assert False

@test(disabled=True)
def test_process_error():
    run("expr 1 / 0")

@test(disabled=True)
def test_system_exit():
    exit(1)
