## Fixed

- Fixed snapshot updates when pytest reuses stale assertion-rewrite cache files after a test folder is moved, which could leave cached code objects pointing at the old source path ([#369](https://github.com/15r10nk/inline-snapshot/issues/369)).
