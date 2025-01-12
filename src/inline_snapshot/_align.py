from itertools import groupby


def align(seq_a, seq_b) -> str:

    start = 0

    for a, b in zip(seq_a, seq_b):
        if a == b:
            start += 1
        else:
            break

    if start == len(seq_a) == len(seq_b):
        return "m" * start

    end = 0

    for a, b in zip(reversed(seq_a[start:]), reversed(seq_b[start:])):
        if a == b:
            end += 1
        else:
            break

    diff = nw_align(seq_a[start : len(seq_a) - end], seq_b[start : len(seq_b) - end])

    return "m" * start + diff + "m" * end


def nw_align(seq_a, seq_b) -> str:

    matrix: list = [[(0, "e")] + [(0, "i")] * len(seq_b)]

    for a in seq_a:
        last = matrix[-1]

        new_line = [(0, "d")]
        for bi, b in enumerate(seq_b, 1):
            la, lc, lb = new_line[-1], last[bi - 1], last[bi]
            values = [(la[0], "i"), (lb[0], "d")]
            if a == b:
                values.append((lc[0] + 1, "m"))

            new_line.append(max(values))
        matrix.append(new_line)

    # backtrack

    ai = len(seq_a)
    bi = len(seq_b)
    d = ""
    track = ""

    while d != "e":
        _, d = matrix[ai][bi]
        if d == "m":
            ai -= 1
            bi -= 1
        elif d == "i":
            bi -= 1
        elif d == "d":
            ai -= 1
        if d != "e":
            track += d

    return track[::-1]


def add_x(track):
    """Replaces an `id` with the same number of insertions and deletions with
    x."""
    groups = [(c, len(list(v))) for c, v in groupby(track)]
    i = 0
    result = ""
    while i < len(groups):
        g = groups[i]
        if i == len(groups) - 1:
            result += g[0] * g[1]
            break

        ng = groups[i + 1]
        if g[0] == "d" and ng[0] == "i" and g[1] == ng[1]:
            result += "x" * g[1]
            i += 1
        else:
            result += g[0] * g[1]

        i += 1

    return result
