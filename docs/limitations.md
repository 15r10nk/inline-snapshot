
## pytest assert rewriting is disabled

inline-snapshot must disable pytest assert-rewriting if you use report/review/create/fix/trim/update flags.

## xdist is not supported

You can not use inline-snapshot in combination with `pytest-xdist`. The use of `-n=...` implies `--inline-snapshot=disable`.
