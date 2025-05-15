from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_json_format():

    Example(
        """\
from inline_snapshot import external

def test_a():
    assert [1,2] == external(".json")
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/17f5ce5ea0f8711b6b20414da84373fb56176c3a3112c86c94529d3e29dacac3-new.json": """\
[
  1,
  2
]\
""",
                "test_something.py": """\
from inline_snapshot import external

def test_a():
    assert [1,2] == external("hash:17f5ce5ea0f8*.json")
""",
            }
        ),
    )


# def test_pickle_format():

#     Example(
#         """\
# from inline_snapshot import external

# def test_a():
#     assert [1,2] == external(".pickle")
# """
#     ).run_inline(
#         ["--inline-snapshot=create"],
#         changed_files=snapshot(
#             {
#                 ".inline-snapshot/external/76325239b7d91654a57010349886e0c24a90dbd94be4a5e69157dbb98e79c756-new.pickle": b"\x80\x05\x95\t\x00\x00\x00\x00\x00\x00\x00]\x94(K\x01K\x02e.",
#                 "test_something.py": """\
# from inline_snapshot import external

# def test_a():
#     assert [1,2] == external("hash:76325239b7d9*.pickle")
# """,
#             }
#         ),
#     )
