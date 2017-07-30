from plano import *

def open_test_session(session):
    set_message_threshold("warn")

def test_logging(session):
    with temp_file() as file:
        with open(file, "w") as fp:
            set_message_output(fp)
            set_message_threshold("debug")

            try:
                try:
                    fail("Nooo!")
                except PlanoException:
                    pass

                error("Error!")
                warn("Warning!")
                notice("Take a look!")
                debug("By the way")
                debug("abc{}{}{}", 1, 2, 3)
                eprint("Here's a story")
                eprint("About a {}", "man named Brady")
                flush()
            except KeyboardInterrupt:
                raise
            except:
                fp.flush()
                print(read(file))
                raise
            finally:
                set_message_output(STD_ERR)
                set_message_threshold("warn")

def test_path_operations(session):
    curr_dir = current_dir()

    path = "a/b/c"
    result = absolute_path(path)

    assert result == join(curr_dir, path), result

    path = "/x/y/z"
    result = absolute_path(path)

    assert result == path, result

    path = "a//b/../c/"
    result = normalize_path(path)

    assert result == "a/c", result

    # XXX with temp_working_dir():

    path = "/a/../c"
    result = real_path(path)

    assert result == "/c", result
