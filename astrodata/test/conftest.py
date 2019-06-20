
import pytest
import os


@pytest.fixture
def input_test_path():

    try:
        path = os.environ['DRAGONS_TEST_INPUTS']
    except KeyError:
        pytest.skip(
            "Could not find environment variable: $DRAGONS_TEST_INPUTS")

    if not os.path.exists(path):
        pytest.skip(
            "Could not access path stored in $DRAGONS_TEST_INPUTS: "
            "{}".format(path)
        )

    return path
